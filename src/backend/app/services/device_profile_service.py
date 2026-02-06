"""Device profile management service."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device_profile import DeviceProfile


class DeviceProfileError(Exception):
    """Device profile related errors."""
    pass


class DeviceProfileService:
    """Service for device profile CRUD and seed operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_profile(
        self,
        name: str,
        device_type: str,
        description: str | None = None,
        telemetry_schema: list | None = None,
        attributes_server: dict | None = None,
        attributes_client: dict | None = None,
        alert_rules: list | None = None,
        default_config: dict | None = None,
        is_default: bool = False,
    ) -> DeviceProfile:
        """Create a new device profile."""
        profile = DeviceProfile(
            id=uuid.uuid4(),
            name=name,
            device_type=device_type,
            description=description,
            telemetry_schema=telemetry_schema or [],
            attributes_server=attributes_server or {},
            attributes_client=attributes_client or {},
            alert_rules=alert_rules or [],
            default_config=default_config or {},
            is_default=is_default,
        )

        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def get_profile(self, profile_id: uuid.UUID) -> DeviceProfile | None:
        """Get device profile by ID."""
        result = await self.db.execute(
            select(DeviceProfile).where(
                and_(
                    DeviceProfile.id == profile_id,
                    DeviceProfile.deleted_at.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_profiles(
        self,
        device_type: str | None = None,
        include_deleted: bool = False
    ) -> list[DeviceProfile]:
        """List device profiles with optional filters."""
        query = select(DeviceProfile)

        if not include_deleted:
            query = query.where(DeviceProfile.deleted_at.is_(None))

        if device_type:
            query = query.where(DeviceProfile.device_type == device_type)

        query = query.order_by(DeviceProfile.name)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_profile(
        self,
        profile_id: uuid.UUID,
        **kwargs
    ) -> DeviceProfile:
        """Update device profile attributes."""
        profile = await self.get_profile(profile_id)
        if not profile:
            raise DeviceProfileError(f"Device profile {profile_id} not found")

        # Only update provided fields
        allowed_fields = [
            'name', 'description', 'device_type', 'telemetry_schema',
            'attributes_server', 'attributes_client', 'alert_rules',
            'default_config', 'is_default'
        ]

        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                setattr(profile, key, value)

        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def delete_profile(self, profile_id: uuid.UUID) -> DeviceProfile:
        """Soft delete a device profile."""
        profile = await self.get_profile(profile_id)
        if not profile:
            raise DeviceProfileError(f"Device profile {profile_id} not found")

        profile.deleted_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def seed_default_profiles(self) -> list[DeviceProfile]:
        """Create default device profiles (idempotent)."""
        # Check if seed profiles already exist
        result = await self.db.execute(
            select(DeviceProfile).where(DeviceProfile.is_default == True)
        )
        existing = list(result.scalars().all())
        if existing:
            return existing

        # Create three seed profiles
        profiles = []

        # 1. Axis M3066-V Microphone
        axis_mic = DeviceProfile(
            id=uuid.uuid4(),
            name="Axis M3066-V Microphone",
            device_type="microphone",
            description="Axis M3066-V network microphone with audio analytics for gunshot, scream, and glass break detection",
            telemetry_schema=[
                {"name": "sound_level", "type": "numeric", "unit": "dB", "min": 0, "max": 130},
                {"name": "detection_event", "type": "string", "enum": ["gunshot", "scream", "glass_break", "explosion", "other"]},
                {"name": "detection_confidence", "type": "numeric", "unit": "percent", "min": 0, "max": 100},
                {"name": "is_active", "type": "boolean"},
            ],
            attributes_server={"manufacturer": "Axis", "model": "M3066-V", "protocol": "http", "audio_analytics": True},
            attributes_client={"ip_address": "", "mac_address": "", "firmware_version": ""},
            alert_rules=[
                {"name": "Gunshot Detected", "metric": "detection_event", "condition": "eq", "threshold": "gunshot", "severity": "critical", "cooldown_seconds": 60},
                {"name": "High Sound Level", "metric": "sound_level", "condition": "gt", "threshold": 100, "severity": "high", "cooldown_seconds": 300},
                {"name": "Scream Detected", "metric": "detection_event", "condition": "eq", "threshold": "scream", "severity": "high", "cooldown_seconds": 120},
            ],
            default_config={"sample_rate_hz": 16000, "sensitivity": 0.7, "enabled_detections": ["gunshot", "scream", "glass_break"]},
            is_default=True,
        )
        profiles.append(axis_mic)
        self.db.add(axis_mic)

        # 2. Generic Camera
        generic_camera = DeviceProfile(
            id=uuid.uuid4(),
            name="Generic Camera",
            device_type="camera",
            description="Generic IP camera with motion detection and video analytics",
            telemetry_schema=[
                {"name": "motion_detected", "type": "boolean"},
                {"name": "motion_score", "type": "numeric", "unit": "percent", "min": 0, "max": 100},
                {"name": "person_count", "type": "numeric", "unit": "count", "min": 0, "max": 1000},
                {"name": "fps", "type": "numeric", "unit": "frames/s", "min": 0, "max": 120},
                {"name": "is_recording", "type": "boolean"},
            ],
            attributes_server={"manufacturer": "Generic", "protocol": "rtsp"},
            attributes_client={"ip_address": "", "mac_address": "", "firmware_version": "", "resolution": ""},
            alert_rules=[
                {"name": "Motion Detected", "metric": "motion_detected", "condition": "eq", "threshold": True, "severity": "medium", "cooldown_seconds": 60},
                {"name": "High Person Count", "metric": "person_count", "condition": "gt", "threshold": 50, "severity": "high", "cooldown_seconds": 300},
            ],
            default_config={"resolution": "1080p", "fps": 30, "motion_sensitivity": 0.5, "recording_mode": "motion"},
            is_default=True,
        )
        profiles.append(generic_camera)
        self.db.add(generic_camera)

        # 3. Generic Sensor
        generic_sensor = DeviceProfile(
            id=uuid.uuid4(),
            name="Generic Sensor",
            device_type="sensor",
            description="Generic environmental sensor for temperature, humidity, and air quality monitoring",
            telemetry_schema=[
                {"name": "temperature", "type": "numeric", "unit": "celsius", "min": -40, "max": 85},
                {"name": "humidity", "type": "numeric", "unit": "percent", "min": 0, "max": 100},
                {"name": "air_quality_index", "type": "numeric", "unit": "aqi", "min": 0, "max": 500},
                {"name": "battery_level", "type": "numeric", "unit": "percent", "min": 0, "max": 100},
                {"name": "tamper_detected", "type": "boolean"},
            ],
            attributes_server={"manufacturer": "Generic", "protocol": "mqtt"},
            attributes_client={"ip_address": "", "mac_address": "", "firmware_version": "", "battery_type": ""},
            alert_rules=[
                {"name": "High Temperature", "metric": "temperature", "condition": "gt", "threshold": 60, "severity": "high", "cooldown_seconds": 300},
                {"name": "Low Battery", "metric": "battery_level", "condition": "lt", "threshold": 10, "severity": "medium", "cooldown_seconds": 3600},
                {"name": "Tamper Alert", "metric": "tamper_detected", "condition": "eq", "threshold": True, "severity": "critical", "cooldown_seconds": 60},
            ],
            default_config={"sample_interval_seconds": 60, "power_mode": "normal"},
            is_default=True,
        )
        profiles.append(generic_sensor)
        self.db.add(generic_sensor)

        await self.db.commit()
        for profile in profiles:
            await self.db.refresh(profile)

        return profiles
