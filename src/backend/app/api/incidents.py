"""Incident Management API endpoints."""

from datetime import datetime
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.incident import Incident as IncidentModel
from app.models.incident import IncidentStatus as IncidentStatusModel

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


@router.post("/", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(incident: IncidentCreate) -> IncidentResponse:
    """Create a new incident."""
    # TODO: Implement incident creation
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Incident creation not yet implemented",
    )


@router.get("/", response_model=list[IncidentResponse])
async def list_incidents(
    status: Annotated[IncidentStatus | None, Query()] = None,
    priority: Annotated[IncidentPriority | None, Query()] = None,
    category: Annotated[IncidentCategory | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[IncidentResponse]:
    """List incidents with optional filters."""
    query = select(IncidentModel)

    if status:
        query = query.where(IncidentModel.status == IncidentStatusModel(status.value))
    if priority:
        query = query.where(IncidentModel.priority == priority.value)
    if category:
        query = query.where(IncidentModel.category == category.value)

    query = query.offset(offset).limit(limit).order_by(IncidentModel.created_at.desc())

    result = await db.execute(query)
    incidents = result.scalars().all()

    return [
        IncidentResponse(
            id=str(inc.id),
            incident_number=inc.incident_number,
            category=IncidentCategory(inc.category.value),
            priority=IncidentPriority(inc.priority.value),
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
        for inc in incidents
    ]


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

    return [
        IncidentResponse(
            id=str(inc.id),
            incident_number=inc.incident_number,
            category=IncidentCategory(inc.category.value),
            priority=IncidentPriority(inc.priority.value),
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
        for inc in incidents
    ]


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(incident_id: str) -> IncidentResponse:
    """Get incident by ID."""
    # TODO: Implement incident retrieval
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Incident retrieval not yet implemented",
    )


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(incident_id: str, update: IncidentUpdate) -> IncidentResponse:
    """Update an incident."""
    # TODO: Implement incident update
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Incident update not yet implemented",
    )


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
