"""Device health monitoring service with polling and status updates."""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.device import IoTDevice, DeviceStatus
from app.services.socketio import emit_device_status

logger = logging.getLogger(__name__)


class DeviceMonitorService:
    """
    Monitors IoT device health by polling status and broadcasting changes.

    Runs as a background task that periodically checks device connectivity
    and emits status change events via WebSocket.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        poll_interval: float = 30.0,
        offline_threshold_seconds: int = 120,
    ):
        self.session_factory = session_factory
        self.poll_interval = poll_interval
        self.offline_threshold = timedelta(seconds=offline_threshold_seconds)
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the monitoring loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop(), name="device_monitor")
        logger.info("Device monitor service started", poll_interval=self.poll_interval)

    async def stop(self) -> None:
        """Stop the monitoring loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Device monitor service stopped")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                await self._check_devices()
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Device monitor error: {e}")
                await asyncio.sleep(5)

    async def _check_devices(self) -> None:
        """Check all active devices for connectivity."""
        async with self.session_factory() as db:
            result = await db.execute(
                select(IoTDevice).where(
                    and_(
                        IoTDevice.deleted_at.is_(None),
                        IoTDevice.status != DeviceStatus.MAINTENANCE.value,
                    )
                )
            )
            devices = list(result.scalars().all())

            now = datetime.now(timezone.utc)
            for device in devices:
                old_status = device.status

                # Mark device as offline if not seen within threshold
                if device.last_seen and (now - device.last_seen) > self.offline_threshold:
                    if device.status in (DeviceStatus.ONLINE.value, DeviceStatus.ALERT.value):
                        device.status = DeviceStatus.OFFLINE.value
                        await db.commit()

                        # Emit status change
                        await emit_device_status({
                            "device_id": str(device.id),
                            "name": device.name,
                            "status": DeviceStatus.OFFLINE.value,
                            "previous_status": old_status,
                            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                            "timestamp": now.isoformat(),
                        })

    async def update_device_heartbeat(
        self,
        db: AsyncSession,
        device_id,
        connection_quality: int | None = None,
    ) -> None:
        """Update device last_seen timestamp (called by device ping/event)."""
        result = await db.execute(
            select(IoTDevice).where(IoTDevice.id == device_id)
        )
        device = result.scalar_one_or_none()
        if not device:
            return

        now = datetime.now(timezone.utc)
        old_status = device.status
        device.last_seen = now

        if connection_quality is not None:
            device.connection_quality = connection_quality

        # If device was offline, mark it online
        if device.status == DeviceStatus.OFFLINE.value:
            device.status = DeviceStatus.ONLINE.value
            await db.commit()

            await emit_device_status({
                "device_id": str(device.id),
                "name": device.name,
                "status": DeviceStatus.ONLINE.value,
                "previous_status": old_status,
                "last_seen": now.isoformat(),
                "timestamp": now.isoformat(),
            })
        else:
            await db.commit()
