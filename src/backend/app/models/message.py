"""Message model for Communication Hub."""

import uuid
from enum import Enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Boolean, ForeignKey, Enum as SQLEnum, Text, DateTime, func, Float
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.channel import Channel


class MessagePriority(str, Enum):
    """Message priority levels."""

    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageType(str, Enum):
    """Types of messages."""

    TEXT = "text"
    FILE = "file"
    IMAGE = "image"
    LOCATION = "location"
    SYSTEM = "system"  # System-generated messages (join, leave, etc.)


class Message(Base, TimestampMixin, SoftDeleteMixin):
    """Message model for communication channels."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Channel association
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped["Channel"] = relationship("Channel", back_populates="messages")

    # Sender (null for system messages)
    sender_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    sender: Mapped[Optional["User"]] = relationship("User")

    # Message content
    message_type: Mapped[MessageType] = mapped_column(
        SQLEnum(MessageType, values_callable=lambda x: [e.value for e in x]),
        default=MessageType.TEXT,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Priority level
    priority: Mapped[MessagePriority] = mapped_column(
        SQLEnum(MessagePriority, values_callable=lambda x: [e.value for e in x]),
        default=MessagePriority.NORMAL,
        nullable=False,
    )

    # File attachment (for FILE and IMAGE types)
    attachment_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    attachment_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    attachment_size: Mapped[Optional[int]] = mapped_column(nullable=True)
    attachment_mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Location sharing (for LOCATION type)
    location_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Reply threading
    reply_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id"),
        nullable=True,
    )
    reply_to: Mapped[Optional["Message"]] = relationship("Message", remote_side=[id])

    # Editing
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Read receipts (stored as JSON array of user IDs)
    read_by: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)

    # Extra data (for extensibility)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, channel_id={self.channel_id}, type={self.message_type.value})>"


class MessageReaction(Base, TimestampMixin):
    """Reactions to messages (emoji reactions)."""

    __tablename__ = "message_reactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    emoji: Mapped[str] = mapped_column(String(10), nullable=False)

    def __repr__(self) -> str:
        return f"<MessageReaction(message_id={self.message_id}, emoji={self.emoji})>"
