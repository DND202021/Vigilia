"""Add Communication Hub tables (channels, messages).

Revision ID: 014
Revises: 013
Create Date: 2025-02-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create channels, channel_members, messages, and message_reactions tables."""

    # Create channel_type enum
    channel_type_enum = postgresql.ENUM(
        'direct', 'incident', 'team', 'broadcast',
        name='channeltype',
        create_type=False,
    )
    channel_type_enum.create(op.get_bind(), checkfirst=True)

    # Create message_type enum
    message_type_enum = postgresql.ENUM(
        'text', 'file', 'image', 'location', 'system',
        name='messagetype',
        create_type=False,
    )
    message_type_enum.create(op.get_bind(), checkfirst=True)

    # Create message_priority enum
    message_priority_enum = postgresql.ENUM(
        'normal', 'high', 'urgent',
        name='messagepriority',
        create_type=False,
    )
    message_priority_enum.create(op.get_bind(), checkfirst=True)

    # Create channels table
    op.create_table(
        'channels',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('channel_type', postgresql.ENUM('direct', 'incident', 'team', 'broadcast', name='channeltype', create_type=False), nullable=False),
        sa.Column('direct_user_ids', sa.String(100), nullable=True, unique=True),
        sa.Column('agency_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_private', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id']),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id']),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_channels_channel_type', 'channels', ['channel_type'])
    op.create_index('ix_channels_agency_id', 'channels', ['agency_id'])
    op.create_index('ix_channels_incident_id', 'channels', ['incident_id'])

    # Create channel_members table
    op.create_table(
        'channel_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_muted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('unread_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_channel_members_channel_id', 'channel_members', ['channel_id'])
    op.create_index('ix_channel_members_user_id', 'channel_members', ['user_id'])
    op.create_index('ix_channel_members_unique', 'channel_members', ['channel_id', 'user_id'], unique=True)

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('message_type', postgresql.ENUM('text', 'file', 'image', 'location', 'system', name='messagetype', create_type=False), nullable=False, server_default='text'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('priority', postgresql.ENUM('normal', 'high', 'urgent', name='messagepriority', create_type=False), nullable=False, server_default='normal'),
        sa.Column('attachment_url', sa.String(500), nullable=True),
        sa.Column('attachment_name', sa.String(255), nullable=True),
        sa.Column('attachment_size', sa.Integer(), nullable=True),
        sa.Column('attachment_mime_type', sa.String(100), nullable=True),
        sa.Column('location_lat', sa.Float(), nullable=True),
        sa.Column('location_lng', sa.Float(), nullable=True),
        sa.Column('location_address', sa.String(500), nullable=True),
        sa.Column('reply_to_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_edited', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_by', postgresql.JSON(), nullable=True),
        sa.Column('extra_data', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id']),
        sa.ForeignKeyConstraint(['reply_to_id'], ['messages.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_messages_channel_id', 'messages', ['channel_id'])
    op.create_index('ix_messages_sender_id', 'messages', ['sender_id'])
    op.create_index('ix_messages_created_at', 'messages', ['created_at'])

    # Create message_reactions table
    op.create_table(
        'message_reactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('emoji', sa.String(10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_message_reactions_message_id', 'message_reactions', ['message_id'])


def downgrade() -> None:
    """Drop Communication Hub tables."""
    op.drop_table('message_reactions')
    op.drop_table('messages')
    op.drop_table('channel_members')
    op.drop_table('channels')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS messagepriority')
    op.execute('DROP TYPE IF EXISTS messagetype')
    op.execute('DROP TYPE IF EXISTS channeltype')
