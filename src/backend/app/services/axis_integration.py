"""Axis Camera and Audio Device Integration.

This service provides integration with Axis network cameras
and audio devices using the VAPIX API.

Supported features:
- Camera discovery and configuration
- Live video streaming (MJPEG, RTSP)
- PTZ control (pan, tilt, zoom)
- Audio streaming and intercom
- Event subscription (motion, audio, analytics)
- Recording triggers
"""

import asyncio
import uuid
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator
from urllib.parse import urlencode

import httpx

from sqlalchemy.ext.asyncio import AsyncSession


class DeviceType(str, Enum):
    """Axis device types."""

    CAMERA = "camera"
    ENCODER = "encoder"
    AUDIO = "audio"
    INTERCOM = "intercom"
    SPEAKER = "speaker"
    IO_RELAY = "io_relay"


class StreamType(str, Enum):
    """Video stream types."""

    MJPEG = "mjpeg"
    RTSP = "rtsp"
    H264 = "h264"
    H265 = "h265"


class PTZCommand(str, Enum):
    """PTZ control commands."""

    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    ZOOM_IN = "zoomin"
    ZOOM_OUT = "zoomout"
    HOME = "home"
    STOP = "stop"


class EventType(str, Enum):
    """Axis event types."""

    MOTION = "motion"
    AUDIO = "audio"
    PIR = "pir"
    TAMPERING = "tampering"
    IO_TRIGGER = "io"
    ANALYTICS = "analytics"
    VIDEO_LOSS = "video_loss"
    DISK_FULL = "disk_full"


@dataclass
class AxisDevice:
    """Axis device configuration."""

    id: uuid.UUID
    name: str
    host: str
    port: int = 80
    username: str = "root"
    password: str = ""
    device_type: DeviceType = DeviceType.CAMERA
    model: str | None = None
    serial_number: str | None = None
    firmware_version: str | None = None
    mac_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_name: str | None = None
    ptz_enabled: bool = False
    audio_enabled: bool = False
    active: bool = True
    extra_config: dict[str, Any] = field(default_factory=dict)

    @property
    def base_url(self) -> str:
        """Get base URL for device."""
        return f"http://{self.host}:{self.port}"

    def get_auth(self) -> tuple[str, str]:
        """Get authentication tuple."""
        return (self.username, self.password)


@dataclass
class StreamConfig:
    """Video stream configuration."""

    resolution: str = "1280x720"
    fps: int = 15
    compression: int = 30
    stream_type: StreamType = StreamType.MJPEG


@dataclass
class AxisEvent:
    """Event received from Axis device."""

    device_id: uuid.UUID
    event_type: EventType
    timestamp: datetime
    source: str | None = None
    value: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


class VAPIXClient:
    """Client for Axis VAPIX API."""

    def __init__(self, device: AxisDevice, timeout: float = 10.0):
        """Initialize VAPIX client."""
        self.device = device
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "VAPIXClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            auth=httpx.DigestAuth(*self.device.get_auth()),
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        data: dict | None = None,
    ) -> httpx.Response:
        """Make HTTP request to device."""
        if not self._client:
            raise RuntimeError("Client not initialized")

        url = f"{self.device.base_url}{path}"
        response = await self._client.request(
            method=method,
            url=url,
            params=params,
            data=data,
        )
        response.raise_for_status()
        return response

    async def get_device_info(self) -> dict[str, Any]:
        """Get device information.

        Uses VAPIX Basic Device Information API.
        """
        # Try JSON API first
        try:
            response = await self._request(
                "POST",
                "/axis-cgi/basicdeviceinfo.cgi",
                data={"apiVersion": "1.0", "method": "getAllProperties"},
            )
            return response.json()
        except Exception:
            pass

        # Fall back to parameter API
        response = await self._request(
            "GET",
            "/axis-cgi/param.cgi",
            params={"action": "list", "group": "Brand"},
        )

        info = {}
        for line in response.text.strip().split("\n"):
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.replace("root.Brand.", "")
                info[key] = value

        return info

    async def get_parameter(self, group: str) -> dict[str, str]:
        """Get device parameters."""
        response = await self._request(
            "GET",
            "/axis-cgi/param.cgi",
            params={"action": "list", "group": group},
        )

        params = {}
        for line in response.text.strip().split("\n"):
            if "=" in line:
                key, value = line.split("=", 1)
                params[key] = value

        return params

    async def set_parameter(self, param: str, value: str) -> bool:
        """Set a device parameter."""
        response = await self._request(
            "GET",
            "/axis-cgi/param.cgi",
            params={"action": "update", param: value},
        )
        return "OK" in response.text

    def get_mjpeg_url(self, config: StreamConfig | None = None) -> str:
        """Get MJPEG stream URL."""
        config = config or StreamConfig()

        params = {
            "resolution": config.resolution,
            "fps": config.fps,
            "compression": config.compression,
        }

        return f"{self.device.base_url}/axis-cgi/mjpg/video.cgi?{urlencode(params)}"

    def get_rtsp_url(
        self,
        stream_profile: str = "videostream",
        channel: int = 1,
    ) -> str:
        """Get RTSP stream URL."""
        auth = f"{self.device.username}:{self.device.password}@" if self.device.password else ""
        return f"rtsp://{auth}{self.device.host}:{554}/axis-media/media.amp?videocodec=h264&camera={channel}"

    def get_snapshot_url(self, resolution: str = "1280x720") -> str:
        """Get snapshot URL."""
        return f"{self.device.base_url}/axis-cgi/jpg/image.cgi?resolution={resolution}"

    async def get_snapshot(self, resolution: str = "1280x720") -> bytes:
        """Get camera snapshot."""
        response = await self._request(
            "GET",
            "/axis-cgi/jpg/image.cgi",
            params={"resolution": resolution},
        )
        return response.content

    async def ptz_command(self, command: PTZCommand, speed: int = 50) -> bool:
        """Send PTZ command.

        Args:
            command: PTZ command
            speed: Movement speed (1-100)
        """
        if not self.device.ptz_enabled:
            return False

        # Map command to VAPIX format
        ptz_map = {
            PTZCommand.UP: {"move": "up"},
            PTZCommand.DOWN: {"move": "down"},
            PTZCommand.LEFT: {"move": "left"},
            PTZCommand.RIGHT: {"move": "right"},
            PTZCommand.ZOOM_IN: {"rzoom": speed},
            PTZCommand.ZOOM_OUT: {"rzoom": -speed},
            PTZCommand.HOME: {"move": "home"},
            PTZCommand.STOP: {"move": "stop"},
        }

        params = ptz_map.get(command, {})
        if command in [PTZCommand.UP, PTZCommand.DOWN, PTZCommand.LEFT, PTZCommand.RIGHT]:
            params["speed"] = speed

        try:
            await self._request(
                "GET",
                "/axis-cgi/com/ptz.cgi",
                params=params,
            )
            return True
        except Exception:
            return False

    async def ptz_goto_preset(self, preset: int) -> bool:
        """Go to a PTZ preset position."""
        if not self.device.ptz_enabled:
            return False

        try:
            await self._request(
                "GET",
                "/axis-cgi/com/ptz.cgi",
                params={"gotoserverpresetno": preset},
            )
            return True
        except Exception:
            return False

    async def ptz_absolute(
        self,
        pan: float | None = None,
        tilt: float | None = None,
        zoom: float | None = None,
    ) -> bool:
        """Set absolute PTZ position.

        Args:
            pan: Pan angle in degrees
            tilt: Tilt angle in degrees
            zoom: Zoom level (1-9999)
        """
        if not self.device.ptz_enabled:
            return False

        params = {}
        if pan is not None:
            params["pan"] = pan
        if tilt is not None:
            params["tilt"] = tilt
        if zoom is not None:
            params["zoom"] = zoom

        if not params:
            return False

        try:
            await self._request(
                "GET",
                "/axis-cgi/com/ptz.cgi",
                params=params,
            )
            return True
        except Exception:
            return False

    async def play_audio(self, audio_clip: str) -> bool:
        """Play audio clip on device speaker.

        Args:
            audio_clip: Path to audio clip on device
        """
        if not self.device.audio_enabled:
            return False

        try:
            await self._request(
                "GET",
                "/axis-cgi/playclip.cgi",
                params={"clip": audio_clip},
            )
            return True
        except Exception:
            return False

    async def get_audio_clips(self) -> list[str]:
        """Get list of available audio clips."""
        try:
            response = await self._request(
                "GET",
                "/axis-cgi/param.cgi",
                params={"action": "list", "group": "MediaClip"},
            )

            clips = []
            for line in response.text.strip().split("\n"):
                if ".Location=" in line:
                    clips.append(line.split("=", 1)[1])
            return clips
        except Exception:
            return []

    async def trigger_output(self, port: int = 1, state: bool = True) -> bool:
        """Trigger digital output.

        Args:
            port: Output port number
            state: Active (True) or Inactive (False)
        """
        try:
            action = "1" if state else "0"
            await self._request(
                "GET",
                "/axis-cgi/io/port.cgi",
                params={"action": action, "port": port},
            )
            return True
        except Exception:
            return False

    async def get_io_status(self) -> dict[str, Any]:
        """Get I/O port status."""
        try:
            response = await self._request(
                "GET",
                "/axis-cgi/io/port.cgi",
                params={"action": "list"},
            )
            return {"raw": response.text}
        except Exception:
            return {}


class AxisEventSubscriber:
    """Subscribe to events from Axis devices."""

    def __init__(self, device: AxisDevice):
        """Initialize event subscriber."""
        self.device = device
        self._running = False
        self._client: httpx.AsyncClient | None = None

    async def subscribe(self) -> AsyncIterator[AxisEvent]:
        """Subscribe to device events.

        Yields events as they occur.
        """
        self._running = True
        self._client = httpx.AsyncClient(
            auth=httpx.DigestAuth(*self.device.get_auth()),
            timeout=None,  # Long polling
        )

        try:
            # Subscribe to ACAP event stream
            url = f"{self.device.base_url}/vapix/services"

            # SOAP request for event subscription
            soap_body = """<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
                <soap:Body>
                    <tev:Subscribe xmlns:tev="http://www.onvif.org/ver10/events/wsdl">
                        <tev:InitialTerminationTime>PT1H</tev:InitialTerminationTime>
                    </tev:Subscribe>
                </soap:Body>
            </soap:Envelope>"""

            async with self._client.stream(
                "POST",
                url,
                content=soap_body,
                headers={"Content-Type": "application/soap+xml"},
            ) as response:
                async for line in response.aiter_lines():
                    if not self._running:
                        break

                    event = self._parse_event(line)
                    if event:
                        yield event

        except Exception:
            pass
        finally:
            if self._client:
                await self._client.aclose()
                self._client = None

    def stop(self) -> None:
        """Stop event subscription."""
        self._running = False

    def _parse_event(self, data: str) -> AxisEvent | None:
        """Parse event from stream data."""
        if not data or not data.strip():
            return None

        # Parse different event formats
        event_type = None
        value = None

        if "motion" in data.lower():
            event_type = EventType.MOTION
            value = "1" if "true" in data.lower() else "0"
        elif "audio" in data.lower():
            event_type = EventType.AUDIO
            value = "1"
        elif "pir" in data.lower():
            event_type = EventType.PIR
            value = "1"
        elif "tampering" in data.lower():
            event_type = EventType.TAMPERING
            value = "1"
        elif "digital" in data.lower() or "io" in data.lower():
            event_type = EventType.IO_TRIGGER
            value = "1" if "active" in data.lower() else "0"

        if event_type:
            return AxisEvent(
                device_id=self.device.id,
                event_type=event_type,
                timestamp=datetime.utcnow(),
                value=value,
                raw_data={"line": data},
            )

        return None


class AxisDeviceManager:
    """Manage multiple Axis devices."""

    def __init__(self, db: AsyncSession):
        """Initialize device manager."""
        self.db = db
        self._devices: dict[uuid.UUID, AxisDevice] = {}
        self._event_subscribers: dict[uuid.UUID, AxisEventSubscriber] = {}

    def register_device(self, device: AxisDevice) -> None:
        """Register a device."""
        self._devices[device.id] = device

    def unregister_device(self, device_id: uuid.UUID) -> None:
        """Unregister a device."""
        if device_id in self._event_subscribers:
            self._event_subscribers[device_id].stop()
            del self._event_subscribers[device_id]
        if device_id in self._devices:
            del self._devices[device_id]

    def get_device(self, device_id: uuid.UUID) -> AxisDevice | None:
        """Get device by ID."""
        return self._devices.get(device_id)

    def list_devices(self, active_only: bool = True) -> list[AxisDevice]:
        """List all devices."""
        devices = list(self._devices.values())
        if active_only:
            devices = [d for d in devices if d.active]
        return devices

    async def discover_device(
        self,
        host: str,
        port: int = 80,
        username: str = "root",
        password: str = "",
    ) -> AxisDevice | None:
        """Discover and probe a device.

        Returns device info if accessible.
        """
        device = AxisDevice(
            id=uuid.uuid4(),
            name=f"Axis Device ({host})",
            host=host,
            port=port,
            username=username,
            password=password,
        )

        try:
            async with VAPIXClient(device) as client:
                info = await client.get_device_info()

                # Update device with discovered info
                if isinstance(info, dict):
                    if "data" in info:
                        props = info["data"]["propertyList"]
                        device.model = props.get("ProdNbr", props.get("prodNbr"))
                        device.serial_number = props.get("SerialNumber", props.get("serialNumber"))
                        device.firmware_version = props.get("Version", props.get("firmwareVersion"))
                        device.mac_address = props.get("MacAddress", props.get("macAddress"))
                    else:
                        device.model = info.get("ProdNbr")
                        device.serial_number = info.get("SerialNumber")
                        device.firmware_version = info.get("Version")

                device.name = f"{device.model or 'Axis'} ({host})"

                # Check for PTZ support
                try:
                    ptz_params = await client.get_parameter("PTZ")
                    device.ptz_enabled = bool(ptz_params)
                except Exception:
                    device.ptz_enabled = False

                # Check for audio support
                try:
                    audio_params = await client.get_parameter("Audio")
                    device.audio_enabled = bool(audio_params)
                except Exception:
                    device.audio_enabled = False

                return device

        except Exception:
            return None

    async def get_snapshot(
        self,
        device_id: uuid.UUID,
        resolution: str = "1280x720",
    ) -> bytes | None:
        """Get snapshot from device."""
        device = self._devices.get(device_id)
        if not device:
            return None

        try:
            async with VAPIXClient(device) as client:
                return await client.get_snapshot(resolution)
        except Exception:
            return None

    async def send_ptz_command(
        self,
        device_id: uuid.UUID,
        command: PTZCommand,
        speed: int = 50,
    ) -> bool:
        """Send PTZ command to device."""
        device = self._devices.get(device_id)
        if not device or not device.ptz_enabled:
            return False

        try:
            async with VAPIXClient(device) as client:
                return await client.ptz_command(command, speed)
        except Exception:
            return False

    async def play_audio(
        self,
        device_id: uuid.UUID,
        clip: str,
    ) -> bool:
        """Play audio clip on device."""
        device = self._devices.get(device_id)
        if not device or not device.audio_enabled:
            return False

        try:
            async with VAPIXClient(device) as client:
                return await client.play_audio(clip)
        except Exception:
            return False

    async def trigger_output(
        self,
        device_id: uuid.UUID,
        port: int = 1,
        state: bool = True,
    ) -> bool:
        """Trigger device output."""
        device = self._devices.get(device_id)
        if not device:
            return False

        try:
            async with VAPIXClient(device) as client:
                return await client.trigger_output(port, state)
        except Exception:
            return False

    def get_stream_urls(
        self,
        device_id: uuid.UUID,
        config: StreamConfig | None = None,
    ) -> dict[str, str] | None:
        """Get stream URLs for device."""
        device = self._devices.get(device_id)
        if not device:
            return None

        # Create temporary client for URL generation
        client = VAPIXClient(device)

        return {
            "mjpeg": client.get_mjpeg_url(config),
            "rtsp": client.get_rtsp_url(),
            "snapshot": client.get_snapshot_url(),
        }
