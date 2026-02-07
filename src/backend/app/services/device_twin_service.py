"""Device twin service for desired/reported config synchronization."""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from deepdiff import DeepDiff
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import structlog

from app.models.device_twin import DeviceTwin
from app.models.device import IoTDevice
from app.services.mqtt_service import VigiliaMQTTService
from app.services.socketio import (
    emit_device_config_updated,
    emit_device_config_synced,
)

logger = structlog.get_logger()


class DeviceTwinError(Exception):
    """Base exception for device twin operations."""
    pass


class DeviceNotFoundError(DeviceTwinError):
    """Raised when device not found."""
    pass


class DeviceTwinService:
    """Manages device twin state synchronization."""

    def __init__(self, db: AsyncSession, mqtt_service: VigiliaMQTTService):
        self.db = db
        self.mqtt = mqtt_service

    async def get_twin(self, device_id: uuid.UUID) -> DeviceTwin:
        """Get device twin, creating one if it doesn't exist."""
        twin = await self._get_or_create_twin(device_id)
        return twin

    async def get_twin_with_delta(self, device_id: uuid.UUID) -> dict:
        """Get device twin with detailed delta calculation."""
        twin = await self.get_twin(device_id)
        delta = self._calculate_delta(twin)

        return {
            "device_id": str(twin.device_id),
            "desired_config": twin.desired_config,
            "desired_version": twin.desired_version,
            "desired_updated_at": twin.desired_updated_at.isoformat() if twin.desired_updated_at else None,
            "reported_config": twin.reported_config,
            "reported_version": twin.reported_version,
            "reported_updated_at": twin.reported_updated_at.isoformat() if twin.reported_updated_at else None,
            "is_synced": twin.is_synced,
            "delta": delta,
        }

    async def update_desired_config(
        self,
        device_id: uuid.UUID,
        desired_config: dict,
    ) -> DeviceTwin:
        """Update desired config and publish to device via MQTT.

        Merges partial update with existing desired config, increments version,
        publishes to MQTT with retain flag, and emits Socket.IO event.
        """
        # Fetch device with building for agency_id
        stmt = (
            select(IoTDevice)
            .options(selectinload(IoTDevice.building))
            .where(IoTDevice.id == device_id)
        )
        result = await self.db.execute(stmt)
        device = result.scalar_one_or_none()
        if not device:
            raise DeviceNotFoundError(f"Device {device_id} not found")

        twin = await self._get_or_create_twin(device_id)

        # Merge with existing config (support partial updates)
        merged = {**twin.desired_config, **desired_config}

        twin.desired_config = merged
        twin.desired_version += 1
        twin.desired_updated_at = datetime.now(timezone.utc)

        # Recalculate sync status
        twin.is_synced = self._is_synced(twin.desired_config, twin.reported_config)

        await self.db.commit()
        await self.db.refresh(twin)

        # Fire-and-forget MQTT publish
        asyncio.create_task(self._publish_desired_config(device, twin))

        # Emit Socket.IO event
        await emit_device_config_updated(
            device_id=str(device_id),
            desired_config=twin.desired_config,
            desired_version=twin.desired_version,
            is_synced=twin.is_synced,
        )

        logger.info(
            "Updated desired config",
            device_id=str(device_id),
            version=twin.desired_version,
            is_synced=twin.is_synced,
        )

        return twin

    async def update_reported_config(
        self,
        device_id: uuid.UUID,
        reported_config: dict,
        reported_version: Optional[int] = None,
    ) -> DeviceTwin:
        """Update reported config from device MQTT message.

        Validates version for stale detection, increments reported_version,
        recalculates is_synced, and emits Socket.IO events.
        """
        twin = await self._get_or_create_twin(device_id)

        # Check version if provided (detect stale updates)
        if reported_version is not None and reported_version <= twin.reported_version:
            logger.warning(
                "Ignoring stale reported config",
                device_id=str(device_id),
                reported_version=reported_version,
                current_version=twin.reported_version,
            )
            return twin

        # Track sync status before update
        was_synced = twin.is_synced

        twin.reported_config = reported_config
        twin.reported_version += 1
        twin.reported_updated_at = datetime.now(timezone.utc)

        # Recalculate sync status
        twin.is_synced = self._is_synced(twin.desired_config, twin.reported_config)

        await self.db.commit()
        await self.db.refresh(twin)

        # Emit config:updated event
        await emit_device_config_updated(
            device_id=str(device_id),
            reported_config=reported_config,
            reported_version=twin.reported_version,
            is_synced=twin.is_synced,
        )

        # Emit config:synced event if just synced
        if not was_synced and twin.is_synced:
            await emit_device_config_synced(
                device_id=str(device_id),
                config=reported_config,
                synced_at=twin.reported_updated_at.isoformat(),
            )

        logger.debug(
            "Updated reported config",
            device_id=str(device_id),
            version=twin.reported_version,
            is_synced=twin.is_synced,
        )

        return twin

    async def _get_or_create_twin(self, device_id: uuid.UUID) -> DeviceTwin:
        """Get existing twin or create new one with empty configs."""
        stmt = select(DeviceTwin).where(DeviceTwin.device_id == device_id)
        result = await self.db.execute(stmt)
        twin = result.scalar_one_or_none()

        if not twin:
            twin = DeviceTwin(device_id=device_id)
            self.db.add(twin)
            await self.db.commit()
            await self.db.refresh(twin)

        return twin

    async def _publish_desired_config(self, device: IoTDevice, twin: DeviceTwin) -> None:
        """Publish desired config to MQTT with retain flag (fire-and-forget)."""
        agency_id = device.building.agency_id if device.building else device.building_id
        topic = f"agency/{agency_id}/device/{device.id}/config/desired"
        payload = {
            "config": twin.desired_config,
            "version": twin.desired_version,
            "timestamp": twin.desired_updated_at.isoformat(),
        }

        try:
            await self.mqtt.publish(
                topic=topic,
                payload=payload,
                qos=1,
                retain=True,
            )
            logger.info(
                "Published desired config to MQTT",
                device_id=str(device.id),
                version=twin.desired_version,
                topic=topic,
            )
        except Exception as e:
            logger.error(
                "Failed to publish desired config to MQTT",
                device_id=str(device.id),
                error=str(e),
            )

    def _is_synced(self, desired: dict, reported: dict) -> bool:
        """Check if desired and reported configs match exactly."""
        return len(DeepDiff(desired, reported, ignore_order=False)) == 0

    def _calculate_delta(self, twin: DeviceTwin) -> dict:
        """Calculate detailed delta between desired and reported configs."""
        desired = twin.desired_config or {}
        reported = twin.reported_config or {}

        diff = DeepDiff(
            desired,
            reported,
            ignore_order=False,
            report_repetition=True,
            verbose_level=2,
        )

        if not diff:
            return {
                "is_synced": True,
                "diff_summary": "Configuration synchronized",
                "differences": {},
            }

        differences = {}

        if "values_changed" in diff:
            differences["values_changed"] = {
                path: {
                    "desired": change["new_value"],
                    "reported": change["old_value"],
                }
                for path, change in diff["values_changed"].items()
            }

        if "dictionary_item_added" in diff:
            differences["dictionary_item_added"] = list(diff["dictionary_item_added"])

        if "dictionary_item_removed" in diff:
            differences["dictionary_item_removed"] = list(diff["dictionary_item_removed"])

        # Generate human-readable summary
        change_count = len(differences.get("values_changed", {}))
        added_count = len(differences.get("dictionary_item_added", []))
        removed_count = len(differences.get("dictionary_item_removed", []))

        summary_parts = []
        if change_count:
            summary_parts.append(f"{change_count} value(s) changed")
        if added_count:
            summary_parts.append(f"{added_count} key(s) added to desired")
        if removed_count:
            summary_parts.append(f"{removed_count} key(s) in reported not in desired")

        diff_summary = ", ".join(summary_parts) if summary_parts else "Unknown difference"

        return {
            "is_synced": False,
            "diff_summary": diff_summary,
            "differences": differences,
        }
