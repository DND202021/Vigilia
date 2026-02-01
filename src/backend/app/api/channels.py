"""Channels API endpoints for Communication Hub."""

import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.channel import ChannelType
from app.services.channel_service import ChannelService

router = APIRouter(prefix="/channels", tags=["channels"])


# Request/Response schemas
class ChannelCreate(BaseModel):
    """Schema for creating a channel."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    channel_type: ChannelType = ChannelType.TEAM
    is_private: bool = False
    member_ids: Optional[list[uuid.UUID]] = None


class DirectChannelCreate(BaseModel):
    """Schema for creating a direct message channel."""

    user_id: uuid.UUID


class ChannelUpdate(BaseModel):
    """Schema for updating a channel."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    is_archived: Optional[bool] = None


class ChannelMemberAdd(BaseModel):
    """Schema for adding a member to a channel."""

    user_id: uuid.UUID
    is_admin: bool = False


class ChannelMemberResponse(BaseModel):
    """Response schema for channel member."""

    id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    user_email: str
    is_admin: bool
    is_muted: bool
    unread_count: int
    joined_at: datetime

    class Config:
        from_attributes = True


class ChannelResponse(BaseModel):
    """Response schema for a channel."""

    id: uuid.UUID
    name: str
    description: Optional[str]
    channel_type: ChannelType
    agency_id: Optional[uuid.UUID]
    incident_id: Optional[uuid.UUID]
    is_archived: bool
    is_private: bool
    last_message_at: Optional[datetime]
    message_count: int
    created_at: datetime
    members: list[ChannelMemberResponse] = []

    class Config:
        from_attributes = True


class ChannelListResponse(BaseModel):
    """Response schema for channel list."""

    id: uuid.UUID
    name: str
    channel_type: ChannelType
    is_private: bool
    last_message_at: Optional[datetime]
    unread_count: int = 0

    class Config:
        from_attributes = True


# Endpoints
@router.get("", response_model=list[ChannelListResponse])
async def list_channels(
    channel_type: Optional[ChannelType] = Query(None),
    include_archived: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all channels for current user."""
    service = ChannelService(db)
    channels = await service.get_user_channels(
        user_id=current_user.id,
        channel_type=channel_type,
        include_archived=include_archived,
    )

    result = []
    for channel in channels:
        # Find current user's membership for unread count
        unread = 0
        for member in channel.members:
            if member.user_id == current_user.id:
                unread = member.unread_count
                break

        result.append(ChannelListResponse(
            id=channel.id,
            name=channel.name,
            channel_type=channel.channel_type,
            is_private=channel.is_private,
            last_message_at=channel.last_message_at,
            unread_count=unread,
        ))

    return result


@router.post("", response_model=ChannelResponse, status_code=201)
async def create_channel(
    data: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new channel."""
    # Only admins can create broadcast channels
    if data.channel_type == ChannelType.BROADCAST:
        if not current_user.has_permission("channels:broadcast"):
            raise HTTPException(status_code=403, detail="Only admins can create broadcast channels")

    service = ChannelService(db)
    channel = await service.create_channel(
        name=data.name,
        description=data.description,
        channel_type=data.channel_type,
        created_by_id=current_user.id,
        agency_id=current_user.agency_id,
        is_private=data.is_private,
        member_ids=data.member_ids,
    )

    return await _channel_to_response(channel)


@router.post("/direct", response_model=ChannelResponse, status_code=201)
async def create_direct_channel(
    data: DirectChannelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or get a direct message channel with another user."""
    if data.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot create DM channel with yourself")

    service = ChannelService(db)
    channel = await service.create_direct_channel(
        user1_id=current_user.id,
        user2_id=data.user_id,
    )

    return await _channel_to_response(channel)


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get channel details."""
    service = ChannelService(db)

    # Check membership
    if not await service.is_member(channel_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not a member of this channel")

    channel = await service.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    return await _channel_to_response(channel)


@router.patch("/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: uuid.UUID,
    data: ChannelUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update channel details."""
    service = ChannelService(db)

    # Check membership and admin status
    channel = await service.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    is_admin = False
    for member in channel.members:
        if member.user_id == current_user.id:
            is_admin = member.is_admin
            break
    else:
        raise HTTPException(status_code=403, detail="Not a member of this channel")

    if not is_admin and channel.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only channel admins can update")

    updated = await service.update_channel(
        channel_id=channel_id,
        name=data.name,
        description=data.description,
        is_archived=data.is_archived,
    )

    return await _channel_to_response(updated)


@router.delete("/{channel_id}", status_code=204)
async def delete_channel(
    channel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a channel."""
    service = ChannelService(db)

    channel = await service.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Only creator or system admin can delete
    if channel.created_by_id != current_user.id and not current_user.has_permission("system:admin"):
        raise HTTPException(status_code=403, detail="Only channel creator can delete")

    await service.delete_channel(channel_id)


@router.post("/{channel_id}/members", status_code=201)
async def add_member(
    channel_id: uuid.UUID,
    data: ChannelMemberAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a member to a channel."""
    service = ChannelService(db)

    channel = await service.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Check if current user is admin
    is_admin = False
    for member in channel.members:
        if member.user_id == current_user.id:
            is_admin = member.is_admin
            break
    else:
        raise HTTPException(status_code=403, detail="Not a member of this channel")

    if not is_admin and channel.channel_type != ChannelType.TEAM:
        raise HTTPException(status_code=403, detail="Only admins can add members")

    await service.add_member(channel_id, data.user_id, data.is_admin)
    return {"message": "Member added"}


@router.delete("/{channel_id}/members/{user_id}", status_code=204)
async def remove_member(
    channel_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a member from a channel."""
    service = ChannelService(db)

    channel = await service.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # User can remove themselves, or admin can remove others
    if user_id != current_user.id:
        is_admin = False
        for member in channel.members:
            if member.user_id == current_user.id:
                is_admin = member.is_admin
                break
        if not is_admin:
            raise HTTPException(status_code=403, detail="Only admins can remove other members")

    await service.remove_member(channel_id, user_id)


@router.post("/{channel_id}/leave", status_code=204)
async def leave_channel(
    channel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Leave a channel."""
    service = ChannelService(db)

    channel = await service.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.channel_type == ChannelType.DIRECT:
        raise HTTPException(status_code=400, detail="Cannot leave direct message channel")

    await service.remove_member(channel_id, current_user.id)


@router.post("/{channel_id}/mute", status_code=200)
async def mute_channel(
    channel_id: uuid.UUID,
    muted: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mute/unmute a channel."""
    service = ChannelService(db)

    if not await service.is_member(channel_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not a member of this channel")

    await service.mute_channel(channel_id, current_user.id, muted)
    return {"muted": muted}


# Helper function
async def _channel_to_response(channel) -> ChannelResponse:
    """Convert channel model to response schema."""
    members = []
    for member in channel.members:
        members.append(ChannelMemberResponse(
            id=member.id,
            user_id=member.user_id,
            user_name=member.user.full_name if member.user else "Unknown",
            user_email=member.user.email if member.user else "",
            is_admin=member.is_admin,
            is_muted=member.is_muted,
            unread_count=member.unread_count,
            joined_at=member.joined_at,
        ))

    return ChannelResponse(
        id=channel.id,
        name=channel.name,
        description=channel.description,
        channel_type=channel.channel_type,
        agency_id=channel.agency_id,
        incident_id=channel.incident_id,
        is_archived=channel.is_archived,
        is_private=channel.is_private,
        last_message_at=channel.last_message_at,
        message_count=channel.message_count,
        created_at=channel.created_at,
        members=members,
    )
