"""Tests for MessageService."""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agency import Agency
from app.models.user import User
from app.models.channel import Channel, ChannelType
from app.models.message import Message, MessageType, MessagePriority
from app.services.channel_service import ChannelService
from app.services.message_service import MessageService


@pytest.mark.asyncio
class TestMessageService:
    """Test suite for MessageService."""

    async def test_send_message_basic(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test sending a basic text message."""
        # Create a channel
        channel_service = ChannelService(db_session)
        channel = await channel_service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        # Send message
        message_service = MessageService(db_session)
        message = await message_service.send_message(
            channel_id=channel.id,
            sender_id=test_user.id,
            content="Hello, World!",
        )

        assert message.id is not None
        assert message.channel_id == channel.id
        assert message.sender_id == test_user.id
        assert message.content == "Hello, World!"
        assert message.message_type == MessageType.TEXT
        assert message.priority == MessagePriority.NORMAL
        assert message.deleted_at is None

    async def test_send_message_with_attachment(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test sending a message with an attachment."""
        channel_service = ChannelService(db_session)
        channel = await channel_service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        message_service = MessageService(db_session)
        message = await message_service.send_message(
            channel_id=channel.id,
            sender_id=test_user.id,
            content="Check this out",
            message_type=MessageType.FILE,
            attachment_url="https://example.com/file.pdf",
            attachment_name="file.pdf",
            attachment_size=1024,
            attachment_mime_type="application/pdf",
        )

        assert message.message_type == MessageType.FILE
        assert message.attachment_url == "https://example.com/file.pdf"
        assert message.attachment_name == "file.pdf"
        assert message.attachment_size == 1024
        assert message.attachment_mime_type == "application/pdf"

    async def test_send_message_updates_channel_stats(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test that sending a message updates channel statistics."""
        channel_service = ChannelService(db_session)
        channel = await channel_service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        initial_count = channel.message_count

        message_service = MessageService(db_session)
        await message_service.send_message(
            channel_id=channel.id,
            sender_id=test_user.id,
            content="Test message",
        )

        # Refresh channel
        await db_session.refresh(channel)

        assert channel.message_count == initial_count + 1
        assert channel.last_message_at is not None

    async def test_get_message(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test retrieving a message by ID."""
        channel_service = ChannelService(db_session)
        channel = await channel_service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        message_service = MessageService(db_session)
        sent = await message_service.send_message(
            channel_id=channel.id,
            sender_id=test_user.id,
            content="Test message",
        )

        retrieved = await message_service.get_message(sent.id)

        assert retrieved is not None
        assert retrieved.id == sent.id
        assert retrieved.content == "Test message"

    async def test_get_channel_messages(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test retrieving messages from a channel."""
        channel_service = ChannelService(db_session)
        channel = await channel_service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        message_service = MessageService(db_session)
        # Send multiple messages
        await message_service.send_message(
            channel_id=channel.id,
            sender_id=test_user.id,
            content="Message 1",
        )
        await message_service.send_message(
            channel_id=channel.id,
            sender_id=test_user.id,
            content="Message 2",
        )
        await message_service.send_message(
            channel_id=channel.id,
            sender_id=test_user.id,
            content="Message 3",
        )

        messages = await message_service.get_channel_messages(channel.id)

        assert len(messages) >= 3

    async def test_mark_as_read(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test marking a message as read."""
        from app.core.security import get_password_hash

        # Create another user
        user2 = User(
            id=uuid.uuid4(),
            email="user2@test.com",
            full_name="User Two",
            hashed_password=get_password_hash("password"),
            agency_id=test_agency.id,
        )
        db_session.add(user2)
        await db_session.commit()

        channel_service = ChannelService(db_session)
        channel = await channel_service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
            member_ids=[user2.id],
        )

        message_service = MessageService(db_session)
        message = await message_service.send_message(
            channel_id=channel.id,
            sender_id=test_user.id,
            content="Test message",
        )

        # User2 marks as read
        result = await message_service.mark_as_read(channel.id, user2.id)

        assert result is True

    async def test_delete_message(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test soft deleting a message."""
        channel_service = ChannelService(db_session)
        channel = await channel_service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        message_service = MessageService(db_session)
        message = await message_service.send_message(
            channel_id=channel.id,
            sender_id=test_user.id,
            content="Test message",
        )

        result = await message_service.delete_message(message.id, test_user.id)

        assert result is True

        # Message should not be retrievable
        retrieved = await message_service.get_message(message.id)
        assert retrieved is None

    async def test_edit_message(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test editing a message."""
        channel_service = ChannelService(db_session)
        channel = await channel_service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        message_service = MessageService(db_session)
        message = await message_service.send_message(
            channel_id=channel.id,
            sender_id=test_user.id,
            content="Original content",
        )

        edited = await message_service.edit_message(message.id, test_user.id, "Edited content")

        assert edited is not None
        assert edited.content == "Edited content"
        assert edited.edited_at is not None

    async def test_add_reaction(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test adding a reaction to a message."""
        channel_service = ChannelService(db_session)
        channel = await channel_service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        message_service = MessageService(db_session)
        message = await message_service.send_message(
            channel_id=channel.id,
            sender_id=test_user.id,
            content="Test message",
        )

        reaction = await message_service.add_reaction(
            message_id=message.id,
            user_id=test_user.id,
            emoji="👍",
        )

        assert reaction is not None
        assert reaction.message_id == message.id
        assert reaction.user_id == test_user.id
        assert reaction.emoji == "👍"

    async def test_remove_reaction(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test removing a reaction from a message."""
        channel_service = ChannelService(db_session)
        channel = await channel_service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        message_service = MessageService(db_session)
        message = await message_service.send_message(
            channel_id=channel.id,
            sender_id=test_user.id,
            content="Test message",
        )

        await message_service.add_reaction(
            message_id=message.id,
            user_id=test_user.id,
            emoji="👍",
        )

        result = await message_service.remove_reaction(
            message_id=message.id,
            user_id=test_user.id,
            emoji="👍",
        )

        assert result is True

    async def test_send_message_with_reply(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test sending a message as a reply to another message."""
        channel_service = ChannelService(db_session)
        channel = await channel_service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        message_service = MessageService(db_session)
        original = await message_service.send_message(
            channel_id=channel.id,
            sender_id=test_user.id,
            content="Original message",
        )

        reply = await message_service.send_message(
            channel_id=channel.id,
            sender_id=test_user.id,
            content="Reply message",
            reply_to_id=original.id,
        )

        assert reply.reply_to_id == original.id

    async def test_send_message_with_location(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test sending a message with location data."""
        channel_service = ChannelService(db_session)
        channel = await channel_service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        message_service = MessageService(db_session)
        message = await message_service.send_message(
            channel_id=channel.id,
            sender_id=test_user.id,
            content="I'm here",
            message_type=MessageType.LOCATION,
            location_lat=40.7128,
            location_lng=-74.0060,
            location_address="New York, NY",
        )

        assert message.message_type == MessageType.LOCATION
        assert message.location_lat == 40.7128
        assert message.location_lng == -74.0060
        assert message.location_address == "New York, NY"

    async def test_send_high_priority_message(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test sending a high-priority message."""
        channel_service = ChannelService(db_session)
        channel = await channel_service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        message_service = MessageService(db_session)
        message = await message_service.send_message(
            channel_id=channel.id,
            sender_id=test_user.id,
            content="URGENT",
            priority=MessagePriority.HIGH,
        )

        assert message.priority == MessagePriority.HIGH
