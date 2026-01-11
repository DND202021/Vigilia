"""Resource Tracking API endpoints."""

from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.resource import (
    Resource as ResourceModel,
    ResourceStatus as ResourceStatusModel,
    ResourceType as ResourceTypeModel,
    Personnel as PersonnelModel,
    Vehicle as VehicleModel,
    Equipment as EquipmentModel,
)

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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, list]:
    """Get available resources, optionally filtered by proximity."""
    result = {
        "personnel": [],
        "vehicles": [],
        "equipment": [],
    }

    # Query available resources
    query = select(ResourceModel).where(
        ResourceModel.status == ResourceStatusModel.AVAILABLE
    )

    if resource_type:
        query = query.where(ResourceModel.resource_type == ResourceTypeModel(resource_type.value))

    db_result = await db.execute(query)
    resources = db_result.scalars().all()

    for resource in resources:
        location = None
        if resource.current_latitude and resource.current_longitude:
            location = Location(
                latitude=resource.current_latitude,
                longitude=resource.current_longitude,
                timestamp=resource.location_updated_at or resource.updated_at,
            )

        if resource.resource_type == ResourceTypeModel.PERSONNEL:
            personnel = await db.get(PersonnelModel, resource.id)
            if personnel:
                result["personnel"].append(
                    PersonnelResponse(
                        id=str(resource.id),
                        badge_number=personnel.badge_number,
                        full_name=resource.name,
                        role=personnel.rank or "Responder",
                        status=ResourceStatus(resource.status.value),
                        current_location=location,
                        assigned_vehicle_id=str(personnel.assigned_vehicle_id) if personnel.assigned_vehicle_id else None,
                        agency_id=str(resource.agency_id),
                    )
                )
        elif resource.resource_type == ResourceTypeModel.VEHICLE:
            vehicle = await db.get(VehicleModel, resource.id)
            if vehicle:
                result["vehicles"].append(
                    VehicleResponse(
                        id=str(resource.id),
                        call_sign=resource.call_sign or resource.name,
                        vehicle_type=vehicle.vehicle_type,
                        status=ResourceStatus(resource.status.value),
                        current_location=location,
                        assigned_personnel=[],
                        agency_id=str(resource.agency_id),
                    )
                )
        elif resource.resource_type == ResourceTypeModel.EQUIPMENT:
            equipment = await db.get(EquipmentModel, resource.id)
            if equipment:
                result["equipment"].append(
                    EquipmentResponse(
                        id=str(resource.id),
                        name=resource.name,
                        equipment_type=equipment.equipment_type,
                        serial_number=equipment.serial_number,
                        status=ResourceStatus(resource.status.value),
                        assigned_to=str(equipment.assigned_to_personnel_id) if equipment.assigned_to_personnel_id else None,
                        agency_id=str(resource.agency_id),
                    )
                )

    return result
