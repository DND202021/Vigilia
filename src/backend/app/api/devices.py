"""Device Management API endpoints.

Handles Axis cameras, audio devices, and other integrated hardware.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user, require_permission, Permission
from app.models.user import User
from app.services.axis_integration import (
    AxisDeviceManager,
    AxisDevice,
    DeviceType,
    StreamType,
    StreamConfig,
    PTZCommand,
    VAPIXClient,
)

router = APIRouter()


# In-memory device storage (would be DB in production)
_device_manager: AxisDeviceManager | None = None


def get_device_manager(db: AsyncSession = Depends(get_db)) -> AxisDeviceManager:
    """Get or create device manager."""
    global _device_manager
    if _device_manager is None:
        _device_manager = AxisDeviceManager(db)
    return _device_manager


class DeviceCreate(BaseModel):
    """Create device request."""

    name: str = Field(..., min_length=1, max_length=255)
    host: str = Field(..., min_length=1)
    port: int = Field(80, ge=1, le=65535)
    username: str = "root"
    password: str = ""
    device_type: str = "camera"
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    location_name: str | None = None


class DeviceResponse(BaseModel):
    """Device response."""

    id: str
    name: str
    host: str
    port: int
    device_type: str
    model: str | None
    serial_number: str | None
    firmware_version: str | None
    mac_address: str | None
    latitude: float | None
    longitude: float | None
    location_name: str | None
    ptz_enabled: bool
    audio_enabled: bool
    active: bool


class DeviceDiscoverRequest(BaseModel):
    """Device discovery request."""

    host: str
    port: int = 80
    username: str = "root"
    password: str = ""


class StreamUrlsResponse(BaseModel):
    """Stream URLs response."""

    mjpeg: str
    rtsp: str
    snapshot: str


class PTZRequest(BaseModel):
    """PTZ command request."""

    command: str = Field(..., description="PTZ command: up, down, left, right, zoomin, zoomout, home, stop")
    speed: int = Field(50, ge=1, le=100)


class PTZAbsoluteRequest(BaseModel):
    """Absolute PTZ position request."""

    pan: float | None = Field(None, ge=-180, le=180)
    tilt: float | None = Field(None, ge=-90, le=90)
    zoom: float | None = Field(None, ge=1, le=9999)


class AudioPlayRequest(BaseModel):
    """Audio playback request."""

    clip: str = Field(..., description="Audio clip path on device")


class OutputTriggerRequest(BaseModel):
    """I/O output trigger request."""

    port: int = Field(1, ge=1, le=8)
    state: bool = True


@router.post("/discover", response_model=DeviceResponse)
async def discover_device(
    request: DeviceDiscoverRequest,
    manager: AxisDeviceManager = Depends(get_device_manager),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> DeviceResponse:
    """Discover and probe an Axis device.

    Connects to the device and retrieves its information.
    """
    device = await manager.discover_device(
        host=request.host,
        port=request.port,
        username=request.username,
        password=request.password,
    )

    if not device:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not connect to device. Check host, port, and credentials.",
        )

    return DeviceResponse(
        id=str(device.id),
        name=device.name,
        host=device.host,
        port=device.port,
        device_type=device.device_type.value,
        model=device.model,
        serial_number=device.serial_number,
        firmware_version=device.firmware_version,
        mac_address=device.mac_address,
        latitude=device.latitude,
        longitude=device.longitude,
        location_name=device.location_name,
        ptz_enabled=device.ptz_enabled,
        audio_enabled=device.audio_enabled,
        active=device.active,
    )


@router.post("", response_model=DeviceResponse)
async def create_device(
    request: DeviceCreate,
    manager: AxisDeviceManager = Depends(get_device_manager),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> DeviceResponse:
    """Register a new device.

    The device will be probed to verify connectivity.
    """
    # Probe device first
    device = await manager.discover_device(
        host=request.host,
        port=request.port,
        username=request.username,
        password=request.password,
    )

    if not device:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not connect to device. Check host, port, and credentials.",
        )

    # Update with user-provided values
    device.name = request.name
    device.latitude = request.latitude
    device.longitude = request.longitude
    device.location_name = request.location_name

    try:
        device.device_type = DeviceType(request.device_type)
    except ValueError:
        device.device_type = DeviceType.CAMERA

    # Register device
    manager.register_device(device)

    return DeviceResponse(
        id=str(device.id),
        name=device.name,
        host=device.host,
        port=device.port,
        device_type=device.device_type.value,
        model=device.model,
        serial_number=device.serial_number,
        firmware_version=device.firmware_version,
        mac_address=device.mac_address,
        latitude=device.latitude,
        longitude=device.longitude,
        location_name=device.location_name,
        ptz_enabled=device.ptz_enabled,
        audio_enabled=device.audio_enabled,
        active=device.active,
    )


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    active_only: bool = True,
    device_type: str | None = None,
    manager: AxisDeviceManager = Depends(get_device_manager),
    current_user: User = Depends(get_current_active_user),
) -> list[DeviceResponse]:
    """List all registered devices."""
    devices = manager.list_devices(active_only=active_only)

    if device_type:
        try:
            dtype = DeviceType(device_type)
            devices = [d for d in devices if d.device_type == dtype]
        except ValueError:
            pass

    return [
        DeviceResponse(
            id=str(d.id),
            name=d.name,
            host=d.host,
            port=d.port,
            device_type=d.device_type.value,
            model=d.model,
            serial_number=d.serial_number,
            firmware_version=d.firmware_version,
            mac_address=d.mac_address,
            latitude=d.latitude,
            longitude=d.longitude,
            location_name=d.location_name,
            ptz_enabled=d.ptz_enabled,
            audio_enabled=d.audio_enabled,
            active=d.active,
        )
        for d in devices
    ]


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    manager: AxisDeviceManager = Depends(get_device_manager),
    current_user: User = Depends(get_current_active_user),
) -> DeviceResponse:
    """Get device by ID."""
    try:
        device_uuid = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format",
        )

    device = manager.get_device(device_uuid)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    return DeviceResponse(
        id=str(device.id),
        name=device.name,
        host=device.host,
        port=device.port,
        device_type=device.device_type.value,
        model=device.model,
        serial_number=device.serial_number,
        firmware_version=device.firmware_version,
        mac_address=device.mac_address,
        latitude=device.latitude,
        longitude=device.longitude,
        location_name=device.location_name,
        ptz_enabled=device.ptz_enabled,
        audio_enabled=device.audio_enabled,
        active=device.active,
    )


@router.delete("/{device_id}")
async def delete_device(
    device_id: str,
    manager: AxisDeviceManager = Depends(get_device_manager),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> dict:
    """Delete a device."""
    try:
        device_uuid = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format",
        )

    device = manager.get_device(device_uuid)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    manager.unregister_device(device_uuid)

    return {"message": f"Device {device.name} deleted"}


@router.get("/{device_id}/streams", response_model=StreamUrlsResponse)
async def get_stream_urls(
    device_id: str,
    resolution: str = "1280x720",
    manager: AxisDeviceManager = Depends(get_device_manager),
    current_user: User = Depends(get_current_active_user),
) -> StreamUrlsResponse:
    """Get streaming URLs for a device."""
    try:
        device_uuid = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format",
        )

    config = StreamConfig(resolution=resolution)
    urls = manager.get_stream_urls(device_uuid, config)

    if not urls:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    return StreamUrlsResponse(**urls)


@router.get("/{device_id}/snapshot")
async def get_snapshot(
    device_id: str,
    resolution: str = "1280x720",
    manager: AxisDeviceManager = Depends(get_device_manager),
    current_user: User = Depends(get_current_active_user),
) -> Response:
    """Get a snapshot from the device."""
    try:
        device_uuid = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format",
        )

    image_data = await manager.get_snapshot(device_uuid, resolution)

    if not image_data:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not get snapshot from device",
        )

    return Response(
        content=image_data,
        media_type="image/jpeg",
    )


@router.post("/{device_id}/ptz")
async def send_ptz_command(
    device_id: str,
    request: PTZRequest,
    manager: AxisDeviceManager = Depends(get_device_manager),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Send PTZ command to device."""
    try:
        device_uuid = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format",
        )

    device = manager.get_device(device_uuid)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    if not device.ptz_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device does not support PTZ",
        )

    try:
        command = PTZCommand(request.command.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid PTZ command. Valid commands: {[c.value for c in PTZCommand]}",
        )

    success = await manager.send_ptz_command(device_uuid, command, request.speed)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to send PTZ command",
        )

    return {"message": f"PTZ command {command.value} sent"}


@router.post("/{device_id}/ptz/absolute")
async def set_ptz_position(
    device_id: str,
    request: PTZAbsoluteRequest,
    manager: AxisDeviceManager = Depends(get_device_manager),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Set absolute PTZ position."""
    try:
        device_uuid = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format",
        )

    device = manager.get_device(device_uuid)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    if not device.ptz_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device does not support PTZ",
        )

    # Use VAPIX client directly for absolute positioning
    try:
        async with VAPIXClient(device) as client:
            success = await client.ptz_absolute(
                pan=request.pan,
                tilt=request.tilt,
                zoom=request.zoom,
            )
    except Exception:
        success = False

    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to set PTZ position",
        )

    return {"message": "PTZ position set"}


@router.post("/{device_id}/ptz/preset/{preset}")
async def goto_ptz_preset(
    device_id: str,
    preset: int,
    manager: AxisDeviceManager = Depends(get_device_manager),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Go to PTZ preset position."""
    try:
        device_uuid = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format",
        )

    device = manager.get_device(device_uuid)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    if not device.ptz_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device does not support PTZ",
        )

    try:
        async with VAPIXClient(device) as client:
            success = await client.ptz_goto_preset(preset)
    except Exception:
        success = False

    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to go to preset",
        )

    return {"message": f"Moving to preset {preset}"}


@router.post("/{device_id}/audio/play")
async def play_audio(
    device_id: str,
    request: AudioPlayRequest,
    manager: AxisDeviceManager = Depends(get_device_manager),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Play audio clip on device."""
    try:
        device_uuid = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format",
        )

    device = manager.get_device(device_uuid)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    if not device.audio_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device does not support audio",
        )

    success = await manager.play_audio(device_uuid, request.clip)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to play audio",
        )

    return {"message": f"Playing audio clip: {request.clip}"}


@router.get("/{device_id}/audio/clips")
async def list_audio_clips(
    device_id: str,
    manager: AxisDeviceManager = Depends(get_device_manager),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """List available audio clips on device."""
    try:
        device_uuid = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format",
        )

    device = manager.get_device(device_uuid)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    try:
        async with VAPIXClient(device) as client:
            clips = await client.get_audio_clips()
    except Exception:
        clips = []

    return {"clips": clips}


@router.post("/{device_id}/io/trigger")
async def trigger_output(
    device_id: str,
    request: OutputTriggerRequest,
    manager: AxisDeviceManager = Depends(get_device_manager),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Trigger I/O output on device."""
    try:
        device_uuid = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format",
        )

    success = await manager.trigger_output(device_uuid, request.port, request.state)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to trigger output",
        )

    state_str = "activated" if request.state else "deactivated"
    return {"message": f"Output port {request.port} {state_str}"}


@router.get("/{device_id}/io/status")
async def get_io_status(
    device_id: str,
    manager: AxisDeviceManager = Depends(get_device_manager),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Get I/O port status from device."""
    try:
        device_uuid = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format",
        )

    device = manager.get_device(device_uuid)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    try:
        async with VAPIXClient(device) as client:
            status_info = await client.get_io_status()
    except Exception:
        status_info = {}

    return status_info
