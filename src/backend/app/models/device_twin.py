"""Device twin model for desired vs reported state synchronization."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Integer, Boolean, DateTime, JSON, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.device import IoTDevice


class DeviceTwin(Base, TimestampMixin):
    """Device twin for desired vs reported state synchronization."""

    __tablename__ = "device_twins"

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iot_devices.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Desired state - set by backend, read by device
    desired_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    desired_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    desired_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Reported state - set by device, read by backend
    reported_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    reported_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reported_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Sync status
    is_synced: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationship
    device: Mapped["IoTDevice"] = relationship("IoTDevice", back_populates="twin")

    @property
    def config_delta(self) -> dict:
        """Return keys that differ between desired and reported."""
        desired = self.desired_config
        reported = self.reported_config
        delta = {}
        for key in desired:
            if key not in reported or desired[key] != reported[key]:
                delta[key] = {"desired": desired[key], "reported": reported.get(key)}
        return delta

    def __repr__(self) -> str:
        return f"<DeviceTwin(device_id={self.device_id}, synced={self.is_synced}, version={self.desired_version})>"
