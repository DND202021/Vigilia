"""Recording and Playback Service.

This service manages video/audio recording from streams
and provides playback functionality including:
- Continuous recording
- Event-triggered recording
- Recording search and playback
- Export to various formats
- Retention management
"""

import asyncio
import uuid
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class RecordingStatus(str, Enum):
    """Recording status."""

    SCHEDULED = "scheduled"
    RECORDING = "recording"
    COMPLETED = "completed"
    FAILED = "failed"
    PROCESSING = "processing"
    ARCHIVED = "archived"
    DELETED = "deleted"


class RecordingType(str, Enum):
    """Recording type."""

    CONTINUOUS = "continuous"
    EVENT = "event"
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class RecordingFormat(str, Enum):
    """Recording output format."""

    MP4 = "mp4"
    WEBM = "webm"
    MKV = "mkv"
    TS = "ts"
    HLS = "hls"


@dataclass
class RecordingConfig:
    """Recording configuration."""

    format: RecordingFormat = RecordingFormat.MP4
    quality: str = "medium"  # low, medium, high, original
    max_duration_minutes: int = 60
    segment_duration_seconds: int = 300  # 5 minutes
    audio_enabled: bool = True
    pre_event_seconds: int = 10  # Buffer before event
    post_event_seconds: int = 30  # Continue after event
    retention_days: int = 30


@dataclass
class Recording:
    """Recording metadata."""

    id: uuid.UUID
    session_id: uuid.UUID | None = None
    source_id: uuid.UUID | None = None
    incident_id: uuid.UUID | None = None
    recording_type: RecordingType = RecordingType.MANUAL
    status: RecordingStatus = RecordingStatus.SCHEDULED
    config: RecordingConfig = field(default_factory=RecordingConfig)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: float = 0
    file_path: str | None = None
    file_size_bytes: int = 0
    thumbnail_path: str | None = None
    title: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: uuid.UUID | None = None

    @property
    def is_active(self) -> bool:
        """Check if recording is active."""
        return self.status == RecordingStatus.RECORDING

    @property
    def playback_url(self) -> str | None:
        """Get playback URL."""
        if self.status not in (RecordingStatus.COMPLETED, RecordingStatus.ARCHIVED):
            return None
        return f"/api/v1/recordings/{self.id}/play"


@dataclass
class RecordingSegment:
    """Recording segment for long recordings."""

    id: uuid.UUID
    recording_id: uuid.UUID
    segment_number: int
    file_path: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    file_size_bytes: int


@dataclass
class PlaybackSession:
    """Playback session for a recording."""

    id: uuid.UUID
    recording_id: uuid.UUID
    user_id: uuid.UUID
    started_at: datetime = field(default_factory=datetime.utcnow)
    current_position_seconds: float = 0
    playback_speed: float = 1.0
    is_paused: bool = False


class RecordingService:
    """Service for managing recordings."""

    def __init__(
        self,
        db: AsyncSession,
        storage_path: str = "/var/lib/vigilia/recordings",
    ):
        """Initialize recording service."""
        self.db = db
        self.storage_path = Path(storage_path)
        self._recordings: dict[uuid.UUID, Recording] = {}
        self._segments: dict[uuid.UUID, list[RecordingSegment]] = {}
        self._playback_sessions: dict[uuid.UUID, PlaybackSession] = {}
        self._active_recorders: dict[uuid.UUID, dict] = {}

    async def start_recording(
        self,
        source_id: uuid.UUID,
        session_id: uuid.UUID | None = None,
        recording_type: RecordingType = RecordingType.MANUAL,
        config: RecordingConfig | None = None,
        incident_id: uuid.UUID | None = None,
        title: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> Recording:
        """Start a new recording.

        Args:
            source_id: Source to record from
            session_id: Associated stream session
            recording_type: Type of recording
            config: Recording configuration
            incident_id: Associated incident
            title: Recording title
            user_id: User who started recording

        Returns:
            Recording instance
        """
        recording = Recording(
            id=uuid.uuid4(),
            session_id=session_id,
            source_id=source_id,
            incident_id=incident_id,
            recording_type=recording_type,
            status=RecordingStatus.RECORDING,
            config=config or RecordingConfig(),
            started_at=datetime.utcnow(),
            title=title or f"Recording {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            created_by=user_id,
        )

        # Create storage directory
        recording_dir = self.storage_path / str(recording.id)
        recording_dir.mkdir(parents=True, exist_ok=True)

        # Set file path
        ext = recording.config.format.value
        recording.file_path = str(recording_dir / f"recording.{ext}")

        self._recordings[recording.id] = recording
        self._segments[recording.id] = []

        # Start actual recording process (placeholder)
        self._active_recorders[recording.id] = {
            "started_at": datetime.utcnow(),
            "bytes_written": 0,
        }

        return recording

    async def stop_recording(self, recording_id: uuid.UUID) -> Recording | None:
        """Stop a recording.

        Args:
            recording_id: Recording to stop

        Returns:
            Updated recording or None
        """
        recording = self._recordings.get(recording_id)
        if not recording or not recording.is_active:
            return None

        recording.status = RecordingStatus.PROCESSING
        recording.ended_at = datetime.utcnow()

        if recording.started_at:
            recording.duration_seconds = (
                recording.ended_at - recording.started_at
            ).total_seconds()

        # Clean up recorder
        if recording_id in self._active_recorders:
            recording.file_size_bytes = self._active_recorders[recording_id].get("bytes_written", 0)
            del self._active_recorders[recording_id]

        # Generate thumbnail (placeholder)
        recording.thumbnail_path = await self._generate_thumbnail(recording)

        recording.status = RecordingStatus.COMPLETED

        return recording

    async def get_recording(self, recording_id: uuid.UUID) -> Recording | None:
        """Get recording by ID."""
        return self._recordings.get(recording_id)

    async def list_recordings(
        self,
        source_id: uuid.UUID | None = None,
        incident_id: uuid.UUID | None = None,
        recording_type: RecordingType | None = None,
        status: RecordingStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Recording]:
        """List recordings with filters.

        Args:
            source_id: Filter by source
            incident_id: Filter by incident
            recording_type: Filter by type
            status: Filter by status
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of recordings
        """
        recordings = list(self._recordings.values())

        # Apply filters
        if source_id:
            recordings = [r for r in recordings if r.source_id == source_id]
        if incident_id:
            recordings = [r for r in recordings if r.incident_id == incident_id]
        if recording_type:
            recordings = [r for r in recordings if r.recording_type == recording_type]
        if status:
            recordings = [r for r in recordings if r.status == status]
        if start_date:
            recordings = [r for r in recordings if r.started_at and r.started_at >= start_date]
        if end_date:
            recordings = [r for r in recordings if r.started_at and r.started_at <= end_date]

        # Sort by start time descending
        recordings.sort(key=lambda r: r.started_at or datetime.min, reverse=True)

        # Paginate
        return recordings[offset:offset + limit]

    async def delete_recording(self, recording_id: uuid.UUID) -> bool:
        """Delete a recording.

        Args:
            recording_id: Recording to delete

        Returns:
            True if deleted
        """
        recording = self._recordings.get(recording_id)
        if not recording:
            return False

        # Stop if active
        if recording.is_active:
            await self.stop_recording(recording_id)

        # Delete files
        if recording.file_path and os.path.exists(recording.file_path):
            try:
                os.remove(recording.file_path)
            except Exception:
                pass

        if recording.thumbnail_path and os.path.exists(recording.thumbnail_path):
            try:
                os.remove(recording.thumbnail_path)
            except Exception:
                pass

        # Delete segments
        for segment in self._segments.get(recording_id, []):
            if os.path.exists(segment.file_path):
                try:
                    os.remove(segment.file_path)
                except Exception:
                    pass

        if recording_id in self._segments:
            del self._segments[recording_id]

        recording.status = RecordingStatus.DELETED
        del self._recordings[recording_id]

        return True

    async def start_playback(
        self,
        recording_id: uuid.UUID,
        user_id: uuid.UUID,
        start_position: float = 0,
    ) -> PlaybackSession | None:
        """Start playback of a recording.

        Args:
            recording_id: Recording to play
            user_id: User starting playback
            start_position: Start position in seconds

        Returns:
            Playback session
        """
        recording = self._recordings.get(recording_id)
        if not recording or recording.status not in (
            RecordingStatus.COMPLETED,
            RecordingStatus.ARCHIVED,
        ):
            return None

        session = PlaybackSession(
            id=uuid.uuid4(),
            recording_id=recording_id,
            user_id=user_id,
            current_position_seconds=start_position,
        )

        self._playback_sessions[session.id] = session
        return session

    async def update_playback_position(
        self,
        session_id: uuid.UUID,
        position: float,
    ) -> bool:
        """Update playback position.

        Args:
            session_id: Playback session
            position: New position in seconds

        Returns:
            True if updated
        """
        session = self._playback_sessions.get(session_id)
        if not session:
            return False

        session.current_position_seconds = position
        return True

    async def stop_playback(self, session_id: uuid.UUID) -> bool:
        """Stop a playback session."""
        if session_id in self._playback_sessions:
            del self._playback_sessions[session_id]
            return True
        return False

    async def export_recording(
        self,
        recording_id: uuid.UUID,
        output_format: RecordingFormat,
        start_time: float | None = None,
        end_time: float | None = None,
    ) -> str | None:
        """Export recording to a different format or trim.

        Args:
            recording_id: Recording to export
            output_format: Target format
            start_time: Start trim point (seconds)
            end_time: End trim point (seconds)

        Returns:
            Path to exported file or None
        """
        recording = self._recordings.get(recording_id)
        if not recording or not recording.file_path:
            return None

        export_dir = self.storage_path / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        export_filename = f"{recording_id}_export_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{output_format.value}"
        export_path = export_dir / export_filename

        # Build FFmpeg command for export (placeholder)
        # Real implementation would execute this
        ffmpeg_cmd = self._build_export_command(
            input_path=recording.file_path,
            output_path=str(export_path),
            output_format=output_format,
            start_time=start_time,
            end_time=end_time,
        )

        # Placeholder - would actually run ffmpeg
        return str(export_path)

    async def search_recordings(
        self,
        query: str,
        tags: list[str] | None = None,
    ) -> list[Recording]:
        """Search recordings by text and tags.

        Args:
            query: Search query
            tags: Filter by tags

        Returns:
            Matching recordings
        """
        results = []
        query_lower = query.lower()

        for recording in self._recordings.values():
            # Search in title and description
            if recording.title and query_lower in recording.title.lower():
                results.append(recording)
                continue

            if recording.description and query_lower in recording.description.lower():
                results.append(recording)
                continue

            # Search in tags
            if any(query_lower in tag.lower() for tag in recording.tags):
                results.append(recording)
                continue

        # Filter by tags if specified
        if tags:
            results = [
                r for r in results
                if any(tag in r.tags for tag in tags)
            ]

        return results

    async def apply_retention_policy(self) -> int:
        """Apply retention policy to old recordings.

        Returns:
            Number of recordings deleted
        """
        deleted_count = 0
        now = datetime.utcnow()

        for recording in list(self._recordings.values()):
            if recording.status not in (RecordingStatus.COMPLETED, RecordingStatus.ARCHIVED):
                continue

            retention_days = recording.config.retention_days
            if recording.created_at and (now - recording.created_at).days > retention_days:
                if await self.delete_recording(recording.id):
                    deleted_count += 1

        return deleted_count

    async def _generate_thumbnail(self, recording: Recording) -> str | None:
        """Generate thumbnail for recording.

        Real implementation would extract a frame using FFmpeg.
        """
        if not recording.file_path:
            return None

        thumbnail_path = recording.file_path.rsplit(".", 1)[0] + "_thumb.jpg"
        # Placeholder - would actually generate thumbnail
        return thumbnail_path

    def _build_export_command(
        self,
        input_path: str,
        output_path: str,
        output_format: RecordingFormat,
        start_time: float | None = None,
        end_time: float | None = None,
    ) -> str:
        """Build FFmpeg export command."""
        cmd_parts = ["ffmpeg", f"-i {input_path}"]

        if start_time is not None:
            cmd_parts.append(f"-ss {start_time}")
        if end_time is not None:
            duration = end_time - (start_time or 0)
            cmd_parts.append(f"-t {duration}")

        # Format-specific settings
        if output_format == RecordingFormat.MP4:
            cmd_parts.extend(["-c:v libx264", "-c:a aac"])
        elif output_format == RecordingFormat.WEBM:
            cmd_parts.extend(["-c:v libvpx-vp9", "-c:a libopus"])

        cmd_parts.append(output_path)

        return " ".join(cmd_parts)


class EventRecordingTrigger:
    """Handles event-triggered recording."""

    def __init__(self, recording_service: RecordingService):
        """Initialize event trigger."""
        self.recording_service = recording_service
        self._active_triggers: dict[uuid.UUID, dict] = {}
        self._buffer_recordings: dict[uuid.UUID, Recording] = {}

    async def on_event(
        self,
        source_id: uuid.UUID,
        event_type: str,
        incident_id: uuid.UUID | None = None,
        config: RecordingConfig | None = None,
    ) -> Recording | None:
        """Handle an event that should trigger recording.

        Args:
            source_id: Source where event occurred
            event_type: Type of event
            incident_id: Associated incident
            config: Recording configuration

        Returns:
            Started recording or None
        """
        config = config or RecordingConfig()

        # Check if already recording this source
        existing = self._active_triggers.get(source_id)
        if existing:
            # Extend recording duration
            existing["extend_until"] = datetime.utcnow() + timedelta(
                seconds=config.post_event_seconds
            )
            return self._buffer_recordings.get(source_id)

        # Start new recording
        recording = await self.recording_service.start_recording(
            source_id=source_id,
            recording_type=RecordingType.EVENT,
            config=config,
            incident_id=incident_id,
            title=f"Event Recording: {event_type}",
        )

        self._active_triggers[source_id] = {
            "recording_id": recording.id,
            "started_at": datetime.utcnow(),
            "extend_until": datetime.utcnow() + timedelta(
                seconds=config.post_event_seconds
            ),
        }
        self._buffer_recordings[source_id] = recording

        # Schedule auto-stop
        asyncio.create_task(self._auto_stop_recording(source_id, config))

        return recording

    async def _auto_stop_recording(
        self,
        source_id: uuid.UUID,
        config: RecordingConfig,
    ) -> None:
        """Automatically stop recording after event ends."""
        while source_id in self._active_triggers:
            trigger = self._active_triggers[source_id]
            now = datetime.utcnow()

            # Check if should stop
            if now >= trigger["extend_until"]:
                recording_id = trigger["recording_id"]
                await self.recording_service.stop_recording(recording_id)

                del self._active_triggers[source_id]
                if source_id in self._buffer_recordings:
                    del self._buffer_recordings[source_id]
                break

            # Check max duration
            if (now - trigger["started_at"]).total_seconds() >= config.max_duration_minutes * 60:
                recording_id = trigger["recording_id"]
                await self.recording_service.stop_recording(recording_id)

                del self._active_triggers[source_id]
                if source_id in self._buffer_recordings:
                    del self._buffer_recordings[source_id]
                break

            await asyncio.sleep(1)
