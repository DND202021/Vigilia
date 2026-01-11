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


class ResourceResponse(BaseModel):
    """Generic resource response matching frontend Resource type."""

    id: str
    resource_type: ResourceType
    name: str
    call_sign: str | None = None
    status: ResourceStatus
    latitude: float | None = None
    longitude: float | None = None
    capabilities: list[str] = []
    agency_id: str
    current_incident_id: str | None = None
    last_status_update: str


class PaginatedResourceResponse(BaseModel):
    """Paginated resource response."""

    items: list[ResourceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("/", response_model=PaginatedResourceResponse)
async def list_resources(
    resource_type: ResourceType | None = None,
    status: ResourceStatus | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResourceResponse:
    """List all resources with pagination."""
    from sqlalchemy import func

    query = select(ResourceModel)

    if resource_type:
        query = query.where(ResourceModel.resource_type == ResourceTypeModel(resource_type.value))
    if status:
        query = query.where(ResourceModel.status == ResourceStatusModel(status.value))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    resources = result.scalars().all()

    items = [
        ResourceResponse(
            id=str(r.id),
            resource_type=ResourceType(r.resource_type.value),
            name=r.name,
            call_sign=r.call_sign,
            status=ResourceStatus(r.status.value),
            latitude=r.current_latitude,
            longitude=r.current_longitude,
            capabilities=[],
            agency_id=str(r.agency_id),
            current_incident_id=None,
            last_status_update=r.updated_at.isoformat(),
        )
        for r in resources
    ]

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedResourceResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


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


@router.get("/available", response_model=list[ResourceResponse])
async def get_available_resources(
    resource_type: ResourceType | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[ResourceResponse]:
    """Get available resources as a flat list."""
    # Query available resources
    query = select(ResourceModel).where(
        ResourceModel.status == ResourceStatusModel.AVAILABLE
    )

    if resource_type:
        query = query.where(ResourceModel.resource_type == ResourceTypeModel(resource_type.value))

    db_result = await db.execute(query)
    resources = db_result.scalars().all()

    result = []
    for resource in resources:
        result.append(
            ResourceResponse(
                id=str(resource.id),
                resource_type=ResourceType(resource.resource_type.value),
                name=resource.name,
                call_sign=resource.call_sign,
                status=ResourceStatus(resource.status.value),
                latitude=resource.current_latitude,
                longitude=resource.current_longitude,
                capabilities=[],
                agency_id=str(resource.agency_id),
                current_incident_id=None,
                last_status_update=resource.updated_at.isoformat(),
            )
        )

    return result
