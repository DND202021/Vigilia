"""Live Audio/Video Streaming Service.

This service manages live streaming from various sources including:
- Axis cameras (RTSP, MJPEG)
- IP cameras
- Audio devices
- Screen sharing
- WebRTC for browser-based streaming
"""

import asyncio
import uuid
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Callable

from sqlalchemy.ext.asyncio import AsyncSession


class StreamType(str, Enum):
    """Stream types."""

    RTSP = "rtsp"
    MJPEG = "mjpeg"
    HLS = "hls"
    WEBRTC = "webrtc"
    DASH = "dash"
    AUDIO_ONLY = "audio"


class StreamQuality(str, Enum):
    """Stream quality presets."""

    LOW = "low"  # 480p, 15fps
    MEDIUM = "medium"  # 720p, 25fps
    HIGH = "high"  # 1080p, 30fps
    ULTRA = "ultra"  # 4K, 30fps
    AUDIO_LOW = "audio_low"  # 64kbps
    AUDIO_HIGH = "audio_high"  # 128kbps


class StreamStatus(str, Enum):
    """Stream status."""

    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    BUFFERING = "buffering"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class StreamConfig:
    """Stream configuration."""

    quality: StreamQuality = StreamQuality.MEDIUM
    codec: str = "h264"  # h264, h265, vp8, vp9
    audio_enabled: bool = True
    audio_codec: str = "aac"  # aac, opus
    bitrate_kbps: int | None = None
    framerate: int | None = None
    keyframe_interval: int = 2  # seconds
    latency_mode: str = "low"  # low, normal, high (for buffering)

    def get_resolution(self) -> tuple[int, int]:
        """Get resolution for quality preset."""
        resolutions = {
            StreamQuality.LOW: (854, 480),
            StreamQuality.MEDIUM: (1280, 720),
            StreamQuality.HIGH: (1920, 1080),
            StreamQuality.ULTRA: (3840, 2160),
        }
        return resolutions.get(self.quality, (1280, 720))

    def get_bitrate(self) -> int:
        """Get bitrate for quality preset."""
        if self.bitrate_kbps:
            return self.bitrate_kbps

        bitrates = {
            StreamQuality.LOW: 1000,
            StreamQuality.MEDIUM: 2500,
            StreamQuality.HIGH: 5000,
            StreamQuality.ULTRA: 15000,
            StreamQuality.AUDIO_LOW: 64,
            StreamQuality.AUDIO_HIGH: 128,
        }
        return bitrates.get(self.quality, 2500)

    def get_framerate(self) -> int:
        """Get framerate for quality preset."""
        if self.framerate:
            return self.framerate

        framerates = {
            StreamQuality.LOW: 15,
            StreamQuality.MEDIUM: 25,
            StreamQuality.HIGH: 30,
            StreamQuality.ULTRA: 30,
        }
        return framerates.get(self.quality, 25)


@dataclass
class StreamSource:
    """Stream source configuration."""

    id: uuid.UUID
    name: str
    source_type: str  # camera, device, screen, audio
    source_url: str | None = None
    device_id: uuid.UUID | None = None
    stream_type: StreamType = StreamType.RTSP
    config: StreamConfig = field(default_factory=StreamConfig)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamSession:
    """Active stream session."""

    id: uuid.UUID
    source: StreamSource
    status: StreamStatus = StreamStatus.INITIALIZING
    started_at: datetime = field(default_factory=datetime.utcnow)
    viewer_count: int = 0
    bytes_sent: int = 0
    frames_sent: int = 0
    errors: list[str] = field(default_factory=list)
    output_urls: dict[str, str] = field(default_factory=dict)
    recording_enabled: bool = False
    recording_id: uuid.UUID | None = None

    def add_error(self, error: str) -> None:
        """Add error message."""
        self.errors.append(f"[{datetime.utcnow().isoformat()}] {error}")
        if len(self.errors) > 100:
            self.errors = self.errors[-100:]


@dataclass
class WebRTCOffer:
    """WebRTC session description."""

    sdp: str
    type: str = "offer"


@dataclass
class WebRTCAnswer:
    """WebRTC answer."""

    sdp: str
    type: str = "answer"


@dataclass
class ICECandidate:
    """WebRTC ICE candidate."""

    candidate: str
    sdp_mid: str
    sdp_m_line_index: int


class StreamingService:
    """Service for managing live streams."""

    def __init__(self, db: AsyncSession):
        """Initialize streaming service."""
        self.db = db
        self._sources: dict[uuid.UUID, StreamSource] = {}
        self._sessions: dict[uuid.UUID, StreamSession] = {}
        self._viewers: dict[uuid.UUID, set[str]] = {}  # session_id -> viewer_ids
        self._event_handlers: list[Callable] = []

    def register_source(self, source: StreamSource) -> None:
        """Register a stream source."""
        self._sources[source.id] = source

    def unregister_source(self, source_id: uuid.UUID) -> None:
        """Unregister a stream source."""
        # Stop any active sessions
        sessions_to_stop = [
            sid for sid, session in self._sessions.items()
            if session.source.id == source_id
        ]
        for sid in sessions_to_stop:
            self._stop_session(sid)

        if source_id in self._sources:
            del self._sources[source_id]

    def get_source(self, source_id: uuid.UUID) -> StreamSource | None:
        """Get source by ID."""
        return self._sources.get(source_id)

    def list_sources(self) -> list[StreamSource]:
        """List all registered sources."""
        return list(self._sources.values())

    async def start_stream(
        self,
        source_id: uuid.UUID,
        stream_type: StreamType | None = None,
        config: StreamConfig | None = None,
        record: bool = False,
    ) -> StreamSession:
        """Start a stream from a source.

        Args:
            source_id: Source to stream from
            stream_type: Override stream type
            config: Override stream config
            record: Whether to record the stream

        Returns:
            Stream session
        """
        source = self._sources.get(source_id)
        if not source:
            raise ValueError(f"Source {source_id} not found")

        # Check if already streaming
        for session in self._sessions.values():
            if session.source.id == source_id and session.status == StreamStatus.ACTIVE:
                return session

        # Create session
        session = StreamSession(
            id=uuid.uuid4(),
            source=source,
            status=StreamStatus.INITIALIZING,
            recording_enabled=record,
        )

        if stream_type:
            session.source.stream_type = stream_type
        if config:
            session.source.config = config

        self._sessions[session.id] = session
        self._viewers[session.id] = set()

        # Generate output URLs based on stream type
        session.output_urls = self._generate_output_urls(session)

        # Mark as active (in real implementation, would start actual streaming)
        session.status = StreamStatus.ACTIVE

        return session

    async def stop_stream(self, session_id: uuid.UUID) -> bool:
        """Stop a stream."""
        return self._stop_session(session_id)

    def _stop_session(self, session_id: uuid.UUID) -> bool:
        """Internal method to stop a session."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.status = StreamStatus.STOPPED

        # Clean up viewers
        if session_id in self._viewers:
            del self._viewers[session_id]

        del self._sessions[session_id]
        return True

    def get_session(self, session_id: uuid.UUID) -> StreamSession | None:
        """Get session by ID."""
        return self._sessions.get(session_id)

    def list_sessions(self, active_only: bool = True) -> list[StreamSession]:
        """List stream sessions."""
        sessions = list(self._sessions.values())
        if active_only:
            sessions = [s for s in sessions if s.status == StreamStatus.ACTIVE]
        return sessions

    def _generate_output_urls(self, session: StreamSession) -> dict[str, str]:
        """Generate output URLs for a stream session."""
        base_path = f"/streams/{session.id}"
        urls = {}

        stream_type = session.source.stream_type

        if stream_type == StreamType.MJPEG:
            urls["mjpeg"] = f"{base_path}/mjpeg"

        elif stream_type == StreamType.HLS:
            urls["hls"] = f"{base_path}/index.m3u8"

        elif stream_type == StreamType.RTSP:
            # Proxy RTSP through HLS for web compatibility
            urls["hls"] = f"{base_path}/index.m3u8"
            urls["rtsp"] = session.source.source_url

        elif stream_type == StreamType.WEBRTC:
            urls["webrtc"] = f"{base_path}/webrtc"
            urls["signaling"] = f"/api/v1/streaming/{session.id}/webrtc/signal"

        elif stream_type == StreamType.DASH:
            urls["dash"] = f"{base_path}/manifest.mpd"

        elif stream_type == StreamType.AUDIO_ONLY:
            urls["audio"] = f"{base_path}/audio"

        return urls

    async def add_viewer(self, session_id: uuid.UUID, viewer_id: str) -> bool:
        """Add a viewer to a stream."""
        if session_id not in self._sessions:
            return False

        if session_id not in self._viewers:
            self._viewers[session_id] = set()

        self._viewers[session_id].add(viewer_id)
        self._sessions[session_id].viewer_count = len(self._viewers[session_id])
        return True

    async def remove_viewer(self, session_id: uuid.UUID, viewer_id: str) -> bool:
        """Remove a viewer from a stream."""
        if session_id not in self._viewers:
            return False

        self._viewers[session_id].discard(viewer_id)
        if session_id in self._sessions:
            self._sessions[session_id].viewer_count = len(self._viewers[session_id])
        return True

    def get_viewer_count(self, session_id: uuid.UUID) -> int:
        """Get viewer count for a session."""
        return len(self._viewers.get(session_id, set()))


class WebRTCSignalingService:
    """WebRTC signaling service for peer connections."""

    def __init__(self):
        """Initialize WebRTC signaling."""
        self._pending_offers: dict[str, WebRTCOffer] = {}
        self._pending_answers: dict[str, WebRTCAnswer] = {}
        self._ice_candidates: dict[str, list[ICECandidate]] = {}
        self._connections: dict[str, dict] = {}

    async def create_offer(
        self,
        session_id: uuid.UUID,
        peer_id: str,
    ) -> dict:
        """Create a WebRTC offer for a stream.

        In a real implementation, this would interface with a
        media server (like Janus, mediasoup, or Kurento) to
        generate the actual SDP offer.
        """
        # Placeholder SDP - real implementation would generate actual SDP
        offer = {
            "type": "offer",
            "sdp": self._generate_sdp_offer(str(session_id)),
        }

        connection_id = f"{session_id}:{peer_id}"
        self._connections[connection_id] = {
            "session_id": str(session_id),
            "peer_id": peer_id,
            "state": "offering",
            "created_at": datetime.utcnow().isoformat(),
        }

        return offer

    async def handle_answer(
        self,
        session_id: uuid.UUID,
        peer_id: str,
        answer: dict,
    ) -> bool:
        """Handle WebRTC answer from peer."""
        connection_id = f"{session_id}:{peer_id}"

        if connection_id not in self._connections:
            return False

        self._connections[connection_id]["state"] = "answered"
        self._connections[connection_id]["answer"] = answer

        return True

    async def add_ice_candidate(
        self,
        session_id: uuid.UUID,
        peer_id: str,
        candidate: dict,
    ) -> bool:
        """Add ICE candidate."""
        connection_id = f"{session_id}:{peer_id}"

        if connection_id not in self._ice_candidates:
            self._ice_candidates[connection_id] = []

        self._ice_candidates[connection_id].append(ICECandidate(
            candidate=candidate.get("candidate", ""),
            sdp_mid=candidate.get("sdpMid", ""),
            sdp_m_line_index=candidate.get("sdpMLineIndex", 0),
        ))

        return True

    async def get_ice_candidates(
        self,
        session_id: uuid.UUID,
        peer_id: str,
    ) -> list[dict]:
        """Get pending ICE candidates."""
        connection_id = f"{session_id}:{peer_id}"
        candidates = self._ice_candidates.get(connection_id, [])

        return [
            {
                "candidate": c.candidate,
                "sdpMid": c.sdp_mid,
                "sdpMLineIndex": c.sdp_m_line_index,
            }
            for c in candidates
        ]

    def _generate_sdp_offer(self, session_id: str) -> str:
        """Generate placeholder SDP offer.

        Real implementation would use actual media server.
        """
        return f"""v=0
o=- {session_id} 2 IN IP4 127.0.0.1
s=Vigilia Stream
t=0 0
a=group:BUNDLE 0 1
a=msid-semantic: WMS
m=video 9 UDP/TLS/RTP/SAVPF 96
c=IN IP4 0.0.0.0
a=rtcp:9 IN IP4 0.0.0.0
a=setup:actpass
a=mid:0
a=sendonly
a=rtcp-mux
a=rtpmap:96 H264/90000
m=audio 9 UDP/TLS/RTP/SAVPF 111
c=IN IP4 0.0.0.0
a=rtcp:9 IN IP4 0.0.0.0
a=setup:actpass
a=mid:1
a=sendonly
a=rtcp-mux
a=rtpmap:111 opus/48000/2
"""


class HLSSegmentManager:
    """Manages HLS stream segments."""

    def __init__(self, segment_duration: int = 2):
        """Initialize HLS segment manager."""
        self.segment_duration = segment_duration
        self._segments: dict[uuid.UUID, list[dict]] = {}
        self._playlists: dict[uuid.UUID, str] = {}

    def add_segment(
        self,
        session_id: uuid.UUID,
        segment_data: bytes,
        duration: float,
    ) -> str:
        """Add a new segment for a session.

        Returns segment filename.
        """
        if session_id not in self._segments:
            self._segments[session_id] = []

        segment_index = len(self._segments[session_id])
        segment_name = f"segment_{segment_index:05d}.ts"

        self._segments[session_id].append({
            "name": segment_name,
            "duration": duration,
            "data": segment_data,
            "created_at": datetime.utcnow(),
        })

        # Keep only last 10 segments (sliding window)
        if len(self._segments[session_id]) > 10:
            self._segments[session_id] = self._segments[session_id][-10:]

        # Update playlist
        self._update_playlist(session_id)

        return segment_name

    def get_playlist(self, session_id: uuid.UUID) -> str | None:
        """Get HLS playlist for session."""
        return self._playlists.get(session_id)

    def get_segment(
        self,
        session_id: uuid.UUID,
        segment_name: str,
    ) -> bytes | None:
        """Get segment data."""
        segments = self._segments.get(session_id, [])
        for segment in segments:
            if segment["name"] == segment_name:
                return segment["data"]
        return None

    def _update_playlist(self, session_id: uuid.UUID) -> None:
        """Update HLS playlist."""
        segments = self._segments.get(session_id, [])
        if not segments:
            return

        # Build M3U8 playlist
        lines = [
            "#EXTM3U",
            "#EXT-X-VERSION:3",
            f"#EXT-X-TARGETDURATION:{self.segment_duration + 1}",
            f"#EXT-X-MEDIA-SEQUENCE:{max(0, len(segments) - 10)}",
        ]

        for segment in segments:
            lines.append(f"#EXTINF:{segment['duration']:.3f},")
            lines.append(segment["name"])

        self._playlists[session_id] = "\n".join(lines)

    def cleanup_session(self, session_id: uuid.UUID) -> None:
        """Clean up session data."""
        if session_id in self._segments:
            del self._segments[session_id]
        if session_id in self._playlists:
            del self._playlists[session_id]


class StreamTranscoder:
    """Handles stream transcoding operations.

    In production, this would interface with FFmpeg or
    a dedicated transcoding service.
    """

    def __init__(self):
        """Initialize transcoder."""
        self._active_jobs: dict[uuid.UUID, dict] = {}

    async def start_transcode(
        self,
        session_id: uuid.UUID,
        input_url: str,
        output_format: str,
        config: StreamConfig,
    ) -> bool:
        """Start transcoding job.

        Args:
            session_id: Stream session ID
            input_url: Source stream URL
            output_format: Target format (hls, dash, etc.)
            config: Stream configuration

        Returns:
            True if started successfully
        """
        if session_id in self._active_jobs:
            return False

        resolution = config.get_resolution()
        bitrate = config.get_bitrate()
        framerate = config.get_framerate()

        # Build FFmpeg command (placeholder)
        ffmpeg_cmd = self._build_ffmpeg_command(
            input_url=input_url,
            output_format=output_format,
            width=resolution[0],
            height=resolution[1],
            bitrate=bitrate,
            framerate=framerate,
            codec=config.codec,
            audio_codec=config.audio_codec,
            audio_enabled=config.audio_enabled,
        )

        self._active_jobs[session_id] = {
            "command": ffmpeg_cmd,
            "started_at": datetime.utcnow(),
            "status": "running",
        }

        return True

    async def stop_transcode(self, session_id: uuid.UUID) -> bool:
        """Stop transcoding job."""
        if session_id not in self._active_jobs:
            return False

        self._active_jobs[session_id]["status"] = "stopped"
        del self._active_jobs[session_id]
        return True

    def _build_ffmpeg_command(
        self,
        input_url: str,
        output_format: str,
        width: int,
        height: int,
        bitrate: int,
        framerate: int,
        codec: str,
        audio_codec: str,
        audio_enabled: bool,
    ) -> str:
        """Build FFmpeg command string.

        This is a placeholder - real implementation would
        execute this command in a subprocess.
        """
        cmd_parts = [
            "ffmpeg",
            f"-i {input_url}",
            f"-c:v {codec}",
            f"-b:v {bitrate}k",
            f"-vf scale={width}:{height}",
            f"-r {framerate}",
        ]

        if audio_enabled:
            cmd_parts.extend([
                f"-c:a {audio_codec}",
                "-b:a 128k",
            ])
        else:
            cmd_parts.append("-an")

        if output_format == "hls":
            cmd_parts.extend([
                "-f hls",
                "-hls_time 2",
                "-hls_list_size 10",
                "-hls_flags delete_segments",
            ])
        elif output_format == "dash":
            cmd_parts.extend([
                "-f dash",
                "-seg_duration 2",
            ])

        return " ".join(cmd_parts)
