"""Alert model for incoming alerts from various sources."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Float, ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.incident import Incident


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, Enum):
    """Alert processing status."""

    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    PROCESSING = "processing"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class AlertSource(str, Enum):
    """Source of the alert."""

    FUNDAMENTUM = "fundamentum"
    ALARM_SYSTEM = "alarm_system"
    AXIS_MICROPHONE = "axis_microphone"
    SECURITY_SYSTEM = "security_system"
    MANUAL = "manual"
    EXTERNAL_API = "external_api"


class Alert(Base, TimestampMixin):
    """Alert model for incoming alerts from various sources."""

    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Source information
    source: Mapped[AlertSource] = mapped_column(
        SQLEnum(AlertSource),
        nullable=False,
        index=True,
    )
    source_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    source_device_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Classification
    severity: Mapped[AlertSeverity] = mapped_column(
        SQLEnum(AlertSeverity),
        default=AlertSeverity.MEDIUM,
        nullable=False,
        index=True,
    )
    status: Mapped[AlertStatus] = mapped_column(
        SQLEnum(AlertStatus),
        default=AlertStatus.PENDING,
        nullable=False,
        index=True,
    )
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Content
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Location (if available)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    zone: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Raw payload for audit
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Processing timestamps
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Acknowledgment info
    acknowledged_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    acknowledgment_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Dismissal info
    dismissed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    dismissal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Linked incidents
    incidents: Mapped[list["Incident"]] = relationship(
        "Incident",
        back_populates="source_alert",
    )

    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, source={self.source}, severity={self.severity}, status={self.status})>"
