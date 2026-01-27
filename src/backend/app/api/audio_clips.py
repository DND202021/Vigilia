"""Audio Clip API endpoints for sound evidence management."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.services.audio_storage_service import AudioStorageService

router = APIRouter()


# ==================== Schemas ====================

class AudioClipResponse(BaseModel):
    """Audio clip metadata response."""
    id: str
    alert_id: str | None = None
    device_id: str
    file_path: str
    file_size_bytes: int | None = None
    duration_seconds: float | None = None
    format: str
    sample_rate: int
    event_type: str
    confidence: float | None = None
    peak_level_db: float | None = None
    background_level_db: float | None = None
    event_timestamp: str
    captured_at: str
    expires_at: str | None = None
    created_at: str


class PaginatedAudioClipResponse(BaseModel):
    """Paginated audio clip response."""
    items: list[AudioClipResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== Helpers ====================

def clip_to_response(clip) -> AudioClipResponse:
    """Convert audio clip model to response."""
    return AudioClipResponse(
        id=str(clip.id),
        alert_id=str(clip.alert_id) if clip.alert_id else None,
        device_id=str(clip.device_id),
        file_path=clip.file_path,
        file_size_bytes=clip.file_size_bytes,
        duration_seconds=clip.duration_seconds,
        format=clip.format,
        sample_rate=clip.sample_rate,
        event_type=clip.event_type,
        confidence=clip.confidence,
        peak_level_db=clip.peak_level_db,
        background_level_db=clip.background_level_db,
        event_timestamp=clip.event_timestamp.isoformat(),
        captured_at=clip.captured_at.isoformat(),
        expires_at=clip.expires_at.isoformat() if clip.expires_at else None,
        created_at=clip.created_at.isoformat() if clip.created_at else "",
    )


# ==================== Endpoints ====================

@router.get("", response_model=PaginatedAudioClipResponse)
async def list_audio_clips(
    device_id: str | None = None,
    alert_id: str | None = None,
    event_type: str | None = None,
    since: str | None = None,
    until: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedAudioClipResponse:
    """List audio clips with optional filters."""
    service = AudioStorageService(db)

    did = uuid.UUID(device_id) if device_id else None
    aid = uuid.UUID(alert_id) if alert_id else None
    since_dt = datetime.fromisoformat(since) if since else None
    until_dt = datetime.fromisoformat(until) if until else None

    clips, total = await service.list_clips(
        device_id=did,
        alert_id=aid,
        event_type=event_type,
        since=since_dt,
        until=until_dt,
        limit=page_size,
        offset=(page - 1) * page_size,
    )

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedAudioClipResponse(
        items=[clip_to_response(c) for c in clips],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{clip_id}", response_model=AudioClipResponse)
async def get_audio_clip(
    clip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AudioClipResponse:
    """Get audio clip metadata by ID."""
    try:
        clip_uuid = uuid.UUID(clip_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid clip ID")

    service = AudioStorageService(db)
    clip = await service.get_clip(clip_uuid)
    if not clip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio clip not found")

    return clip_to_response(clip)


@router.get("/{clip_id}/stream")
async def stream_audio_clip(
    clip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Stream audio clip for in-browser playback."""
    try:
        clip_uuid = uuid.UUID(clip_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid clip ID")

    service = AudioStorageService(db)
    result = await service.get_clip_data(clip_uuid)

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio clip not found or file missing")

    data, content_type = result

    import io
    return StreamingResponse(
        io.BytesIO(data),
        media_type=content_type,
        headers={
            "Content-Length": str(len(data)),
            "Accept-Ranges": "bytes",
        },
    )


@router.get("/{clip_id}/download")
async def download_audio_clip(
    clip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Download audio clip as a file."""
    try:
        clip_uuid = uuid.UUID(clip_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid clip ID")

    service = AudioStorageService(db)
    clip = await service.get_clip(clip_uuid)
    if not clip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio clip not found")

    result = await service.get_clip_data(clip_uuid)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file missing")

    data, content_type = result
    filename = f"{clip.event_type}_{clip.event_timestamp.strftime('%Y%m%d_%H%M%S')}.{clip.format}"

    import io
    return StreamingResponse(
        io.BytesIO(data),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(data)),
        },
    )
