"""IoT Device management service."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.device import IoTDevice, DeviceType, DeviceStatus
from app.models.device_status_history import DeviceStatusHistory
from app.models.alert import Alert, AlertStatus


class DeviceError(Exception):
    """Device-related errors."""
    pass


class DeviceService:
    """Service for IoT device CRUD, status tracking, and floor placement."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_device(
        self,
        name: str,
        device_type: DeviceType,
        building_id: uuid.UUID,
        serial_number: str | None = None,
        ip_address: str | None = None,
        mac_address: str | None = None,
        model: str | None = None,
        firmware_version: str | None = None,
        manufacturer: str = "Axis",
        floor_plan_id: uuid.UUID | None = None,
        position_x: float | None = None,
        position_y: float | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        location_name: str | None = None,
        config: dict | None = None,
        capabilities: list | None = None,
    ) -> IoTDevice:
        """Register a new IoT device."""
        # Validate that both coordinates are provided when floor_plan_id is set
        if floor_plan_id is not None:
            if position_x is None or position_y is None:
                raise DeviceError(
                    "Both position_x and position_y are required when floor_plan_id is specified"
                )

        device = IoTDevice(
            id=uuid.uuid4(),
            name=name,
            device_type=device_type.value if hasattr(device_type, 'value') else device_type,
            serial_number=serial_number,
            ip_address=ip_address,
            mac_address=mac_address,
            model=model,
            firmware_version=firmware_version,
            manufacturer=manufacturer,
            building_id=building_id,
            floor_plan_id=floor_plan_id,
            position_x=position_x,
            position_y=position_y,
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
            status=DeviceStatus.OFFLINE.value,
            config=config or {},
            capabilities=capabilities or [],
        )

        self.db.add(device)
        await self.db.commit()
        await self.db.refresh(device)
        return device

    async def get_device(self, device_id: uuid.UUID) -> IoTDevice | None:
        """Get device by ID."""
        result = await self.db.execute(
            select(IoTDevice).where(
                and_(IoTDevice.id == device_id, IoTDevice.deleted_at.is_(None))
            )
        )
        return result.scalar_one_or_none()

    async def list_devices(
        self,
        building_id: uuid.UUID | None = None,
        floor_plan_id: uuid.UUID | None = None,
        device_type: DeviceType | None = None,
        status: DeviceStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[IoTDevice], int]:
        """List devices with optional filters."""
        query = select(IoTDevice).where(IoTDevice.deleted_at.is_(None))

        if building_id:
            query = query.where(IoTDevice.building_id == building_id)
        if floor_plan_id:
            query = query.where(IoTDevice.floor_plan_id == floor_plan_id)
        if device_type:
            query = query.where(IoTDevice.device_type == (device_type.value if hasattr(device_type, 'value') else device_type))
        if status:
            query = query.where(IoTDevice.status == (status.value if hasattr(status, 'value') else status))

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.order_by(IoTDevice.name).limit(limit).offset(offset)
        result = await self.db.execute(query)

        return list(result.scalars().all()), total

    async def update_device(
        self, device_id: uuid.UUID, **kwargs: Any
    ) -> IoTDevice:
        """Update device attributes."""
        device = await self.get_device(device_id)
        if not device:
            raise DeviceError(f"Device {device_id} not found")

        for key, value in kwargs.items():
            if hasattr(device, key) and value is not None:
                setattr(device, key, value)

        await self.db.commit()
        await self.db.refresh(device)
        return device

    async def update_position(
        self,
        device_id: uuid.UUID,
        floor_plan_id: uuid.UUID,
        position_x: float,
        position_y: float,
    ) -> IoTDevice:
        """Update device position on a floor plan."""
        device = await self.get_device(device_id)
        if not device:
            raise DeviceError(f"Device {device_id} not found")

        device.floor_plan_id = floor_plan_id
        device.position_x = position_x
        device.position_y = position_y

        await self.db.commit()
        await self.db.refresh(device)
        return device

    async def _record_status_change(
        self,
        device_id: uuid.UUID,
        old_status: str | None,
        new_status: str,
        connection_quality: int | None = None,
        reason: str | None = None,
    ) -> DeviceStatusHistory:
        """Record a status change in the history table."""
        history = DeviceStatusHistory(
            id=uuid.uuid4(),
            device_id=device_id,
            old_status=old_status,
            new_status=new_status,
            changed_at=datetime.now(timezone.utc),
            connection_quality=connection_quality,
            reason=reason,
        )
        self.db.add(history)
        return history

    async def update_status(
        self,
        device_id: uuid.UUID,
        status: DeviceStatus,
        connection_quality: int | None = None,
        reason: str | None = None,
    ) -> IoTDevice:
        """Update device operational status."""
        device = await self.get_device(device_id)
        if not device:
            raise DeviceError(f"Device {device_id} not found")

        old_status = device.status
        new_status = status.value if hasattr(status, 'value') else status

        # Only record history if status actually changed
        if old_status != new_status:
            await self._record_status_change(
                device_id=device_id,
                old_status=old_status,
                new_status=new_status,
                connection_quality=connection_quality,
                reason=reason,
            )

        device.status = new_status
        device.last_seen = datetime.now(timezone.utc)
        if connection_quality is not None:
            device.connection_quality = connection_quality

        await self.db.commit()
        await self.db.refresh(device)
        return device

    async def update_config(
        self, device_id: uuid.UUID, config: dict
    ) -> IoTDevice:
        """Update device detection configuration."""
        device = await self.get_device(device_id)
        if not device:
            raise DeviceError(f"Device {device_id} not found")

        device.config = config
        await self.db.commit()
        await self.db.refresh(device)
        return device

    async def delete_device(self, device_id: uuid.UUID) -> None:
        """Soft delete a device."""
        device = await self.get_device(device_id)
        if not device:
            raise DeviceError(f"Device {device_id} not found")

        device.deleted_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def get_devices_by_building(
        self, building_id: uuid.UUID
    ) -> list[IoTDevice]:
        """Get all devices in a building."""
        result = await self.db.execute(
            select(IoTDevice).where(
                and_(
                    IoTDevice.building_id == building_id,
                    IoTDevice.deleted_at.is_(None),
                )
            ).order_by(IoTDevice.name)
        )
        return list(result.scalars().all())

    async def get_devices_by_floor(
        self, floor_plan_id: uuid.UUID
    ) -> list[IoTDevice]:
        """Get all devices on a specific floor."""
        result = await self.db.execute(
            select(IoTDevice).where(
                and_(
                    IoTDevice.floor_plan_id == floor_plan_id,
                    IoTDevice.deleted_at.is_(None),
                )
            ).order_by(IoTDevice.name)
        )
        return list(result.scalars().all())

    async def get_building_alert_counts(
        self, building_ids: list[uuid.UUID] | None = None
    ) -> dict[str, int]:
        """Get active alert counts per building."""
        query = (
            select(
                Alert.building_id,
                func.count(Alert.id).label("alert_count"),
            )
            .where(
                and_(
                    Alert.building_id.isnot(None),
                    Alert.status.in_([
                        AlertStatus.PENDING,
                        AlertStatus.PROCESSING,
                        AlertStatus.ACKNOWLEDGED,
                    ]),
                )
            )
            .group_by(Alert.building_id)
        )

        if building_ids:
            query = query.where(Alert.building_id.in_(building_ids))

        result = await self.db.execute(query)
        rows = result.all()
        return {str(row[0]): row[1] for row in rows}

    async def get_device_by_serial(self, serial_number: str) -> IoTDevice | None:
        """Find device by serial number."""
        result = await self.db.execute(
            select(IoTDevice).where(
                and_(
                    IoTDevice.serial_number == serial_number,
                    IoTDevice.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_status_history(
        self,
        device_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DeviceStatusHistory], int]:
        """Get status history for a device with pagination."""
        # Verify device exists
        device = await self.get_device(device_id)
        if not device:
            raise DeviceError(f"Device {device_id} not found")

        # Base query
        query = select(DeviceStatusHistory).where(
            DeviceStatusHistory.device_id == device_id
        )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and order by most recent first
        query = query.order_by(DeviceStatusHistory.changed_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)

        return list(result.scalars().all()), total
