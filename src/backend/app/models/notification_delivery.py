"""Notification delivery tracking model for delivery status and retry management."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.alert import Alert
    from app.models.user import User


class DeliveryStatus(str, Enum):
    """Delivery status tracking for notification lifecycle."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


class DeliveryChannel(str, Enum):
    """Delivery channel types for notifications."""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    CALL = "call"


class NotificationDelivery(Base, TimestampMixin):
    """Tracks notification delivery attempts across channels with retry support."""

    __tablename__ = "notification_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Foreign keys
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert: Mapped["Alert"] = relationship("Alert", backref="notification_deliveries")

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user: Mapped["User"] = relationship("User", backref="notification_deliveries")

    # Delivery tracking
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default=DeliveryStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    # External service tracking
    external_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="SendGrid message ID, Twilio SID, etc.",
    )

    # Retry management
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Status timestamps
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<NotificationDelivery(id={self.id}, alert_id={self.alert_id}, user_id={self.user_id}, channel={self.channel}, status={self.status})>"


# Create composite indexes for common queries
Index(
    "ix_notification_deliveries_alert_status",
    NotificationDelivery.alert_id,
    NotificationDelivery.status,
)
Index(
    "ix_notification_deliveries_user_status",
    NotificationDelivery.user_id,
    NotificationDelivery.status,
)
