"""Tests for ChannelService."""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agency import Agency
from app.models.user import User
from app.models.channel import Channel, ChannelType, ChannelMember
from app.models.message import Message, MessageType
from app.models.incident import Incident, IncidentStatus, IncidentPriority, IncidentCategory
from app.services.channel_service import ChannelService
from app.core.security import get_password_hash


@pytest.mark.asyncio
class TestChannelService:
    """Test suite for ChannelService."""

    async def test_create_channel_basic(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test creating a basic channel."""
        service = ChannelService(db_session)

        channel = await service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
            description="Test Description",
            agency_id=test_agency.id,
        )

        assert channel.id is not None
        assert channel.name == "Test Channel"
        assert channel.description == "Test Description"
        assert channel.channel_type == ChannelType.TEAM
        assert channel.created_by_id == test_user.id
        assert channel.agency_id == test_agency.id
        assert channel.is_private is False
        assert channel.deleted_at is None

    async def test_create_channel_adds_creator_as_admin(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test that channel creator is automatically added as admin member."""
        service = ChannelService(db_session)

        channel = await service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
            agency_id=test_agency.id,
        )

        is_member = await service.is_member(channel.id, test_user.id)
        assert is_member is True

    async def test_create_channel_with_additional_members(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test creating a channel with additional members."""
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

        service = ChannelService(db_session)

        channel = await service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.BROADCAST,
            created_by_id=test_user.id,
            is_private=True,
            member_ids=[user2.id],
        )

        # Both users should be members
        assert await service.is_member(channel.id, test_user.id) is True
        assert await service.is_member(channel.id, user2.id) is True

    async def test_create_direct_channel_new(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test creating a new direct message channel."""
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

        service = ChannelService(db_session)

        channel = await service.create_direct_channel(test_user.id, user2.id)

        assert channel.channel_type == ChannelType.DIRECT
        assert channel.is_private is True
        assert "DM:" in channel.name
        assert test_user.full_name in channel.name
        assert user2.full_name in channel.name

        # Both users should be members
        assert await service.is_member(channel.id, test_user.id) is True
        assert await service.is_member(channel.id, user2.id) is True

    async def test_create_direct_channel_returns_existing(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test that creating a duplicate direct channel returns existing one."""
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

        service = ChannelService(db_session)

        # Create first channel
        channel1 = await service.create_direct_channel(test_user.id, user2.id)

        # Try to create again (reversed user order)
        channel2 = await service.create_direct_channel(user2.id, test_user.id)

        # Should return the same channel
        assert channel1.id == channel2.id

    async def test_create_incident_channel(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test creating an incident channel."""
        # Create an incident
        incident = Incident(
            id=uuid.uuid4(),
            incident_number="INC-001",
            title="Test Incident",
            status=IncidentStatus.NEW,
            priority=IncidentPriority.HIGH,
            category=IncidentCategory.FIRE,
            latitude=40.7128,
            longitude=-74.0060,
            reported_at=datetime.now(timezone.utc),
            agency_id=test_agency.id,
        )
        db_session.add(incident)
        await db_session.commit()

        service = ChannelService(db_session)

        channel = await service.create_incident_channel(
            incident_id=incident.id,
            incident_number=incident.incident_number,
            created_by_id=test_user.id,
            agency_id=test_agency.id,
        )

        assert channel.channel_type == ChannelType.INCIDENT
        assert channel.incident_id == incident.id
        assert f"#{incident.incident_number}" in channel.name
        assert await service.is_member(channel.id, test_user.id) is True

    async def test_create_incident_channel_returns_existing(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test that creating duplicate incident channel returns existing one."""
        # Create an incident
        incident = Incident(
            id=uuid.uuid4(),
            incident_number="INC-001",
            title="Test Incident",
            status=IncidentStatus.NEW,
            priority=IncidentPriority.HIGH,
            category=IncidentCategory.FIRE,
            latitude=40.7128,
            longitude=-74.0060,
            reported_at=datetime.now(timezone.utc),
            agency_id=test_agency.id,
        )
        db_session.add(incident)
        await db_session.commit()

        service = ChannelService(db_session)

        channel1 = await service.create_incident_channel(
            incident_id=incident.id,
            incident_number=incident.incident_number,
            created_by_id=test_user.id,
        )

        channel2 = await service.create_incident_channel(
            incident_id=incident.id,
            incident_number=incident.incident_number,
            created_by_id=test_user.id,
        )

        assert channel1.id == channel2.id

    async def test_get_channel(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test retrieving a channel by ID."""
        service = ChannelService(db_session)

        created = await service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        retrieved = await service.get_channel(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Test Channel"

    async def test_get_channel_returns_none_for_deleted(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test that get_channel returns None for deleted channels."""
        service = ChannelService(db_session)

        channel = await service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        await service.delete_channel(channel.id)

        retrieved = await service.get_channel(channel.id)
        assert retrieved is None

    async def test_get_user_channels(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test retrieving all channels for a user."""
        service = ChannelService(db_session)

        # Create multiple channels
        await service.create_channel(
            name="Channel 1",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )
        await service.create_channel(
            name="Channel 2",
            channel_type=ChannelType.BROADCAST,
            created_by_id=test_user.id,
        )

        channels = await service.get_user_channels(test_user.id)

        assert len(channels) == 2

    async def test_get_user_channels_filter_by_type(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test filtering user channels by type."""
        service = ChannelService(db_session)

        await service.create_channel(
            name="Public Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )
        await service.create_channel(
            name="Private Channel",
            channel_type=ChannelType.BROADCAST,
            created_by_id=test_user.id,
        )

        public_channels = await service.get_user_channels(test_user.id, channel_type=ChannelType.TEAM)

        assert len(public_channels) == 1
        assert public_channels[0].channel_type == ChannelType.TEAM

    async def test_get_user_channels_excludes_archived(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test that archived channels are excluded by default."""
        service = ChannelService(db_session)

        channel = await service.create_channel(
            name="Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        await service.archive_channel(channel.id)

        channels = await service.get_user_channels(test_user.id)
        assert len(channels) == 0

        channels_with_archived = await service.get_user_channels(test_user.id, include_archived=True)
        assert len(channels_with_archived) == 1

    async def test_add_member(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test adding a member to a channel."""
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

        service = ChannelService(db_session)

        channel = await service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        await service.add_member(channel.id, user2.id)

        assert await service.is_member(channel.id, user2.id) is True

    async def test_add_member_creates_system_message(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test that adding a member creates a system message."""
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

        service = ChannelService(db_session)

        channel = await service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        await service.add_member(channel.id, user2.id)
        await db_session.commit()

        # Check for system message (not in direct channels)
        from sqlalchemy import select
        result = await db_session.execute(
            select(Message).where(Message.channel_id == channel.id, Message.message_type == MessageType.SYSTEM)
        )
        messages = result.scalars().all()
        assert any("joined" in msg.content for msg in messages)

    async def test_add_member_idempotent(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test that adding same member twice is idempotent."""
        service = ChannelService(db_session)

        channel = await service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        # Add twice
        member1 = await service.add_member(channel.id, test_user.id)
        member2 = await service.add_member(channel.id, test_user.id)

        assert member1.id == member2.id

    async def test_remove_member(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test removing a member from a channel."""
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

        service = ChannelService(db_session)

        channel = await service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
            member_ids=[user2.id],
        )

        result = await service.remove_member(channel.id, user2.id)

        assert result is True
        assert await service.is_member(channel.id, user2.id) is False

    async def test_remove_member_creates_system_message(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test that removing a member creates a system message."""
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

        service = ChannelService(db_session)

        channel = await service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
            member_ids=[user2.id],
        )

        await service.remove_member(channel.id, user2.id)

        # Check for system message
        from sqlalchemy import select
        result = await db_session.execute(
            select(Message).where(Message.channel_id == channel.id, Message.message_type == MessageType.SYSTEM)
        )
        messages = result.scalars().all()
        assert any("left" in msg.content for msg in messages)

    async def test_remove_member_returns_false_if_not_member(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test that removing non-member returns False."""
        service = ChannelService(db_session)

        channel = await service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        random_user_id = uuid.uuid4()
        result = await service.remove_member(channel.id, random_user_id)

        assert result is False

    async def test_is_member(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test checking if user is member of channel."""
        service = ChannelService(db_session)

        channel = await service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        assert await service.is_member(channel.id, test_user.id) is True

        random_user_id = uuid.uuid4()
        assert await service.is_member(channel.id, random_user_id) is False

    async def test_update_channel(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test updating channel details."""
        service = ChannelService(db_session)

        channel = await service.create_channel(
            name="Old Name",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
            description="Old Description",
        )

        updated = await service.update_channel(
            channel.id,
            name="New Name",
            description="New Description",
        )

        assert updated is not None
        assert updated.name == "New Name"
        assert updated.description == "New Description"

    async def test_update_channel_returns_none_for_nonexistent(self, db_session: AsyncSession):
        """Test updating nonexistent channel returns None."""
        service = ChannelService(db_session)

        result = await service.update_channel(uuid.uuid4(), name="Test")

        assert result is None

    async def test_archive_channel(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test archiving a channel."""
        service = ChannelService(db_session)

        channel = await service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        archived = await service.archive_channel(channel.id)

        assert archived is not None
        assert archived.is_archived is True

    async def test_delete_channel(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test soft deleting a channel."""
        service = ChannelService(db_session)

        channel = await service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        result = await service.delete_channel(channel.id)

        assert result is True

        # Channel should not be retrievable
        retrieved = await service.get_channel(channel.id)
        assert retrieved is None

    async def test_delete_channel_returns_false_for_nonexistent(self, db_session: AsyncSession):
        """Test deleting nonexistent channel returns False."""
        service = ChannelService(db_session)

        result = await service.delete_channel(uuid.uuid4())

        assert result is False

    async def test_get_channel_for_incident(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test retrieving channel for an incident."""
        # Create an incident
        incident = Incident(
            id=uuid.uuid4(),
            incident_number="INC-001",
            title="Test Incident",
            status=IncidentStatus.NEW,
            priority=IncidentPriority.HIGH,
            category=IncidentCategory.FIRE,
            latitude=40.7128,
            longitude=-74.0060,
            reported_at=datetime.now(timezone.utc),
            agency_id=test_agency.id,
        )
        db_session.add(incident)
        await db_session.commit()

        service = ChannelService(db_session)

        channel = await service.create_incident_channel(
            incident_id=incident.id,
            incident_number=incident.incident_number,
            created_by_id=test_user.id,
        )

        retrieved = await service.get_channel_for_incident(incident.id)

        assert retrieved is not None
        assert retrieved.id == channel.id

    async def test_mute_channel(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test muting a channel for a user."""
        service = ChannelService(db_session)

        channel = await service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        result = await service.mute_channel(channel.id, test_user.id, muted=True)

        assert result is True

    async def test_unmute_channel(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test unmuting a channel for a user."""
        service = ChannelService(db_session)

        channel = await service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        await service.mute_channel(channel.id, test_user.id, muted=True)
        result = await service.mute_channel(channel.id, test_user.id, muted=False)

        assert result is True

    async def test_mute_channel_returns_false_for_nonmember(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test muting channel for non-member returns False."""
        service = ChannelService(db_session)

        channel = await service.create_channel(
            name="Test Channel",
            channel_type=ChannelType.TEAM,
            created_by_id=test_user.id,
        )

        random_user_id = uuid.uuid4()
        result = await service.mute_channel(channel.id, random_user_id, muted=True)

        assert result is False
