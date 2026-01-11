"""Resource Tracking API endpoints."""

from datetime import datetime
from enum import Enum

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter()


class ResourceStatus(str, Enum):
    """Resource availability status."""

    AVAILABLE = "available"
    ASSIGNED = "assigned"
    EN_ROUTE = "en_route"
    ON_SCENE = "on_scene"
    OFF_DUTY = "off_duty"
    OUT_OF_SERVICE = "out_of_service"


class ResourceType(str, Enum):
    """Type of resource."""

    PERSONNEL = "personnel"
    VEHICLE = "vehicle"
    EQUIPMENT = "equipment"


class Location(BaseModel):
    """Geographic location model."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    timestamp: datetime


class PersonnelResponse(BaseModel):
    """Personnel resource response."""

    id: str
    badge_number: str
    full_name: str
    role: str
    status: ResourceStatus
    current_location: Location | None
    assigned_vehicle_id: str | None
    agency_id: str


class VehicleResponse(BaseModel):
    """Vehicle resource response."""

    id: str
    call_sign: str
    vehicle_type: str
    status: ResourceStatus
    current_location: Location | None
    assigned_personnel: list[str] = []
    agency_id: str


class EquipmentResponse(BaseModel):
    """Equipment resource response."""

    id: str
    name: str
    equipment_type: str
    serial_number: str | None
    status: ResourceStatus
    assigned_to: str | None
    agency_id: str


@router.get("/personnel", response_model=list[PersonnelResponse])
async def list_personnel(
    status: ResourceStatus | None = None,
    agency_id: str | None = None,
) -> list[PersonnelResponse]:
    """List personnel resources."""
    # TODO: Implement personnel listing
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Personnel listing not yet implemented",
    )


@router.get("/vehicles", response_model=list[VehicleResponse])
async def list_vehicles(
    status: ResourceStatus | None = None,
    agency_id: str | None = None,
) -> list[VehicleResponse]:
    """List vehicle resources."""
    # TODO: Implement vehicle listing
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Vehicle listing not yet implemented",
    )


@router.get("/equipment", response_model=list[EquipmentResponse])
async def list_equipment(
    status: ResourceStatus | None = None,
    agency_id: str | None = None,
) -> list[EquipmentResponse]:
    """List equipment resources."""
    # TODO: Implement equipment listing
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Equipment listing not yet implemented",
    )


@router.patch("/{resource_type}/{resource_id}/status")
async def update_resource_status(
    resource_type: ResourceType,
    resource_id: str,
    status: ResourceStatus,
) -> dict[str, str]:
    """Update resource status."""
    # TODO: Implement status update
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Status update not yet implemented",
    )


@router.get("/available")
async def get_available_resources(
    resource_type: ResourceType | None = None,
    near_latitude: float | None = None,
    near_longitude: float | None = None,
    radius_km: float = 10.0,
) -> dict[str, list]:
    """Get available resources, optionally filtered by proximity."""
    # TODO: Implement available resources query
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Available resources query not yet implemented",
    )
