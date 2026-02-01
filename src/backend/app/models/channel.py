"""Channel model for Communication Hub."""

import uuid
from enum import Enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Boolean, ForeignKey, Enum as SQLEnum, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.agency import Agency
    from app.models.incident import Incident
    from app.models.message import Message


class ChannelType(str, Enum):
    """Types of communication channels."""

    DIRECT = "direct"  # 1:1 user messaging
    INCIDENT = "incident"  # Auto-created for incidents
    TEAM = "team"  # Team/unit channels
    BROADCAST = "broadcast"  # Agency-wide broadcasts (admin only)


class Channel(Base, TimestampMixin, SoftDeleteMixin):
    """Communication channel model."""

    __tablename__ = "channels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Channel info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    channel_type: Mapped[ChannelType] = mapped_column(
        SQLEnum(ChannelType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )

    # For direct messages - store sorted user IDs to prevent duplicates
    direct_user_ids: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)

    # Agency scope (null for system-wide or cross-agency)
    agency_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agencies.id"),
        nullable=True,
        index=True,
    )
    agency: Mapped[Optional["Agency"]] = relationship("Agency")

    # Incident association (for incident channels)
    incident_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id"),
        nullable=True,
        index=True,
    )
    incident: Mapped[Optional["Incident"]] = relationship("Incident")

    # Creator
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])

    # Channel settings
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    members: Mapped[list["ChannelMember"]] = relationship(
        "ChannelMember",
        back_populates="channel",
        cascade="all, delete-orphan",
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="channel",
        cascade="all, delete-orphan",
    )

    # Cache for quick access
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    message_count: Mapped[int] = mapped_column(default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<Channel(id={self.id}, name={self.name}, type={self.channel_type.value})>"


class ChannelMember(Base, TimestampMixin):
    """Channel membership model."""

    __tablename__ = "channel_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped["Channel"] = relationship("Channel", back_populates="members")

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    user: Mapped["User"] = relationship("User")

    # Membership settings
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Read tracking
    last_read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    unread_count: Mapped[int] = mapped_column(default=0, nullable=False)

    # Joined timestamp
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ChannelMember(channel_id={self.channel_id}, user_id={self.user_id})>"
