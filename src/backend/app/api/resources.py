"""Resource Tracking API endpoints."""

from datetime import datetime
from enum import Enum
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette import status as http_status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
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
    DISPATCHED = "dispatched"  # Alias for assigned (frontend compatibility)
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

    model_config = {"from_attributes": True}


class ResourceCreateRequest(BaseModel):
    """Request to create a new resource."""

    resource_type: ResourceType
    name: str
    call_sign: str | None = None
    status: ResourceStatus = ResourceStatus.AVAILABLE
    latitude: float | None = None
    longitude: float | None = None
    agency_id: str


class ResourceStatusUpdate(BaseModel):
    """Request to update resource status."""

    status: ResourceStatus
    incident_id: str | None = None


class ResourceLocationUpdate(BaseModel):
    """Request to update resource location."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class PaginatedResourceResponse(BaseModel):
    """Paginated resource response."""

    items: list[ResourceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AssignmentRecommendationResponse(BaseModel):
    """Resource assignment recommendation."""

    resource_id: str
    resource_name: str
    resource_type: str
    call_sign: str | None
    distance_km: float
    score: float
    reasons: list[str]


def resource_to_response(resource: ResourceModel) -> ResourceResponse:
    """Convert a database resource model to response."""
    return ResourceResponse(
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
        last_status_update=resource.updated_at.isoformat() if resource.updated_at else datetime.utcnow().isoformat(),
    )


@router.get("", response_model=PaginatedResourceResponse)
async def list_resources(
    resource_type: ResourceType | None = None,
    status: ResourceStatus | None = None,
    agency_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResourceResponse:
    """List all resources with optional filtering and pagination."""
    query = select(ResourceModel).where(ResourceModel.deleted_at.is_(None))

    if resource_type:
        query = query.where(ResourceModel.resource_type == ResourceTypeModel(resource_type.value))
    if status:
        query = query.where(ResourceModel.status == ResourceStatusModel(status.value))
    if agency_id:
        try:
            agency_uuid = uuid.UUID(agency_id)
            query = query.where(ResourceModel.agency_id == agency_uuid)
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Invalid agency_id format",
            )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(ResourceModel.created_at.desc())

    result = await db.execute(query)
    resources = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedResourceResponse(
        items=[resource_to_response(r) for r in resources],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/available", response_model=list[ResourceResponse])
async def get_available_resources(
    resource_type: ResourceType | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[ResourceResponse]:
    """Get available resources as a flat list."""
    query = select(ResourceModel).where(
        ResourceModel.status == ResourceStatusModel.AVAILABLE,
        ResourceModel.deleted_at.is_(None),
    )

    if resource_type:
        query = query.where(ResourceModel.resource_type == ResourceTypeModel(resource_type.value))

    db_result = await db.execute(query)
    resources = db_result.scalars().all()

    return [resource_to_response(r) for r in resources]


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ResourceResponse:
    """Get a single resource by ID."""
    try:
        resource_uuid = uuid.UUID(resource_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid resource_id format",
        )

    query = select(ResourceModel).where(
        ResourceModel.id == resource_uuid,
        ResourceModel.deleted_at.is_(None),
    )
    result = await db.execute(query)
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )

    return resource_to_response(resource)


@router.post("", response_model=ResourceResponse, status_code=http_status.HTTP_201_CREATED)
async def create_resource(
    data: ResourceCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ResourceResponse:
    """Create a new resource."""
    try:
        agency_uuid = uuid.UUID(data.agency_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid agency_id format",
        )

    resource = ResourceModel(
        resource_type=ResourceTypeModel(data.resource_type.value),
        name=data.name,
        call_sign=data.call_sign,
        status=ResourceStatusModel(data.status.value),
        current_latitude=data.latitude,
        current_longitude=data.longitude,
        agency_id=agency_uuid,
        location_updated_at=datetime.utcnow() if data.latitude and data.longitude else None,
    )

    db.add(resource)
    await db.commit()
    await db.refresh(resource)

    # Emit Socket.IO event for real-time updates
    from app.services.socketio import emit_resource_updated
    import asyncio
    asyncio.create_task(emit_resource_updated(resource_to_response(resource).model_dump()))

    return resource_to_response(resource)


@router.patch("/{resource_id}/status", response_model=ResourceResponse)
async def update_resource_status(
    resource_id: str,
    data: ResourceStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ResourceResponse:
    """Update resource status."""
    try:
        resource_uuid = uuid.UUID(resource_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid resource_id format",
        )

    query = select(ResourceModel).where(
        ResourceModel.id == resource_uuid,
        ResourceModel.deleted_at.is_(None),
    )
    result = await db.execute(query)
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )

    # Map 'dispatched' to 'assigned' for database compatibility
    status_value = data.status.value
    if status_value == "dispatched":
        status_value = "assigned"
    resource.status = ResourceStatusModel(status_value)
    await db.commit()
    await db.refresh(resource)

    # Emit Socket.IO event for real-time updates
    from app.services.socketio import emit_resource_updated
    import asyncio
    asyncio.create_task(emit_resource_updated(resource_to_response(resource).model_dump()))

    return resource_to_response(resource)


@router.patch("/{resource_id}/location", response_model=ResourceResponse)
async def update_resource_location(
    resource_id: str,
    data: ResourceLocationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ResourceResponse:
    """Update resource location."""
    try:
        resource_uuid = uuid.UUID(resource_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid resource_id format",
        )

    query = select(ResourceModel).where(
        ResourceModel.id == resource_uuid,
        ResourceModel.deleted_at.is_(None),
    )
    result = await db.execute(query)
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )

    resource.current_latitude = data.latitude
    resource.current_longitude = data.longitude
    resource.location_updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(resource)

    # Emit Socket.IO event for real-time updates
    from app.services.socketio import emit_resource_updated
    import asyncio
    asyncio.create_task(emit_resource_updated(resource_to_response(resource).model_dump()))

    return resource_to_response(resource)


@router.delete("/{resource_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Soft delete a resource."""
    try:
        resource_uuid = uuid.UUID(resource_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid resource_id format",
        )

    query = select(ResourceModel).where(
        ResourceModel.id == resource_uuid,
        ResourceModel.deleted_at.is_(None),
    )
    result = await db.execute(query)
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )

    resource.deleted_at = datetime.utcnow()
    await db.commit()


@router.get("/recommendations/{incident_id}", response_model=list[AssignmentRecommendationResponse])
async def get_assignment_recommendations(
    incident_id: str,
    max_results: int = Query(10, ge=1, le=50),
    max_distance_km: float = Query(50.0, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[AssignmentRecommendationResponse]:
    """Get resource assignment recommendations for an incident.

    Returns a ranked list of available resources based on:
    - Distance from incident location
    - Resource capabilities matching incident requirements
    - Resource availability
    """
    from app.models.incident import Incident as IncidentModel
    from app.services.assignment_engine import AssignmentEngine

    try:
        incident_uuid = uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid incident_id format",
        )

    # Get the incident
    query = select(IncidentModel).where(IncidentModel.id == incident_uuid)
    result = await db.execute(query)
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    # Get recommendations
    engine = AssignmentEngine(db)
    recommendations = await engine.get_recommendations(
        incident,
        max_results=max_results,
        max_distance_km=max_distance_km,
    )

    return [
        AssignmentRecommendationResponse(
            resource_id=r.resource_id,
            resource_name=r.resource_name,
            resource_type=r.resource_type,
            call_sign=r.call_sign,
            distance_km=r.distance_km,
            score=r.score,
            reasons=r.reasons,
        )
        for r in recommendations
    ]


@router.post("/{resource_id}/assign/{incident_id}", response_model=ResourceResponse)
async def assign_resource_to_incident(
    resource_id: str,
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ResourceResponse:
    """Assign a resource to an incident."""
    from app.models.incident import Incident as IncidentModel

    try:
        resource_uuid = uuid.UUID(resource_id)
        incident_uuid = uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )

    # Get resource
    resource_query = select(ResourceModel).where(
        ResourceModel.id == resource_uuid,
        ResourceModel.deleted_at.is_(None),
    )
    resource_result = await db.execute(resource_query)
    resource = resource_result.scalar_one_or_none()

    if not resource:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )

    if resource.status != ResourceStatusModel.AVAILABLE:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Resource is not available",
        )

    # Get incident
    incident_query = select(IncidentModel).where(IncidentModel.id == incident_uuid)
    incident_result = await db.execute(incident_query)
    incident = incident_result.scalar_one_or_none()

    if not incident:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    # Assign resource
    resource.status = ResourceStatusModel.ASSIGNED

    # Add to incident's assigned units
    if incident.assigned_units is None:
        incident.assigned_units = []
    if str(resource_uuid) not in incident.assigned_units:
        incident.assigned_units = incident.assigned_units + [str(resource_uuid)]

    await db.commit()
    await db.refresh(resource)

    # Emit Socket.IO event
    from app.services.socketio import emit_resource_updated
    import asyncio
    asyncio.create_task(emit_resource_updated(resource_to_response(resource).model_dump()))

    return resource_to_response(resource)
