"""Device profile model for defining device capabilities and configurations."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.device import IoTDevice


class DeviceProfile(Base, TimestampMixin, SoftDeleteMixin):
    """Device profile template defining expected capabilities and configurations."""

    __tablename__ = "device_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Telemetry schema: [{"name": "temperature", "type": "numeric", "unit": "celsius", "min": -40, "max": 85}]
    telemetry_schema: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Server-side attributes: {"manufacturer": "Axis", "model": "M3066-V"}
    attributes_server: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Client-side attributes: {"ip_address": "...", "mac_address": "..."}
    attributes_client: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Alert rules: [{"name": "High dB", "metric": "sound_level", "condition": "gt", "threshold": 85, "severity": "high"}]
    alert_rules: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Default device configuration
    default_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    devices: Mapped[list["IoTDevice"]] = relationship("IoTDevice", back_populates="profile")

    def __repr__(self) -> str:
        return f"<DeviceProfile(id={self.id}, name={self.name}, type={self.device_type})>"
