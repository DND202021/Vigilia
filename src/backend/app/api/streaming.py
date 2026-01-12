"""Streaming and Recording API endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user, require_permission, Permission
from app.models.user import User
from app.services.streaming import (
    StreamingService,
    StreamSource,
    StreamSession,
    StreamType,
    StreamQuality,
    StreamConfig,
    WebRTCSignalingService,
    HLSSegmentManager,
)
from app.services.recording import (
    RecordingService,
    Recording,
    RecordingType,
    RecordingStatus,
    RecordingFormat,
    RecordingConfig,
)

router = APIRouter()


# Service instances
_streaming_service: StreamingService | None = None
_recording_service: RecordingService | None = None
_webrtc_signaling: WebRTCSignalingService | None = None
_hls_manager: HLSSegmentManager | None = None


def get_streaming_service(db: AsyncSession = Depends(get_db)) -> StreamingService:
    """Get streaming service instance."""
    global _streaming_service
    if _streaming_service is None:
        _streaming_service = StreamingService(db)
    return _streaming_service


def get_recording_service(db: AsyncSession = Depends(get_db)) -> RecordingService:
    """Get recording service instance."""
    global _recording_service
    if _recording_service is None:
        _recording_service = RecordingService(db)
    return _recording_service


def get_webrtc_signaling() -> WebRTCSignalingService:
    """Get WebRTC signaling service instance."""
    global _webrtc_signaling
    if _webrtc_signaling is None:
        _webrtc_signaling = WebRTCSignalingService()
    return _webrtc_signaling


def get_hls_manager() -> HLSSegmentManager:
    """Get HLS segment manager instance."""
    global _hls_manager
    if _hls_manager is None:
        _hls_manager = HLSSegmentManager()
    return _hls_manager


# Request/Response Models
class StreamSourceCreate(BaseModel):
    """Create stream source request."""

    name: str = Field(..., min_length=1, max_length=255)
    source_type: str = Field(..., description="Source type: camera, device, screen, audio")
    source_url: str | None = None
    device_id: str | None = None
    stream_type: str = Field("rtsp", description="Stream type: rtsp, mjpeg, hls, webrtc")
    quality: str = Field("medium", description="Quality: low, medium, high, ultra")
    audio_enabled: bool = True


class StreamSourceResponse(BaseModel):
    """Stream source response."""

    id: str
    name: str
    source_type: str
    source_url: str | None
    device_id: str | None
    stream_type: str
    quality: str


class StreamSessionResponse(BaseModel):
    """Stream session response."""

    id: str
    source_id: str
    source_name: str
    status: str
    started_at: datetime
    viewer_count: int
    output_urls: dict[str, str]
    recording_enabled: bool
    recording_id: str | None


class StartStreamRequest(BaseModel):
    """Start stream request."""

    source_id: str
    stream_type: str | None = None
    quality: str | None = None
    record: bool = False


class WebRTCSignalRequest(BaseModel):
    """WebRTC signaling request."""

    peer_id: str
    type: str  # offer, answer, ice
    sdp: str | None = None
    candidate: dict | None = None


class RecordingCreateRequest(BaseModel):
    """Create recording request."""

    source_id: str
    session_id: str | None = None
    incident_id: str | None = None
    recording_type: str = "manual"
    title: str | None = None
    format: str = "mp4"
    quality: str = "medium"
    max_duration_minutes: int = Field(60, ge=1, le=480)
    audio_enabled: bool = True


class RecordingResponse(BaseModel):
    """Recording response."""

    id: str
    source_id: str | None
    session_id: str | None
    incident_id: str | None
    recording_type: str
    status: str
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: float
    file_size_bytes: int
    title: str | None
    description: str | None
    tags: list[str]
    playback_url: str | None
    thumbnail_url: str | None
    created_at: datetime


class RecordingUpdateRequest(BaseModel):
    """Update recording request."""

    title: str | None = None
    description: str | None = None
    tags: list[str] | None = None


class PlaybackSessionResponse(BaseModel):
    """Playback session response."""

    id: str
    recording_id: str
    started_at: datetime
    current_position_seconds: float
    playback_speed: float
    is_paused: bool


# Stream Source Endpoints
@router.post("/sources", response_model=StreamSourceResponse)
async def create_stream_source(
    request: StreamSourceCreate,
    service: StreamingService = Depends(get_streaming_service),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> StreamSourceResponse:
    """Create a new stream source."""
    try:
        stream_type = StreamType(request.stream_type.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid stream type. Valid types: {[t.value for t in StreamType]}",
        )

    try:
        quality = StreamQuality(request.quality.lower())
    except ValueError:
        quality = StreamQuality.MEDIUM

    device_uuid = None
    if request.device_id:
        try:
            device_uuid = uuid.UUID(request.device_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid device ID format",
            )

    source = StreamSource(
        id=uuid.uuid4(),
        name=request.name,
        source_type=request.source_type,
        source_url=request.source_url,
        device_id=device_uuid,
        stream_type=stream_type,
        config=StreamConfig(
            quality=quality,
            audio_enabled=request.audio_enabled,
        ),
    )

    service.register_source(source)

    return StreamSourceResponse(
        id=str(source.id),
        name=source.name,
        source_type=source.source_type,
        source_url=source.source_url,
        device_id=str(source.device_id) if source.device_id else None,
        stream_type=source.stream_type.value,
        quality=source.config.quality.value,
    )


@router.get("/sources", response_model=list[StreamSourceResponse])
async def list_stream_sources(
    service: StreamingService = Depends(get_streaming_service),
    current_user: User = Depends(get_current_active_user),
) -> list[StreamSourceResponse]:
    """List all stream sources."""
    sources = service.list_sources()

    return [
        StreamSourceResponse(
            id=str(s.id),
            name=s.name,
            source_type=s.source_type,
            source_url=s.source_url,
            device_id=str(s.device_id) if s.device_id else None,
            stream_type=s.stream_type.value,
            quality=s.config.quality.value,
        )
        for s in sources
    ]


@router.delete("/sources/{source_id}")
async def delete_stream_source(
    source_id: str,
    service: StreamingService = Depends(get_streaming_service),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> dict:
    """Delete a stream source."""
    try:
        source_uuid = uuid.UUID(source_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid source ID format",
        )

    source = service.get_source(source_uuid)
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )

    service.unregister_source(source_uuid)

    return {"message": f"Source '{source.name}' deleted"}


# Stream Session Endpoints
@router.post("/sessions", response_model=StreamSessionResponse)
async def start_stream(
    request: StartStreamRequest,
    service: StreamingService = Depends(get_streaming_service),
    current_user: User = Depends(get_current_active_user),
) -> StreamSessionResponse:
    """Start a new stream session."""
    try:
        source_uuid = uuid.UUID(request.source_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid source ID format",
        )

    stream_type = None
    if request.stream_type:
        try:
            stream_type = StreamType(request.stream_type.lower())
        except ValueError:
            pass

    config = None
    if request.quality:
        try:
            quality = StreamQuality(request.quality.lower())
            config = StreamConfig(quality=quality)
        except ValueError:
            pass

    try:
        session = await service.start_stream(
            source_id=source_uuid,
            stream_type=stream_type,
            config=config,
            record=request.record,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return StreamSessionResponse(
        id=str(session.id),
        source_id=str(session.source.id),
        source_name=session.source.name,
        status=session.status.value,
        started_at=session.started_at,
        viewer_count=session.viewer_count,
        output_urls=session.output_urls,
        recording_enabled=session.recording_enabled,
        recording_id=str(session.recording_id) if session.recording_id else None,
    )


@router.get("/sessions", response_model=list[StreamSessionResponse])
async def list_stream_sessions(
    active_only: bool = True,
    service: StreamingService = Depends(get_streaming_service),
    current_user: User = Depends(get_current_active_user),
) -> list[StreamSessionResponse]:
    """List stream sessions."""
    sessions = service.list_sessions(active_only=active_only)

    return [
        StreamSessionResponse(
            id=str(s.id),
            source_id=str(s.source.id),
            source_name=s.source.name,
            status=s.status.value,
            started_at=s.started_at,
            viewer_count=s.viewer_count,
            output_urls=s.output_urls,
            recording_enabled=s.recording_enabled,
            recording_id=str(s.recording_id) if s.recording_id else None,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=StreamSessionResponse)
async def get_stream_session(
    session_id: str,
    service: StreamingService = Depends(get_streaming_service),
    current_user: User = Depends(get_current_active_user),
) -> StreamSessionResponse:
    """Get a stream session by ID."""
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    session = service.get_session(session_uuid)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return StreamSessionResponse(
        id=str(session.id),
        source_id=str(session.source.id),
        source_name=session.source.name,
        status=session.status.value,
        started_at=session.started_at,
        viewer_count=session.viewer_count,
        output_urls=session.output_urls,
        recording_enabled=session.recording_enabled,
        recording_id=str(session.recording_id) if session.recording_id else None,
    )


@router.delete("/sessions/{session_id}")
async def stop_stream(
    session_id: str,
    service: StreamingService = Depends(get_streaming_service),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Stop a stream session."""
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    success = await service.stop_stream(session_uuid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return {"message": "Stream stopped"}


@router.post("/sessions/{session_id}/join")
async def join_stream(
    session_id: str,
    service: StreamingService = Depends(get_streaming_service),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Join a stream as viewer."""
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    success = await service.add_viewer(session_uuid, str(current_user.id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    session = service.get_session(session_uuid)

    return {
        "message": "Joined stream",
        "viewer_count": session.viewer_count if session else 0,
        "output_urls": session.output_urls if session else {},
    }


@router.post("/sessions/{session_id}/leave")
async def leave_stream(
    session_id: str,
    service: StreamingService = Depends(get_streaming_service),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Leave a stream as viewer."""
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    await service.remove_viewer(session_uuid, str(current_user.id))

    return {"message": "Left stream"}


# WebRTC Signaling Endpoints
@router.post("/sessions/{session_id}/webrtc/signal")
async def webrtc_signal(
    session_id: str,
    request: WebRTCSignalRequest,
    service: StreamingService = Depends(get_streaming_service),
    signaling: WebRTCSignalingService = Depends(get_webrtc_signaling),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Handle WebRTC signaling."""
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    session = service.get_session(session_uuid)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if request.type == "offer":
        # Client wants to receive stream, create offer
        offer = await signaling.create_offer(session_uuid, request.peer_id)
        return {"type": "offer", "sdp": offer["sdp"]}

    elif request.type == "answer":
        # Client responding with answer
        if not request.sdp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SDP required for answer",
            )
        await signaling.handle_answer(
            session_uuid,
            request.peer_id,
            {"type": "answer", "sdp": request.sdp},
        )
        return {"message": "Answer received"}

    elif request.type == "ice":
        # ICE candidate
        if not request.candidate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Candidate required for ICE",
            )
        await signaling.add_ice_candidate(
            session_uuid,
            request.peer_id,
            request.candidate,
        )
        return {"message": "ICE candidate added"}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unknown signal type: {request.type}",
    )


@router.get("/sessions/{session_id}/webrtc/ice/{peer_id}")
async def get_ice_candidates(
    session_id: str,
    peer_id: str,
    signaling: WebRTCSignalingService = Depends(get_webrtc_signaling),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Get pending ICE candidates."""
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    candidates = await signaling.get_ice_candidates(session_uuid, peer_id)

    return {"candidates": candidates}


# Recording Endpoints
@router.post("/recordings", response_model=RecordingResponse)
async def start_recording(
    request: RecordingCreateRequest,
    service: RecordingService = Depends(get_recording_service),
    current_user: User = Depends(get_current_active_user),
) -> RecordingResponse:
    """Start a new recording."""
    try:
        source_uuid = uuid.UUID(request.source_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid source ID format",
        )

    session_uuid = None
    if request.session_id:
        try:
            session_uuid = uuid.UUID(request.session_id)
        except ValueError:
            pass

    incident_uuid = None
    if request.incident_id:
        try:
            incident_uuid = uuid.UUID(request.incident_id)
        except ValueError:
            pass

    try:
        rec_type = RecordingType(request.recording_type.lower())
    except ValueError:
        rec_type = RecordingType.MANUAL

    try:
        rec_format = RecordingFormat(request.format.lower())
    except ValueError:
        rec_format = RecordingFormat.MP4

    config = RecordingConfig(
        format=rec_format,
        quality=request.quality,
        max_duration_minutes=request.max_duration_minutes,
        audio_enabled=request.audio_enabled,
    )

    recording = await service.start_recording(
        source_id=source_uuid,
        session_id=session_uuid,
        recording_type=rec_type,
        config=config,
        incident_id=incident_uuid,
        title=request.title,
        user_id=current_user.id,
    )

    return RecordingResponse(
        id=str(recording.id),
        source_id=str(recording.source_id) if recording.source_id else None,
        session_id=str(recording.session_id) if recording.session_id else None,
        incident_id=str(recording.incident_id) if recording.incident_id else None,
        recording_type=recording.recording_type.value,
        status=recording.status.value,
        started_at=recording.started_at,
        ended_at=recording.ended_at,
        duration_seconds=recording.duration_seconds,
        file_size_bytes=recording.file_size_bytes,
        title=recording.title,
        description=recording.description,
        tags=recording.tags,
        playback_url=recording.playback_url,
        thumbnail_url=f"/api/v1/streaming/recordings/{recording.id}/thumbnail" if recording.thumbnail_path else None,
        created_at=recording.created_at,
    )


@router.get("/recordings", response_model=list[RecordingResponse])
async def list_recordings(
    source_id: str | None = None,
    incident_id: str | None = None,
    recording_type: str | None = None,
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: RecordingService = Depends(get_recording_service),
    current_user: User = Depends(get_current_active_user),
) -> list[RecordingResponse]:
    """List recordings."""
    source_uuid = None
    if source_id:
        try:
            source_uuid = uuid.UUID(source_id)
        except ValueError:
            pass

    incident_uuid = None
    if incident_id:
        try:
            incident_uuid = uuid.UUID(incident_id)
        except ValueError:
            pass

    rec_type = None
    if recording_type:
        try:
            rec_type = RecordingType(recording_type.lower())
        except ValueError:
            pass

    rec_status = None
    if status:
        try:
            rec_status = RecordingStatus(status.lower())
        except ValueError:
            pass

    recordings = await service.list_recordings(
        source_id=source_uuid,
        incident_id=incident_uuid,
        recording_type=rec_type,
        status=rec_status,
        limit=limit,
        offset=offset,
    )

    return [
        RecordingResponse(
            id=str(r.id),
            source_id=str(r.source_id) if r.source_id else None,
            session_id=str(r.session_id) if r.session_id else None,
            incident_id=str(r.incident_id) if r.incident_id else None,
            recording_type=r.recording_type.value,
            status=r.status.value,
            started_at=r.started_at,
            ended_at=r.ended_at,
            duration_seconds=r.duration_seconds,
            file_size_bytes=r.file_size_bytes,
            title=r.title,
            description=r.description,
            tags=r.tags,
            playback_url=r.playback_url,
            thumbnail_url=f"/api/v1/streaming/recordings/{r.id}/thumbnail" if r.thumbnail_path else None,
            created_at=r.created_at,
        )
        for r in recordings
    ]


@router.get("/recordings/{recording_id}", response_model=RecordingResponse)
async def get_recording(
    recording_id: str,
    service: RecordingService = Depends(get_recording_service),
    current_user: User = Depends(get_current_active_user),
) -> RecordingResponse:
    """Get recording by ID."""
    try:
        rec_uuid = uuid.UUID(recording_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid recording ID format",
        )

    recording = await service.get_recording(rec_uuid)
    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not found",
        )

    return RecordingResponse(
        id=str(recording.id),
        source_id=str(recording.source_id) if recording.source_id else None,
        session_id=str(recording.session_id) if recording.session_id else None,
        incident_id=str(recording.incident_id) if recording.incident_id else None,
        recording_type=recording.recording_type.value,
        status=recording.status.value,
        started_at=recording.started_at,
        ended_at=recording.ended_at,
        duration_seconds=recording.duration_seconds,
        file_size_bytes=recording.file_size_bytes,
        title=recording.title,
        description=recording.description,
        tags=recording.tags,
        playback_url=recording.playback_url,
        thumbnail_url=f"/api/v1/streaming/recordings/{recording.id}/thumbnail" if recording.thumbnail_path else None,
        created_at=recording.created_at,
    )


@router.post("/recordings/{recording_id}/stop", response_model=RecordingResponse)
async def stop_recording(
    recording_id: str,
    service: RecordingService = Depends(get_recording_service),
    current_user: User = Depends(get_current_active_user),
) -> RecordingResponse:
    """Stop a recording."""
    try:
        rec_uuid = uuid.UUID(recording_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid recording ID format",
        )

    recording = await service.stop_recording(rec_uuid)
    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not found or not active",
        )

    return RecordingResponse(
        id=str(recording.id),
        source_id=str(recording.source_id) if recording.source_id else None,
        session_id=str(recording.session_id) if recording.session_id else None,
        incident_id=str(recording.incident_id) if recording.incident_id else None,
        recording_type=recording.recording_type.value,
        status=recording.status.value,
        started_at=recording.started_at,
        ended_at=recording.ended_at,
        duration_seconds=recording.duration_seconds,
        file_size_bytes=recording.file_size_bytes,
        title=recording.title,
        description=recording.description,
        tags=recording.tags,
        playback_url=recording.playback_url,
        thumbnail_url=f"/api/v1/streaming/recordings/{recording.id}/thumbnail" if recording.thumbnail_path else None,
        created_at=recording.created_at,
    )


@router.delete("/recordings/{recording_id}")
async def delete_recording(
    recording_id: str,
    service: RecordingService = Depends(get_recording_service),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> dict:
    """Delete a recording."""
    try:
        rec_uuid = uuid.UUID(recording_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid recording ID format",
        )

    success = await service.delete_recording(rec_uuid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not found",
        )

    return {"message": "Recording deleted"}


@router.patch("/recordings/{recording_id}", response_model=RecordingResponse)
async def update_recording(
    recording_id: str,
    update: RecordingUpdateRequest,
    service: RecordingService = Depends(get_recording_service),
    current_user: User = Depends(get_current_active_user),
) -> RecordingResponse:
    """Update recording metadata."""
    try:
        rec_uuid = uuid.UUID(recording_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid recording ID format",
        )

    recording = await service.get_recording(rec_uuid)
    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not found",
        )

    if update.title is not None:
        recording.title = update.title
    if update.description is not None:
        recording.description = update.description
    if update.tags is not None:
        recording.tags = update.tags

    return RecordingResponse(
        id=str(recording.id),
        source_id=str(recording.source_id) if recording.source_id else None,
        session_id=str(recording.session_id) if recording.session_id else None,
        incident_id=str(recording.incident_id) if recording.incident_id else None,
        recording_type=recording.recording_type.value,
        status=recording.status.value,
        started_at=recording.started_at,
        ended_at=recording.ended_at,
        duration_seconds=recording.duration_seconds,
        file_size_bytes=recording.file_size_bytes,
        title=recording.title,
        description=recording.description,
        tags=recording.tags,
        playback_url=recording.playback_url,
        thumbnail_url=f"/api/v1/streaming/recordings/{recording.id}/thumbnail" if recording.thumbnail_path else None,
        created_at=recording.created_at,
    )


@router.post("/recordings/{recording_id}/play", response_model=PlaybackSessionResponse)
async def start_playback(
    recording_id: str,
    start_position: float = Query(0, ge=0),
    service: RecordingService = Depends(get_recording_service),
    current_user: User = Depends(get_current_active_user),
) -> PlaybackSessionResponse:
    """Start playback of a recording."""
    try:
        rec_uuid = uuid.UUID(recording_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid recording ID format",
        )

    session = await service.start_playback(
        recording_id=rec_uuid,
        user_id=current_user.id,
        start_position=start_position,
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not found or not available for playback",
        )

    return PlaybackSessionResponse(
        id=str(session.id),
        recording_id=str(session.recording_id),
        started_at=session.started_at,
        current_position_seconds=session.current_position_seconds,
        playback_speed=session.playback_speed,
        is_paused=session.is_paused,
    )
