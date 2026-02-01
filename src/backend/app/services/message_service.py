"""Message service for Communication Hub."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.channel import Channel, ChannelMember
from app.models.message import Message, MessageType, MessagePriority, MessageReaction


class MessageService:
    """Service for managing messages."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_message(
        self,
        channel_id: uuid.UUID,
        sender_id: uuid.UUID,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        priority: MessagePriority = MessagePriority.NORMAL,
        attachment_url: Optional[str] = None,
        attachment_name: Optional[str] = None,
        attachment_size: Optional[int] = None,
        attachment_mime_type: Optional[str] = None,
        location_lat: Optional[float] = None,
        location_lng: Optional[float] = None,
        location_address: Optional[str] = None,
        reply_to_id: Optional[uuid.UUID] = None,
        extra_data: Optional[dict] = None,
    ) -> Message:
        """Send a message to a channel."""
        message = Message(
            channel_id=channel_id,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
            priority=priority,
            attachment_url=attachment_url,
            attachment_name=attachment_name,
            attachment_size=attachment_size,
            attachment_mime_type=attachment_mime_type,
            location_lat=location_lat,
            location_lng=location_lng,
            location_address=location_address,
            reply_to_id=reply_to_id,
            extra_data=extra_data,
            read_by=[str(sender_id)],  # Sender has read their own message
        )
        self.db.add(message)

        # Update channel stats
        channel_result = await self.db.execute(
            select(Channel).where(Channel.id == channel_id)
        )
        channel = channel_result.scalar_one_or_none()
        if channel:
            channel.last_message_at = datetime.now(timezone.utc)
            channel.message_count += 1

        # Update unread counts for other members
        await self.db.execute(
            select(ChannelMember)
            .where(
                and_(
                    ChannelMember.channel_id == channel_id,
                    ChannelMember.user_id != sender_id,
                )
            )
        )
        members_result = await self.db.execute(
            select(ChannelMember).where(
                and_(
                    ChannelMember.channel_id == channel_id,
                    ChannelMember.user_id != sender_id,
                )
            )
        )
        for member in members_result.scalars():
            member.unread_count += 1

        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_message(self, message_id: uuid.UUID) -> Optional[Message]:
        """Get a message by ID."""
        result = await self.db.execute(
            select(Message)
            .options(selectinload(Message.sender), selectinload(Message.reply_to))
            .where(
                and_(
                    Message.id == message_id,
                    Message.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_channel_messages(
        self,
        channel_id: uuid.UUID,
        limit: int = 50,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
    ) -> list[Message]:
        """Get messages for a channel with pagination."""
        query = (
            select(Message)
            .options(selectinload(Message.sender), selectinload(Message.reply_to))
            .where(
                and_(
                    Message.channel_id == channel_id,
                    Message.deleted_at.is_(None),
                )
            )
        )

        if before:
            query = query.where(Message.created_at < before)
        if after:
            query = query.where(Message.created_at > after)

        query = query.order_by(desc(Message.created_at)).limit(limit)

        result = await self.db.execute(query)
        messages = list(result.scalars().all())
        # Reverse to get chronological order
        return list(reversed(messages))

    async def edit_message(
        self,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
        new_content: str,
    ) -> Optional[Message]:
        """Edit a message (only by sender)."""
        message = await self.get_message(message_id)
        if not message or message.sender_id != user_id:
            return None

        message.content = new_content
        message.is_edited = True
        message.edited_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def delete_message(
        self,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> bool:
        """Soft delete a message (by sender or admin)."""
        message = await self.get_message(message_id)
        if not message:
            return False

        # Only sender or admin can delete
        if message.sender_id != user_id and not is_admin:
            return False

        message.deleted_at = datetime.now(timezone.utc)

        # Update channel message count
        channel_result = await self.db.execute(
            select(Channel).where(Channel.id == message.channel_id)
        )
        channel = channel_result.scalar_one_or_none()
        if channel and channel.message_count > 0:
            channel.message_count -= 1

        await self.db.commit()
        return True

    async def mark_as_read(
        self,
        channel_id: uuid.UUID,
        user_id: uuid.UUID,
        up_to_message_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """Mark messages as read for a user."""
        # Update member's last_read_at and reset unread count
        result = await self.db.execute(
            select(ChannelMember).where(
                and_(
                    ChannelMember.channel_id == channel_id,
                    ChannelMember.user_id == user_id,
                )
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            return False

        member.last_read_at = datetime.now(timezone.utc)
        member.unread_count = 0

        # Update read_by on messages
        if up_to_message_id:
            message = await self.get_message(up_to_message_id)
            if message:
                # Mark all messages up to this one as read
                messages_result = await self.db.execute(
                    select(Message).where(
                        and_(
                            Message.channel_id == channel_id,
                            Message.created_at <= message.created_at,
                            Message.deleted_at.is_(None),
                        )
                    )
                )
                for msg in messages_result.scalars():
                    if msg.read_by is None:
                        msg.read_by = []
                    if str(user_id) not in msg.read_by:
                        msg.read_by = msg.read_by + [str(user_id)]

        await self.db.commit()
        return True

    async def search_messages(
        self,
        user_id: uuid.UUID,
        query: str,
        channel_id: Optional[uuid.UUID] = None,
        limit: int = 50,
    ) -> list[Message]:
        """Search messages across user's channels."""
        # Get user's channel IDs
        member_result = await self.db.execute(
            select(ChannelMember.channel_id).where(ChannelMember.user_id == user_id)
        )
        channel_ids = [row[0] for row in member_result.all()]

        if not channel_ids:
            return []

        search_query = (
            select(Message)
            .options(selectinload(Message.sender), selectinload(Message.channel))
            .where(
                and_(
                    Message.channel_id.in_(channel_ids),
                    Message.content.ilike(f"%{query}%"),
                    Message.deleted_at.is_(None),
                )
            )
        )

        if channel_id:
            search_query = search_query.where(Message.channel_id == channel_id)

        search_query = search_query.order_by(desc(Message.created_at)).limit(limit)

        result = await self.db.execute(search_query)
        return list(result.scalars().all())

    async def add_reaction(
        self,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
        emoji: str,
    ) -> MessageReaction:
        """Add a reaction to a message."""
        # Check for existing reaction
        result = await self.db.execute(
            select(MessageReaction).where(
                and_(
                    MessageReaction.message_id == message_id,
                    MessageReaction.user_id == user_id,
                    MessageReaction.emoji == emoji,
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        reaction = MessageReaction(
            message_id=message_id,
            user_id=user_id,
            emoji=emoji,
        )
        self.db.add(reaction)
        await self.db.commit()
        await self.db.refresh(reaction)
        return reaction

    async def remove_reaction(
        self,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
        emoji: str,
    ) -> bool:
        """Remove a reaction from a message."""
        result = await self.db.execute(
            select(MessageReaction).where(
                and_(
                    MessageReaction.message_id == message_id,
                    MessageReaction.user_id == user_id,
                    MessageReaction.emoji == emoji,
                )
            )
        )
        reaction = result.scalar_one_or_none()
        if not reaction:
            return False

        await self.db.delete(reaction)
        await self.db.commit()
        return True

    async def get_message_reactions(self, message_id: uuid.UUID) -> list[MessageReaction]:
        """Get all reactions for a message."""
        result = await self.db.execute(
            select(MessageReaction).where(MessageReaction.message_id == message_id)
        )
        return list(result.scalars().all())

    async def get_unread_count(self, user_id: uuid.UUID) -> dict:
        """Get total unread count and per-channel counts for a user."""
        result = await self.db.execute(
            select(ChannelMember).where(ChannelMember.user_id == user_id)
        )
        members = result.scalars().all()

        total = 0
        by_channel = {}
        for member in members:
            total += member.unread_count
            if member.unread_count > 0:
                by_channel[str(member.channel_id)] = member.unread_count

        return {
            "total": total,
            "by_channel": by_channel,
        }

    async def send_broadcast(
        self,
        agency_id: uuid.UUID,
        sender_id: uuid.UUID,
        content: str,
        priority: MessagePriority = MessagePriority.HIGH,
    ) -> Optional[Message]:
        """Send a broadcast message to agency-wide channel."""
        # Find or create broadcast channel for agency
        result = await self.db.execute(
            select(Channel).where(
                and_(
                    Channel.agency_id == agency_id,
                    Channel.channel_type == "broadcast",
                    Channel.deleted_at.is_(None),
                )
            )
        )
        channel = result.scalar_one_or_none()

        if not channel:
            # Create broadcast channel
            from app.services.channel_service import ChannelService
            channel_service = ChannelService(self.db)
            channel = await channel_service.create_channel(
                name="Agency Broadcast",
                channel_type="broadcast",
                created_by_id=sender_id,
                agency_id=agency_id,
                description="Agency-wide broadcast channel",
            )

        return await self.send_message(
            channel_id=channel.id,
            sender_id=sender_id,
            content=content,
            priority=priority,
        )
