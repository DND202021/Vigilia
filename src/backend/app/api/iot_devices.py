"""IoT Device Management API endpoints for sound anomaly detection devices."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.device import DeviceType, DeviceStatus
from app.services.device_service import DeviceService, DeviceError

router = APIRouter()


# ==================== Schemas ====================

class IoTDeviceCreate(BaseModel):
    """Create IoT device request."""
    name: str = Field(..., min_length=1, max_length=200)
    device_type: str = Field(..., description="microphone, camera, sensor, gateway, other")
    building_id: str
    serial_number: str | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    model: str | None = None
    firmware_version: str | None = None
    manufacturer: str = "Axis"
    floor_plan_id: str | None = None
    position_x: float | None = Field(None, ge=0, le=100)
    position_y: float | None = Field(None, ge=0, le=100)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    location_name: str | None = None
    config: dict | None = None
    capabilities: list[str] | None = None


class IoTDeviceUpdate(BaseModel):
    """Update IoT device request."""
    name: str | None = Field(None, min_length=1, max_length=200)
    serial_number: str | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    model: str | None = None
    firmware_version: str | None = None
    manufacturer: str | None = None
    floor_plan_id: str | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    location_name: str | None = None
    capabilities: list[str] | None = None


class PositionUpdate(BaseModel):
    """Update device position on floor plan."""
    floor_plan_id: str
    position_x: float = Field(..., ge=0, le=100)
    position_y: float = Field(..., ge=0, le=100)


class ConfigUpdate(BaseModel):
    """Update device detection configuration."""
    config: dict


class IoTDeviceResponse(BaseModel):
    """IoT device response."""
    id: str
    name: str
    device_type: str
    serial_number: str | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    model: str | None = None
    firmware_version: str | None = None
    manufacturer: str
    building_id: str
    floor_plan_id: str | None = None
    position_x: float | None = None
    position_y: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_name: str | None = None
    status: str
    last_seen: str | None = None
    connection_quality: int | None = None
    config: dict | None = None
    capabilities: list | None = None
    created_at: str
    updated_at: str


class PaginatedDeviceResponse(BaseModel):
    """Paginated device response."""
    items: list[IoTDeviceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== Helpers ====================

def device_to_response(device) -> IoTDeviceResponse:
    """Convert device model to response."""
    return IoTDeviceResponse(
        id=str(device.id),
        name=device.name,
        device_type=device.device_type.value if hasattr(device.device_type, 'value') else device.device_type,
        serial_number=device.serial_number,
        ip_address=device.ip_address,
        mac_address=device.mac_address,
        model=device.model,
        firmware_version=device.firmware_version,
        manufacturer=device.manufacturer,
        building_id=str(device.building_id),
        floor_plan_id=str(device.floor_plan_id) if device.floor_plan_id else None,
        position_x=device.position_x,
        position_y=device.position_y,
        latitude=device.latitude,
        longitude=device.longitude,
        location_name=device.location_name,
        status=device.status.value if hasattr(device.status, 'value') else device.status,
        last_seen=device.last_seen.isoformat() if device.last_seen else None,
        connection_quality=device.connection_quality,
        config=device.config,
        capabilities=device.capabilities,
        created_at=device.created_at.isoformat() if device.created_at else "",
        updated_at=device.updated_at.isoformat() if device.updated_at else "",
    )


# ==================== Endpoints ====================

@router.get("", response_model=PaginatedDeviceResponse)
async def list_iot_devices(
    building_id: str | None = None,
    floor_plan_id: str | None = None,
    device_type: str | None = None,
    device_status: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedDeviceResponse:
    """List IoT devices with optional filters."""
    service = DeviceService(db)

    bid = uuid.UUID(building_id) if building_id else None
    fpid = uuid.UUID(floor_plan_id) if floor_plan_id else None
    dtype = DeviceType(device_type) if device_type else None
    dstatus = DeviceStatus(device_status) if device_status else None

    devices, total = await service.list_devices(
        building_id=bid,
        floor_plan_id=fpid,
        device_type=dtype,
        status=dstatus,
        limit=page_size,
        offset=(page - 1) * page_size,
    )

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedDeviceResponse(
        items=[device_to_response(d) for d in devices],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{device_id}", response_model=IoTDeviceResponse)
async def get_iot_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> IoTDeviceResponse:
    """Get IoT device by ID."""
    try:
        device_uuid = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid device ID")

    service = DeviceService(db)
    device = await service.get_device(device_uuid)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    return device_to_response(device)


@router.post("", response_model=IoTDeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_iot_device(
    data: IoTDeviceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> IoTDeviceResponse:
    """Register a new IoT device."""
    try:
        dtype = DeviceType(data.device_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid device_type: {data.device_type}",
        )

    service = DeviceService(db)
    try:
        device = await service.create_device(
            name=data.name,
            device_type=dtype,
            building_id=uuid.UUID(data.building_id),
            serial_number=data.serial_number,
            ip_address=data.ip_address,
            mac_address=data.mac_address,
            model=data.model,
            firmware_version=data.firmware_version,
            manufacturer=data.manufacturer,
            floor_plan_id=uuid.UUID(data.floor_plan_id) if data.floor_plan_id else None,
            position_x=data.position_x,
            position_y=data.position_y,
            latitude=data.latitude,
            longitude=data.longitude,
            location_name=data.location_name,
            config=data.config,
            capabilities=data.capabilities,
        )
    except DeviceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return device_to_response(device)


@router.patch("/{device_id}", response_model=IoTDeviceResponse)
async def update_iot_device(
    device_id: str,
    data: IoTDeviceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> IoTDeviceResponse:
    """Update IoT device information."""
    try:
        device_uuid = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid device ID")

    service = DeviceService(db)
    updates = data.model_dump(exclude_unset=True)

    # Convert floor_plan_id string to UUID
    if "floor_plan_id" in updates and updates["floor_plan_id"]:
        updates["floor_plan_id"] = uuid.UUID(updates["floor_plan_id"])

    try:
        device = await service.update_device(device_uuid, **updates)
    except DeviceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return device_to_response(device)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_iot_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Remove an IoT device (soft delete)."""
    try:
        device_uuid = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid device ID")

    service = DeviceService(db)
    try:
        await service.delete_device(device_uuid)
    except DeviceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{device_id}/position", response_model=IoTDeviceResponse)
async def update_device_position(
    device_id: str,
    data: PositionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> IoTDeviceResponse:
    """Update device position on floor plan."""
    try:
        device_uuid = uuid.UUID(device_id)
        fp_uuid = uuid.UUID(data.floor_plan_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format")

    service = DeviceService(db)
    try:
        device = await service.update_position(device_uuid, fp_uuid, data.position_x, data.position_y)
    except DeviceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return device_to_response(device)


@router.patch("/{device_id}/config", response_model=IoTDeviceResponse)
async def update_device_config(
    device_id: str,
    data: ConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> IoTDeviceResponse:
    """Update device detection configuration."""
    try:
        device_uuid = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid device ID")

    service = DeviceService(db)
    try:
        device = await service.update_config(device_uuid, data.config)
    except DeviceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return device_to_response(device)


@router.get("/{device_id}/status")
async def get_device_status(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Get real-time device status."""
    try:
        device_uuid = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid device ID")

    service = DeviceService(db)
    device = await service.get_device(device_uuid)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    return {
        "device_id": str(device.id),
        "status": device.status.value if hasattr(device.status, 'value') else device.status,
        "last_seen": device.last_seen.isoformat() if device.last_seen else None,
        "connection_quality": device.connection_quality,
    }
