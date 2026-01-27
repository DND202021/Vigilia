"""IoT Device model for managing microphones, cameras, and sensors."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Float, Integer, Boolean, ForeignKey
from sqlalchemy import Enum as SQLEnum, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.building import Building, FloorPlan


class DeviceType(str, Enum):
    """IoT device type classification."""

    MICROPHONE = "microphone"
    CAMERA = "camera"
    SENSOR = "sensor"
    GATEWAY = "gateway"
    OTHER = "other"


class DeviceStatus(str, Enum):
    """Device operational status."""

    ONLINE = "online"
    OFFLINE = "offline"
    ALERT = "alert"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class IoTDevice(Base, TimestampMixin, SoftDeleteMixin):
    """IoT Device model for building-associated monitoring devices."""

    __tablename__ = "iot_devices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Device identification
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    device_type: Mapped[DeviceType] = mapped_column(
        SQLEnum(DeviceType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    serial_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True, unique=True, index=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    mac_address: Mapped[str | None] = mapped_column(String(17), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    manufacturer: Mapped[str] = mapped_column(String(100), default="Axis", nullable=False)

    # Association with building and floor
    building_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    building: Mapped["Building"] = relationship("Building", backref="devices")

    floor_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("floor_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    floor_plan: Mapped["FloorPlan | None"] = relationship("FloorPlan", backref="devices")

    # Position on floor plan (percentage-based, 0-100)
    position_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    position_y: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Physical location
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Status
    status: Mapped[DeviceStatus] = mapped_column(
        SQLEnum(DeviceStatus, values_callable=lambda x: [e.value for e in x]),
        default=DeviceStatus.OFFLINE,
        nullable=False,
        index=True,
    )
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    connection_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Configuration (detection sensitivities, etc.)
    config: Mapped[dict | None] = mapped_column(JSON, default=dict)

    # Detection capabilities list
    capabilities: Mapped[list | None] = mapped_column(JSON, default=list)

    # Additional metadata
    metadata_extra: Mapped[dict | None] = mapped_column(JSON, default=dict)

    def __repr__(self) -> str:
        return f"<IoTDevice(id={self.id}, name={self.name}, type={self.device_type})>"

    @property
    def is_placed(self) -> bool:
        """Check if device is placed on a floor plan."""
        return self.floor_plan_id is not None and self.position_x is not None and self.position_y is not None
