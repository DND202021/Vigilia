"""Audio clip model for storing audio evidence from detection events."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Float, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.device import IoTDevice
    from app.models.alert import Alert


class AudioClip(Base, TimestampMixin):
    """Audio clip model for storing audio evidence captured during detection events."""

    __tablename__ = "audio_clips"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # References
    alert_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alerts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iot_devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    device: Mapped["IoTDevice"] = relationship("IoTDevice", backref="audio_clips")

    # Audio file data
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    format: Mapped[str] = mapped_column(String(20), default="wav", nullable=False)
    sample_rate: Mapped[int] = mapped_column(Integer, default=16000, nullable=False)

    # Event context
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    peak_level_db: Mapped[float | None] = mapped_column(Float, nullable=True)
    background_level_db: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Timestamps
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Additional metadata
    metadata_extra: Mapped[dict | None] = mapped_column(JSON, default=dict)

    def __repr__(self) -> str:
        return f"<AudioClip(id={self.id}, device_id={self.device_id}, event_type={self.event_type})>"
