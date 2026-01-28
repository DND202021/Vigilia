"""Device Status History model for tracking status changes."""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DeviceStatusHistory(Base):
    """Tracks device status changes over time."""

    __tablename__ = "device_status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iot_devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    old_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,  # null for initial status
    )
    new_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(),
        nullable=False,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,  # optional reason for change
    )
    connection_quality: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Relationships
    device = relationship("IoTDevice", backref="status_history")

    def __repr__(self) -> str:
        return f"<DeviceStatusHistory(id={self.id}, device_id={self.device_id}, {self.old_status} -> {self.new_status})>"
