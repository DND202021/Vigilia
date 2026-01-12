"""Incident Management API endpoints."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.incident import Incident as IncidentModel
from app.models.incident import IncidentStatus as IncidentStatusModel
from app.models.incident import IncidentCategory as IncidentCategoryModel
from app.models.incident import IncidentPriority as IncidentPriorityModel
from app.services.socketio import emit_incident_created, emit_incident_updated

router = APIRouter()


class IncidentStatus(str, Enum):
    """Incident status enumeration."""

    NEW = "new"
    ASSIGNED = "assigned"
    EN_ROUTE = "en_route"
    ON_SCENE = "on_scene"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentPriority(int, Enum):
    """Incident priority levels (1=Critical, 5=Low)."""

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    MINIMAL = 5


class IncidentCategory(str, Enum):
    """Incident category enumeration."""

    FIRE = "fire"
    MEDICAL = "medical"
    POLICE = "police"
    RESCUE = "rescue"
    TRAFFIC = "traffic"
    HAZMAT = "hazmat"
    INTRUSION = "intrusion"
    OTHER = "other"


class Location(BaseModel):
    """Geographic location model."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: str | None = None
    building_info: str | None = None


class IncidentCreate(BaseModel):
    """Schema for creating a new incident."""

    category: IncidentCategory
    priority: IncidentPriority = IncidentPriority.MEDIUM
    title: str = Field(..., min_length=5, max_length=200)
    description: str | None = None
    location: Location
    source_alert_id: str | None = None


class IncidentResponse(BaseModel):
    """Schema for incident response."""

    id: str
    incident_number: str
    category: IncidentCategory
    priority: IncidentPriority
    status: IncidentStatus
    title: str
    description: str | None
    location: Location
    created_at: datetime
    updated_at: datetime
    assigned_units: list[str] = []


class IncidentUpdate(BaseModel):
    """Schema for updating an incident."""

    priority: IncidentPriority | None = None
    status: IncidentStatus | None = None
    title: str | None = None
    description: str | None = None


class PaginatedIncidentResponse(BaseModel):
    """Paginated incident response."""

    items: list[IncidentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


def incident_to_response(inc: IncidentModel) -> IncidentResponse:
    """Convert an incident model to response."""
    return IncidentResponse(
        id=str(inc.id),
        incident_number=inc.incident_number,
        category=IncidentCategory(inc.category.value),
        priority=IncidentPriority(inc.priority),
        status=IncidentStatus(inc.status.value),
        title=inc.title,
        description=inc.description,
        location=Location(
            latitude=inc.latitude,
            longitude=inc.longitude,
            address=inc.address,
            building_info=inc.building_info,
        ),
        created_at=inc.created_at,
        updated_at=inc.updated_at,
        assigned_units=inc.assigned_units or [],
    )


async def generate_incident_number(db: AsyncSession) -> str:
    """Generate a unique incident number."""
    today = datetime.now(timezone.utc)
    prefix = today.strftime("%Y%m%d")

    # Count incidents created today
    start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
    count_query = select(func.count()).select_from(IncidentModel).where(
        IncidentModel.created_at >= start_of_day
    )
    result = await db.execute(count_query)
    count = (result.scalar() or 0) + 1

    return f"INC-{prefix}-{count:04d}"


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    incident: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> IncidentResponse:
    """Create a new incident."""
    if not current_user.agency_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an agency to create incidents",
        )

    # Generate incident number
    incident_number = await generate_incident_number(db)

    # Create new incident
    new_incident = IncidentModel(
        id=uuid.uuid4(),
        incident_number=incident_number,
        category=IncidentCategoryModel(incident.category.value),
        priority=incident.priority.value,
        status=IncidentStatusModel.NEW,
        title=incident.title,
        description=incident.description,
        latitude=incident.location.latitude,
        longitude=incident.location.longitude,
        address=incident.location.address,
        building_info=incident.location.building_info,
        reported_at=datetime.now(timezone.utc),
        agency_id=current_user.agency_id,
        source_alert_id=uuid.UUID(incident.source_alert_id) if incident.source_alert_id else None,
        assigned_units=[],
        timeline_events=[{
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "created",
            "user_id": str(current_user.id),
            "details": f"Incident created by {current_user.full_name or current_user.email}",
        }],
    )

    db.add(new_incident)
    await db.commit()
    await db.refresh(new_incident)

    response = incident_to_response(new_incident)

    # Emit real-time event
    await emit_incident_created(response.model_dump(mode="json"))

    return response


@router.get("", response_model=PaginatedIncidentResponse)
async def list_incidents(
    status: Annotated[IncidentStatus | None, Query()] = None,
    priority: Annotated[IncidentPriority | None, Query()] = None,
    incident_type: Annotated[IncidentCategory | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedIncidentResponse:
    """List incidents with optional filters and pagination."""
    query = select(IncidentModel)

    if status:
        query = query.where(IncidentModel.status == IncidentStatusModel(status.value))
    if priority:
        query = query.where(IncidentModel.priority == priority.value)
    if incident_type:
        query = query.where(IncidentModel.category == incident_type.value)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(IncidentModel.created_at.desc())

    result = await db.execute(query)
    incidents = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedIncidentResponse(
        items=[incident_to_response(inc) for inc in incidents],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/active", response_model=list[IncidentResponse])
async def get_active_incidents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[IncidentResponse]:
    """Get all active incidents (not resolved or closed)."""
    active_statuses = [
        IncidentStatusModel.NEW,
        IncidentStatusModel.ASSIGNED,
        IncidentStatusModel.EN_ROUTE,
        IncidentStatusModel.ON_SCENE,
    ]

    query = select(IncidentModel).where(
        IncidentModel.status.in_(active_statuses)
    ).order_by(IncidentModel.priority, IncidentModel.created_at.desc())

    result = await db.execute(query)
    incidents = result.scalars().all()

    return [incident_to_response(inc) for inc in incidents]


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> IncidentResponse:
    """Get incident by ID."""
    try:
        incident_uuid = uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid incident ID format",
        )

    query = select(IncidentModel).where(IncidentModel.id == incident_uuid)
    result = await db.execute(query)
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    return incident_to_response(incident)


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: str,
    update: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> IncidentResponse:
    """Update an incident."""
    try:
        incident_uuid = uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid incident ID format",
        )

    query = select(IncidentModel).where(IncidentModel.id == incident_uuid)
    result = await db.execute(query)
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    # Track changes for timeline
    changes = []

    if update.priority is not None and update.priority.value != incident.priority:
        changes.append(f"priority changed from {incident.priority} to {update.priority.value}")
        incident.priority = update.priority.value

    if update.status is not None and update.status.value != incident.status.value:
        changes.append(f"status changed from {incident.status.value} to {update.status.value}")
        incident.status = IncidentStatusModel(update.status.value)

        # Update timeline timestamps
        now = datetime.now(timezone.utc)
        if update.status == IncidentStatus.ASSIGNED and not incident.dispatched_at:
            incident.dispatched_at = now
        elif update.status == IncidentStatus.ON_SCENE and not incident.arrived_at:
            incident.arrived_at = now
        elif update.status == IncidentStatus.RESOLVED and not incident.resolved_at:
            incident.resolved_at = now
        elif update.status == IncidentStatus.CLOSED and not incident.closed_at:
            incident.closed_at = now

    if update.title is not None and update.title != incident.title:
        changes.append(f"title updated")
        incident.title = update.title

    if update.description is not None and update.description != incident.description:
        changes.append(f"description updated")
        incident.description = update.description

    # Add timeline event if changes were made
    if changes:
        timeline = incident.timeline_events or []
        timeline.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "updated",
            "user_id": str(current_user.id),
            "details": "; ".join(changes),
        })
        incident.timeline_events = timeline

    await db.commit()
    await db.refresh(incident)

    response = incident_to_response(incident)

    # Emit real-time event
    await emit_incident_updated(response.model_dump(mode="json"))

    return response


@router.post("/{incident_id}/assign")
async def assign_unit(incident_id: str, unit_id: str) -> dict[str, str]:
    """Assign a unit to an incident."""
    # TODO: Implement unit assignment
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Unit assignment not yet implemented",
    )


@router.post("/{incident_id}/escalate")
async def escalate_incident(incident_id: str, reason: str) -> dict[str, str]:
    """Escalate an incident."""
    # TODO: Implement escalation
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Escalation not yet implemented",
    )


@router.get("/{incident_id}/timeline")
async def get_incident_timeline(incident_id: str) -> list[dict]:
    """Get complete timeline of incident events."""
    # TODO: Implement timeline retrieval
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Timeline retrieval not yet implemented",
    )
