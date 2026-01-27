"""Audio clip storage and retrieval service."""

import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audio_clip import AudioClip


class AudioStorageError(Exception):
    """Audio storage related errors."""
    pass


class AudioStorageService:
    """Service for storing, retrieving, and managing audio clips."""

    # Default retention period in days
    DEFAULT_RETENTION_DAYS = 90

    def __init__(
        self,
        db: AsyncSession,
        storage_path: str = "/data/audio_clips",
    ):
        self.db = db
        self.storage_path = Path(storage_path)

    async def store_clip(
        self,
        device_id: uuid.UUID,
        event_type: str,
        event_timestamp: datetime,
        audio_data: bytes,
        alert_id: uuid.UUID | None = None,
        confidence: float | None = None,
        peak_level_db: float | None = None,
        background_level_db: float | None = None,
        duration_seconds: float | None = None,
        format: str = "wav",
        sample_rate: int = 16000,
    ) -> AudioClip:
        """Store an audio clip and create a database record."""
        # Generate file path
        date_str = event_timestamp.strftime("%Y/%m/%d")
        filename = f"{event_type}_{device_id}_{event_timestamp.strftime('%H%M%S')}_{uuid.uuid4().hex[:8]}.{format}"
        relative_path = f"{date_str}/{filename}"
        full_path = self.storage_path / relative_path

        # Ensure directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write audio file
        with open(full_path, "wb") as f:
            f.write(audio_data)

        # Calculate retention expiry
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.DEFAULT_RETENTION_DAYS)

        # Create database record
        clip = AudioClip(
            id=uuid.uuid4(),
            alert_id=alert_id,
            device_id=device_id,
            file_path=relative_path,
            file_size_bytes=len(audio_data),
            duration_seconds=duration_seconds,
            format=format,
            sample_rate=sample_rate,
            event_type=event_type,
            confidence=confidence,
            peak_level_db=peak_level_db,
            background_level_db=background_level_db,
            event_timestamp=event_timestamp,
            captured_at=datetime.now(timezone.utc),
            expires_at=expires_at,
        )

        self.db.add(clip)
        await self.db.commit()
        await self.db.refresh(clip)

        return clip

    async def get_clip(self, clip_id: uuid.UUID) -> AudioClip | None:
        """Get audio clip metadata by ID."""
        result = await self.db.execute(
            select(AudioClip).where(AudioClip.id == clip_id)
        )
        return result.scalar_one_or_none()

    async def get_clip_by_alert(self, alert_id: uuid.UUID) -> AudioClip | None:
        """Get audio clip for a specific alert."""
        result = await self.db.execute(
            select(AudioClip).where(AudioClip.alert_id == alert_id)
        )
        return result.scalar_one_or_none()

    async def get_clip_data(self, clip_id: uuid.UUID) -> tuple[bytes, str] | None:
        """Get the actual audio file data for streaming/download."""
        clip = await self.get_clip(clip_id)
        if not clip:
            return None

        full_path = self.storage_path / clip.file_path
        if not full_path.exists():
            return None

        with open(full_path, "rb") as f:
            data = f.read()

        content_type = "audio/wav" if clip.format == "wav" else f"audio/{clip.format}"
        return data, content_type

    async def list_clips(
        self,
        device_id: uuid.UUID | None = None,
        alert_id: uuid.UUID | None = None,
        event_type: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AudioClip], int]:
        """List audio clips with optional filters."""
        query = select(AudioClip)

        conditions = []
        if device_id:
            conditions.append(AudioClip.device_id == device_id)
        if alert_id:
            conditions.append(AudioClip.alert_id == alert_id)
        if event_type:
            conditions.append(AudioClip.event_type == event_type)
        if since:
            conditions.append(AudioClip.event_timestamp >= since)
        if until:
            conditions.append(AudioClip.event_timestamp <= until)

        if conditions:
            query = query.where(and_(*conditions))

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.order_by(AudioClip.event_timestamp.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)

        return list(result.scalars().all()), total

    async def cleanup_expired(self) -> int:
        """Delete expired audio clips (file and database record)."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(AudioClip).where(
                and_(
                    AudioClip.expires_at.isnot(None),
                    AudioClip.expires_at <= now,
                )
            )
        )
        expired_clips = list(result.scalars().all())

        deleted_count = 0
        for clip in expired_clips:
            # Delete file
            full_path = self.storage_path / clip.file_path
            if full_path.exists():
                full_path.unlink()

            # Delete record
            await self.db.delete(clip)
            deleted_count += 1

        if deleted_count > 0:
            await self.db.commit()

        return deleted_count
