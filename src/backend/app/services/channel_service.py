"""Channel service for Communication Hub."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.channel import Channel, ChannelType, ChannelMember
from app.models.message import Message, MessageType
from app.models.user import User


class ChannelService:
    """Service for managing communication channels."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_channel(
        self,
        name: str,
        channel_type: ChannelType,
        created_by_id: uuid.UUID,
        description: Optional[str] = None,
        agency_id: Optional[uuid.UUID] = None,
        incident_id: Optional[uuid.UUID] = None,
        is_private: bool = False,
        member_ids: Optional[list[uuid.UUID]] = None,
    ) -> Channel:
        """Create a new channel."""
        channel = Channel(
            name=name,
            description=description,
            channel_type=channel_type,
            agency_id=agency_id,
            incident_id=incident_id,
            created_by_id=created_by_id,
            is_private=is_private,
        )
        self.db.add(channel)
        await self.db.flush()

        # Add creator as admin member
        await self.add_member(channel.id, created_by_id, is_admin=True)

        # Add additional members
        if member_ids:
            for member_id in member_ids:
                if member_id != created_by_id:
                    await self.add_member(channel.id, member_id)

        await self.db.commit()
        await self.db.refresh(channel)
        return channel

    async def create_direct_channel(
        self,
        user1_id: uuid.UUID,
        user2_id: uuid.UUID,
    ) -> Channel:
        """Create or get existing direct message channel between two users."""
        # Create sorted user IDs string to prevent duplicates
        sorted_ids = sorted([str(user1_id), str(user2_id)])
        direct_user_ids = f"{sorted_ids[0]}:{sorted_ids[1]}"

        # Check for existing channel
        result = await self.db.execute(
            select(Channel).where(
                and_(
                    Channel.channel_type == ChannelType.DIRECT,
                    Channel.direct_user_ids == direct_user_ids,
                    Channel.deleted_at.is_(None),
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        # Get user names for channel name
        user1_result = await self.db.execute(select(User).where(User.id == user1_id))
        user2_result = await self.db.execute(select(User).where(User.id == user2_id))
        user1 = user1_result.scalar_one_or_none()
        user2 = user2_result.scalar_one_or_none()

        name = f"DM: {user1.full_name if user1 else 'User'} & {user2.full_name if user2 else 'User'}"

        channel = Channel(
            name=name,
            channel_type=ChannelType.DIRECT,
            direct_user_ids=direct_user_ids,
            created_by_id=user1_id,
            is_private=True,
        )
        self.db.add(channel)
        await self.db.flush()

        # Add both users as members
        await self.add_member(channel.id, user1_id)
        await self.add_member(channel.id, user2_id)

        await self.db.commit()
        await self.db.refresh(channel)
        return channel

    async def create_incident_channel(
        self,
        incident_id: uuid.UUID,
        incident_number: str,
        created_by_id: uuid.UUID,
        agency_id: Optional[uuid.UUID] = None,
    ) -> Channel:
        """Auto-create channel for an incident."""
        # Check for existing incident channel
        result = await self.db.execute(
            select(Channel).where(
                and_(
                    Channel.channel_type == ChannelType.INCIDENT,
                    Channel.incident_id == incident_id,
                    Channel.deleted_at.is_(None),
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        channel = Channel(
            name=f"Incident #{incident_number}",
            description=f"Communication channel for incident {incident_number}",
            channel_type=ChannelType.INCIDENT,
            incident_id=incident_id,
            agency_id=agency_id,
            created_by_id=created_by_id,
        )
        self.db.add(channel)
        await self.db.flush()

        # Add creator as member
        await self.add_member(channel.id, created_by_id, is_admin=True)

        # Create system message
        system_message = Message(
            channel_id=channel.id,
            sender_id=None,
            message_type=MessageType.SYSTEM,
            content=f"Channel created for Incident #{incident_number}",
        )
        self.db.add(system_message)

        await self.db.commit()
        await self.db.refresh(channel)
        return channel

    async def get_channel(self, channel_id: uuid.UUID) -> Optional[Channel]:
        """Get channel by ID with members."""
        result = await self.db.execute(
            select(Channel)
            .options(
                selectinload(Channel.members).selectinload(ChannelMember.user),
                selectinload(Channel.created_by),
            )
            .where(
                and_(
                    Channel.id == channel_id,
                    Channel.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_user_channels(
        self,
        user_id: uuid.UUID,
        channel_type: Optional[ChannelType] = None,
        include_archived: bool = False,
    ) -> list[Channel]:
        """Get all channels for a user."""
        query = (
            select(Channel)
            .join(ChannelMember)
            .options(
                selectinload(Channel.members).selectinload(ChannelMember.user),
            )
            .where(
                and_(
                    ChannelMember.user_id == user_id,
                    Channel.deleted_at.is_(None),
                )
            )
        )

        if channel_type:
            query = query.where(Channel.channel_type == channel_type)

        if not include_archived:
            query = query.where(Channel.is_archived == False)

        query = query.order_by(Channel.last_message_at.desc().nullslast())

        result = await self.db.execute(query)
        return list(result.scalars().unique().all())

    async def add_member(
        self,
        channel_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool = False,
    ) -> ChannelMember:
        """Add a member to a channel."""
        # Check if already a member
        result = await self.db.execute(
            select(ChannelMember).where(
                and_(
                    ChannelMember.channel_id == channel_id,
                    ChannelMember.user_id == user_id,
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        member = ChannelMember(
            channel_id=channel_id,
            user_id=user_id,
            is_admin=is_admin,
        )
        self.db.add(member)
        await self.db.flush()

        # Create system message for join
        channel = await self.get_channel(channel_id)
        if channel and channel.channel_type != ChannelType.DIRECT:
            user_result = await self.db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if user:
                system_message = Message(
                    channel_id=channel_id,
                    sender_id=None,
                    message_type=MessageType.SYSTEM,
                    content=f"{user.full_name} joined the channel",
                )
                self.db.add(system_message)

        return member

    async def remove_member(self, channel_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Remove a member from a channel."""
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

        # Get user name for system message
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        await self.db.delete(member)

        # Create system message for leave
        channel = await self.get_channel(channel_id)
        if channel and channel.channel_type != ChannelType.DIRECT and user:
            system_message = Message(
                channel_id=channel_id,
                sender_id=None,
                message_type=MessageType.SYSTEM,
                content=f"{user.full_name} left the channel",
            )
            self.db.add(system_message)

        await self.db.commit()
        return True

    async def is_member(self, channel_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Check if user is a member of a channel."""
        result = await self.db.execute(
            select(ChannelMember).where(
                and_(
                    ChannelMember.channel_id == channel_id,
                    ChannelMember.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def update_channel(
        self,
        channel_id: uuid.UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_archived: Optional[bool] = None,
    ) -> Optional[Channel]:
        """Update channel details."""
        channel = await self.get_channel(channel_id)
        if not channel:
            return None

        if name is not None:
            channel.name = name
        if description is not None:
            channel.description = description
        if is_archived is not None:
            channel.is_archived = is_archived

        await self.db.commit()
        await self.db.refresh(channel)
        return channel

    async def archive_channel(self, channel_id: uuid.UUID) -> Optional[Channel]:
        """Archive a channel."""
        return await self.update_channel(channel_id, is_archived=True)

    async def delete_channel(self, channel_id: uuid.UUID) -> bool:
        """Soft delete a channel."""
        channel = await self.get_channel(channel_id)
        if not channel:
            return False

        channel.deleted_at = datetime.now(timezone.utc)
        await self.db.commit()
        return True

    async def get_channel_for_incident(self, incident_id: uuid.UUID) -> Optional[Channel]:
        """Get the channel associated with an incident."""
        result = await self.db.execute(
            select(Channel)
            .options(selectinload(Channel.members))
            .where(
                and_(
                    Channel.incident_id == incident_id,
                    Channel.channel_type == ChannelType.INCIDENT,
                    Channel.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    async def mute_channel(
        self,
        channel_id: uuid.UUID,
        user_id: uuid.UUID,
        muted: bool = True,
    ) -> bool:
        """Mute/unmute a channel for a user."""
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

        member.is_muted = muted
        await self.db.commit()
        return True
