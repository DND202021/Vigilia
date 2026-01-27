"""Notification preference model for user alerting configuration."""

import uuid
from datetime import time
from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, Integer, ForeignKey, Time, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class NotificationPreference(Base, TimestampMixin):
    """Notification preferences per user for alert delivery channels."""

    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # User reference (one preferences record per user)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    user: Mapped["User"] = relationship("User", backref="notification_preferences")

    # Notification channels
    call_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sms_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Building scope: which buildings to receive alerts for
    # Empty list means all buildings
    building_ids: Mapped[list | None] = mapped_column(JSON, default=list)

    # Severity filter: 1=critical only, 2=critical+high, 3=+medium, 4=+low, 5=all
    min_severity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Quiet hours
    quiet_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    quiet_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    quiet_override_critical: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    def __repr__(self) -> str:
        return f"<NotificationPreference(user_id={self.user_id}, call={self.call_enabled}, sms={self.sms_enabled}, email={self.email_enabled})>"
