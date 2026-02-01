"""Messages API endpoints for Communication Hub."""

import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.message import MessageType, MessagePriority
from app.services.channel_service import ChannelService
from app.services.message_service import MessageService

router = APIRouter(prefix="/messages", tags=["messages"])


# Request/Response schemas
class MessageCreate(BaseModel):
    """Schema for sending a message."""

    content: str = Field(..., min_length=1, max_length=10000)
    message_type: MessageType = MessageType.TEXT
    priority: MessagePriority = MessagePriority.NORMAL
    reply_to_id: Optional[uuid.UUID] = None
    # Location fields
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    location_address: Optional[str] = None


class MessageEdit(BaseModel):
    """Schema for editing a message."""

    content: str = Field(..., min_length=1, max_length=10000)


class MessageReactionAdd(BaseModel):
    """Schema for adding a reaction."""

    emoji: str = Field(..., min_length=1, max_length=10)


class SenderResponse(BaseModel):
    """Response schema for message sender."""

    id: uuid.UUID
    full_name: str
    email: str

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Response schema for a message."""

    id: uuid.UUID
    channel_id: uuid.UUID
    sender_id: Optional[uuid.UUID]
    sender: Optional[SenderResponse]
    message_type: MessageType
    content: str
    priority: MessagePriority
    attachment_url: Optional[str]
    attachment_name: Optional[str]
    attachment_size: Optional[int]
    attachment_mime_type: Optional[str]
    location_lat: Optional[float]
    location_lng: Optional[float]
    location_address: Optional[str]
    reply_to_id: Optional[uuid.UUID]
    is_edited: bool
    edited_at: Optional[datetime]
    read_by: Optional[list[str]]
    created_at: datetime

    class Config:
        from_attributes = True


class UnreadCountResponse(BaseModel):
    """Response schema for unread counts."""

    total: int
    by_channel: dict[str, int]


# Endpoints
@router.get("/channel/{channel_id}", response_model=list[MessageResponse])
async def get_channel_messages(
    channel_id: uuid.UUID,
    limit: int = Query(50, le=100),
    before: Optional[datetime] = Query(None),
    after: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get messages for a channel."""
    channel_service = ChannelService(db)

    # Check membership
    if not await channel_service.is_member(channel_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not a member of this channel")

    message_service = MessageService(db)
    messages = await message_service.get_channel_messages(
        channel_id=channel_id,
        limit=limit,
        before=before,
        after=after,
    )

    return [_message_to_response(msg) for msg in messages]


@router.post("/channel/{channel_id}", response_model=MessageResponse, status_code=201)
async def send_message(
    channel_id: uuid.UUID,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message to a channel."""
    channel_service = ChannelService(db)

    # Check membership
    if not await channel_service.is_member(channel_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not a member of this channel")

    message_service = MessageService(db)
    message = await message_service.send_message(
        channel_id=channel_id,
        sender_id=current_user.id,
        content=data.content,
        message_type=data.message_type,
        priority=data.priority,
        reply_to_id=data.reply_to_id,
        location_lat=data.location_lat,
        location_lng=data.location_lng,
        location_address=data.location_address,
    )

    # Emit WebSocket event
    from app.services.socketio import sio
    await sio.emit(
        "message:new",
        {
            "channel_id": str(channel_id),
            "message": _message_to_dict(message),
        },
        room=f"channel:{channel_id}",
    )

    return _message_to_response(message)


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific message."""
    message_service = MessageService(db)
    message = await message_service.get_message(message_id)

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Check channel membership
    channel_service = ChannelService(db)
    if not await channel_service.is_member(message.channel_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not a member of this channel")

    return _message_to_response(message)


@router.patch("/{message_id}", response_model=MessageResponse)
async def edit_message(
    message_id: uuid.UUID,
    data: MessageEdit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edit a message (only by sender)."""
    message_service = MessageService(db)
    message = await message_service.edit_message(
        message_id=message_id,
        user_id=current_user.id,
        new_content=data.content,
    )

    if not message:
        raise HTTPException(status_code=404, detail="Message not found or not authorized")

    # Emit WebSocket event
    from app.services.socketio import sio
    await sio.emit(
        "message:edited",
        {
            "channel_id": str(message.channel_id),
            "message_id": str(message_id),
            "content": message.content,
            "edited_at": message.edited_at.isoformat() if message.edited_at else None,
        },
        room=f"channel:{message.channel_id}",
    )

    return _message_to_response(message)


@router.delete("/{message_id}", status_code=204)
async def delete_message(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a message."""
    message_service = MessageService(db)
    message = await message_service.get_message(message_id)

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Check if user is sender or channel admin
    channel_service = ChannelService(db)
    channel = await channel_service.get_channel(message.channel_id)
    is_admin = False
    if channel:
        for member in channel.members:
            if member.user_id == current_user.id:
                is_admin = member.is_admin
                break

    success = await message_service.delete_message(
        message_id=message_id,
        user_id=current_user.id,
        is_admin=is_admin,
    )

    if not success:
        raise HTTPException(status_code=403, detail="Not authorized to delete this message")

    # Emit WebSocket event
    from app.services.socketio import sio
    await sio.emit(
        "message:deleted",
        {
            "channel_id": str(message.channel_id),
            "message_id": str(message_id),
        },
        room=f"channel:{message.channel_id}",
    )


@router.post("/channel/{channel_id}/read", status_code=200)
async def mark_as_read(
    channel_id: uuid.UUID,
    message_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark messages as read."""
    channel_service = ChannelService(db)

    if not await channel_service.is_member(channel_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not a member of this channel")

    message_service = MessageService(db)
    await message_service.mark_as_read(
        channel_id=channel_id,
        user_id=current_user.id,
        up_to_message_id=message_id,
    )

    return {"message": "Marked as read"}


@router.get("/unread/count", response_model=UnreadCountResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get unread message counts."""
    message_service = MessageService(db)
    counts = await message_service.get_unread_count(current_user.id)
    return counts


@router.get("/search", response_model=list[MessageResponse])
async def search_messages(
    query: str = Query(..., min_length=2),
    channel_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search messages across user's channels."""
    message_service = MessageService(db)
    messages = await message_service.search_messages(
        user_id=current_user.id,
        query=query,
        channel_id=channel_id,
        limit=limit,
    )

    return [_message_to_response(msg) for msg in messages]


@router.post("/{message_id}/reactions", status_code=201)
async def add_reaction(
    message_id: uuid.UUID,
    data: MessageReactionAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a reaction to a message."""
    message_service = MessageService(db)
    message = await message_service.get_message(message_id)

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Check channel membership
    channel_service = ChannelService(db)
    if not await channel_service.is_member(message.channel_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not a member of this channel")

    reaction = await message_service.add_reaction(
        message_id=message_id,
        user_id=current_user.id,
        emoji=data.emoji,
    )

    # Emit WebSocket event
    from app.services.socketio import sio
    await sio.emit(
        "message:reaction",
        {
            "channel_id": str(message.channel_id),
            "message_id": str(message_id),
            "user_id": str(current_user.id),
            "emoji": data.emoji,
            "action": "add",
        },
        room=f"channel:{message.channel_id}",
    )

    return {"message": "Reaction added"}


@router.delete("/{message_id}/reactions/{emoji}", status_code=204)
async def remove_reaction(
    message_id: uuid.UUID,
    emoji: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a reaction from a message."""
    message_service = MessageService(db)
    message = await message_service.get_message(message_id)

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    success = await message_service.remove_reaction(
        message_id=message_id,
        user_id=current_user.id,
        emoji=emoji,
    )

    if success:
        # Emit WebSocket event
        from app.services.socketio import sio
        await sio.emit(
            "message:reaction",
            {
                "channel_id": str(message.channel_id),
                "message_id": str(message_id),
                "user_id": str(current_user.id),
                "emoji": emoji,
                "action": "remove",
            },
            room=f"channel:{message.channel_id}",
        )


# Helper functions
def _message_to_response(message) -> MessageResponse:
    """Convert message model to response schema."""
    sender = None
    if message.sender:
        sender = SenderResponse(
            id=message.sender.id,
            full_name=message.sender.full_name,
            email=message.sender.email,
        )

    return MessageResponse(
        id=message.id,
        channel_id=message.channel_id,
        sender_id=message.sender_id,
        sender=sender,
        message_type=message.message_type,
        content=message.content,
        priority=message.priority,
        attachment_url=message.attachment_url,
        attachment_name=message.attachment_name,
        attachment_size=message.attachment_size,
        attachment_mime_type=message.attachment_mime_type,
        location_lat=message.location_lat,
        location_lng=message.location_lng,
        location_address=message.location_address,
        reply_to_id=message.reply_to_id,
        is_edited=message.is_edited,
        edited_at=message.edited_at,
        read_by=message.read_by,
        created_at=message.created_at,
    )


def _message_to_dict(message) -> dict:
    """Convert message to dict for WebSocket events."""
    return {
        "id": str(message.id),
        "channel_id": str(message.channel_id),
        "sender_id": str(message.sender_id) if message.sender_id else None,
        "sender_name": message.sender.full_name if message.sender else None,
        "message_type": message.message_type.value,
        "content": message.content,
        "priority": message.priority.value,
        "created_at": message.created_at.isoformat(),
    }
