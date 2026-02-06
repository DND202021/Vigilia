"""Device telemetry model (TimescaleDB hypertable)."""

import uuid
from datetime import datetime

from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DeviceTelemetry(Base):
    """Telemetry hypertable for device time-series data (narrow schema).

    CRITICAL: Do NOT inherit TimestampMixin - hypertables use 'time' column only.
    """

    __tablename__ = "device_telemetry"

    # Time column (MUST be NOT NULL for hypertable, part of composite PK)
    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
    )

    # Device reference (part of composite PK)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iot_devices.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    # Metric identifier (part of composite PK)
    metric_name: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
        nullable=False,
    )

    # Value columns (narrow schema - only one populated per row)
    value_numeric: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_string: Mapped[str | None] = mapped_column(String(500), nullable=True)
    value_bool: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # NO created_at/updated_at - use 'time' column for TimescaleDB
    # NO relationship back to IoTDevice - avoid loading millions of telemetry rows

    def __repr__(self) -> str:
        return f"<DeviceTelemetry(time={self.time}, device_id={self.device_id}, metric={self.metric_name})>"
