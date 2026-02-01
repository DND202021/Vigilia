"""IoT Device Management API endpoints for sound anomaly detection devices."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.device import DeviceType, DeviceStatus
from app.models.alert import Alert, AlertStatus
from app.services.device_service import DeviceService, DeviceError

router = APIRouter()


# ==================== Schemas ====================

class IoTDeviceCreate(BaseModel):
    """Create IoT device request."""
    name: str = Field(..., min_length=1, max_length=200)
    device_type: str = Field(..., description="microphone, camera, sensor, gateway, other")
    building_id: str = Field(..., min_length=1, description="Building UUID")
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
    icon_type: str | None = Field(None, max_length=50, description="Icon type for floor plan display")
    icon_color: str | None = Field(None, max_length=50, description="Icon color (Tailwind class or hex)")
    config: dict | None = None
    capabilities: list[str] | None = None

    @field_validator('building_id')
    @classmethod
    def validate_building_id(cls, v: str) -> str:
        """Validate building_id is a valid UUID."""
        try:
            uuid.UUID(v)
        except (ValueError, TypeError):
            raise ValueError('building_id must be a valid UUID')
        return v

    @field_validator('floor_plan_id')
    @classmethod
    def validate_floor_plan_id(cls, v: str | None) -> str | None:
        """Validate floor_plan_id is a valid UUID if provided."""
        if v is not None and v != '':
            try:
                uuid.UUID(v)
            except (ValueError, TypeError):
                raise ValueError('floor_plan_id must be a valid UUID')
        return v if v != '' else None

    @model_validator(mode='after')
    def validate_floor_plan_position(self) -> 'IoTDeviceCreate':
        """Ensure both coordinates are provided when floor_plan_id is set."""
        if self.floor_plan_id is not None:
            if self.position_x is None or self.position_y is None:
                raise ValueError(
                    'Both position_x and position_y are required when floor_plan_id is specified'
                )
        return self


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
    icon_type: str | None = Field(None, max_length=50, description="Icon type for floor plan display")
    icon_color: str | None = Field(None, max_length=50, description="Icon color (Tailwind class or hex)")
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
    icon_type: str | None = None
    icon_color: str | None = None
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


class AlertResponse(BaseModel):
    """Alert response for device alerts endpoint."""
    id: str
    alert_type: str
    severity: str
    title: str
    description: str | None = None
    status: str
    created_at: str
    resolved_at: str | None = None
    acknowledged_at: str | None = None
    confidence: float | None = None
    risk_level: str | None = None


class PaginatedAlertResponse(BaseModel):
    """Paginated alert response."""
    items: list[AlertResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DeviceStatusHistoryResponse(BaseModel):
    """Device status history entry response."""
    id: str
    device_id: str
    old_status: str | None = None
    new_status: str
    changed_at: str
    reason: str | None = None
    connection_quality: int | None = None


class PaginatedStatusHistoryResponse(BaseModel):
    """Paginated device status history response."""
    items: list[DeviceStatusHistoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== Helpers ====================

def status_history_to_response(history) -> DeviceStatusHistoryResponse:
    """Convert DeviceStatusHistory model to response."""
    return DeviceStatusHistoryResponse(
        id=str(history.id),
        device_id=str(history.device_id),
        old_status=history.old_status,
        new_status=history.new_status,
        changed_at=history.changed_at.isoformat() if history.changed_at else "",
        reason=history.reason,
        connection_quality=history.connection_quality,
    )


def alert_to_response(alert: Alert) -> AlertResponse:
    """Convert Alert model to AlertResponse."""
    # Determine resolved_at based on status
    resolved_at = None
    if alert.status == AlertStatus.RESOLVED and alert.processed_at:
        resolved_at = alert.processed_at.isoformat()

    return AlertResponse(
        id=str(alert.id),
        alert_type=alert.alert_type,
        severity=alert.severity.value if hasattr(alert.severity, 'value') else alert.severity,
        title=alert.title,
        description=alert.description,
        status=alert.status.value if hasattr(alert.status, 'value') else alert.status,
        created_at=alert.created_at.isoformat() if alert.created_at else "",
        resolved_at=resolved_at,
        acknowledged_at=alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        confidence=alert.confidence,
        risk_level=alert.risk_level,
    )


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
        icon_type=device.icon_type,
        icon_color=device.icon_color,
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
            icon_type=data.icon_type,
            icon_color=data.icon_color,
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


@router.get("/{device_id}/alerts", response_model=PaginatedAlertResponse)
async def get_device_alerts(
    device_id: str,
    status: str | None = None,  # pending, acknowledged, resolved
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedAlertResponse:
    """Get alerts generated by a specific device."""
    # Validate device_id format
    try:
        device_uuid = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid device ID")

    # Validate device exists
    service = DeviceService(db)
    device = await service.get_device(device_uuid)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    # Build query for alerts by device_id
    query = select(Alert).where(Alert.device_id == device_uuid)

    # Apply optional status filter
    if status:
        try:
            alert_status = AlertStatus(status)
            query = query.where(Alert.status == alert_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}. Valid values are: pending, acknowledged, processing, resolved, dismissed",
            )

    # Apply optional date range filters
    if start_date:
        query = query.where(Alert.created_at >= start_date)
    if end_date:
        query = query.where(Alert.created_at <= end_date)

    # Count total matching alerts
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering (most recent first)
    query = query.order_by(Alert.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
    result = await db.execute(query)
    alerts = list(result.scalars().all())

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedAlertResponse(
        items=[alert_to_response(a) for a in alerts],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{device_id}/history", response_model=PaginatedStatusHistoryResponse)
async def get_device_status_history(
    device_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedStatusHistoryResponse:
    """Get status change history for a device with pagination."""
    try:
        device_uuid = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid device ID")

    service = DeviceService(db)
    try:
        history_items, total = await service.get_status_history(
            device_id=device_uuid,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
    except DeviceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedStatusHistoryResponse(
        items=[status_history_to_response(h) for h in history_items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
