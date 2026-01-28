"""Emergency Planning API endpoints for Sprint 10.

Provides CRUD operations for emergency procedures, evacuation routes,
and emergency checkpoints for building emergency response planning.
"""

from datetime import datetime
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette import status as http_status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.building import Building as BuildingModel, FloorPlan as FloorPlanModel
from app.models.emergency_procedure import EmergencyProcedure, ProcedureType
from app.models.evacuation_route import EvacuationRoute, RouteType
from app.models.emergency_checkpoint import EmergencyCheckpoint, CheckpointType

router = APIRouter()


# ==================== Pydantic Schemas ====================

# --- Emergency Procedure Schemas ---

class ProcedureStepSchema(BaseModel):
    """Schema for a procedure step."""
    order: int
    title: str
    description: str | None = None
    responsible_role: str | None = None
    duration_minutes: int | None = None


class ProcedureContactSchema(BaseModel):
    """Schema for a procedure contact."""
    name: str
    role: str | None = None
    phone: str | None = None
    email: str | None = None


class ProcedureCreateRequest(BaseModel):
    """Request to create an emergency procedure."""
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    procedure_type: str = Field(..., description="evacuation, fire, medical, hazmat, lockdown, active_shooter, weather, utility_failure")
    priority: int = Field(3, ge=1, le=5, description="1=highest priority, 5=lowest")
    steps: list[dict] | None = None
    contacts: list[dict] | None = None
    equipment_needed: list[str] | None = None
    estimated_duration_minutes: int | None = None
    is_active: bool = True


class ProcedureUpdateRequest(BaseModel):
    """Request to update an emergency procedure."""
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    procedure_type: str | None = None
    priority: int | None = Field(None, ge=1, le=5)
    steps: list[dict] | None = None
    contacts: list[dict] | None = None
    equipment_needed: list[str] | None = None
    estimated_duration_minutes: int | None = None
    is_active: bool | None = None


class ProcedureResponse(BaseModel):
    """Emergency procedure response model."""
    id: str
    building_id: str
    name: str
    description: str | None = None
    procedure_type: str
    priority: int
    steps: list[dict] | None = None
    contacts: list[dict] | None = None
    equipment_needed: list[str] | None = None
    estimated_duration_minutes: int | None = None
    is_active: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class PaginatedProcedureResponse(BaseModel):
    """Paginated procedure response."""
    items: list[ProcedureResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# --- Evacuation Route Schemas ---

class WaypointSchema(BaseModel):
    """Schema for a route waypoint."""
    order: int
    x: float = Field(..., ge=0, le=100, description="X position as percentage")
    y: float = Field(..., ge=0, le=100, description="Y position as percentage")
    floor_plan_id: str | None = None
    label: str | None = None


class RouteCreateRequest(BaseModel):
    """Request to create an evacuation route."""
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    floor_plan_id: str | None = None
    route_type: str = Field("primary", description="primary, secondary, accessible, emergency_vehicle")
    waypoints: list[dict] | None = None
    color: str = Field("#ff0000", max_length=20)
    line_width: int = Field(3, ge=1, le=10)
    is_active: bool = True
    capacity: int | None = None
    estimated_time_seconds: int | None = None
    accessibility_features: list[str] | None = None


class RouteUpdateRequest(BaseModel):
    """Request to update an evacuation route."""
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    floor_plan_id: str | None = None
    route_type: str | None = None
    waypoints: list[dict] | None = None
    color: str | None = Field(None, max_length=20)
    line_width: int | None = Field(None, ge=1, le=10)
    is_active: bool | None = None
    capacity: int | None = None
    estimated_time_seconds: int | None = None
    accessibility_features: list[str] | None = None


class RouteResponse(BaseModel):
    """Evacuation route response model."""
    id: str
    building_id: str
    floor_plan_id: str | None = None
    name: str
    description: str | None = None
    route_type: str
    waypoints: list[dict] | None = None
    color: str
    line_width: int
    is_active: bool
    capacity: int | None = None
    estimated_time_seconds: int | None = None
    accessibility_features: list[str] | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class PaginatedRouteResponse(BaseModel):
    """Paginated route response."""
    items: list[RouteResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# --- Emergency Checkpoint Schemas ---

class CheckpointEquipmentSchema(BaseModel):
    """Schema for checkpoint equipment."""
    name: str
    quantity: int = 1
    location: str | None = None


class CheckpointContactSchema(BaseModel):
    """Schema for checkpoint contact info."""
    phone: str | None = None
    email: str | None = None
    radio_channel: str | None = None


class CheckpointCreateRequest(BaseModel):
    """Request to create an emergency checkpoint."""
    name: str = Field(..., min_length=1, max_length=200)
    floor_plan_id: str | None = None
    checkpoint_type: str = Field(..., description="assembly_point, muster_station, first_aid, command_post, triage_area, decontamination, staging_area, media_point")
    position_x: float = Field(..., ge=0, le=100, description="X position as percentage")
    position_y: float = Field(..., ge=0, le=100, description="Y position as percentage")
    capacity: int | None = None
    equipment: list[dict] | None = None
    responsible_person: str | None = None
    contact_info: dict | None = None
    instructions: str | None = None
    is_active: bool = True


class CheckpointUpdateRequest(BaseModel):
    """Request to update an emergency checkpoint."""
    name: str | None = Field(None, min_length=1, max_length=200)
    floor_plan_id: str | None = None
    checkpoint_type: str | None = None
    position_x: float | None = Field(None, ge=0, le=100)
    position_y: float | None = Field(None, ge=0, le=100)
    capacity: int | None = None
    equipment: list[dict] | None = None
    responsible_person: str | None = None
    contact_info: dict | None = None
    instructions: str | None = None
    is_active: bool | None = None


class CheckpointResponse(BaseModel):
    """Emergency checkpoint response model."""
    id: str
    building_id: str
    floor_plan_id: str | None = None
    name: str
    checkpoint_type: str
    position_x: float
    position_y: float
    capacity: int | None = None
    equipment: list[dict] | None = None
    responsible_person: str | None = None
    contact_info: dict | None = None
    instructions: str | None = None
    is_active: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class PaginatedCheckpointResponse(BaseModel):
    """Paginated checkpoint response."""
    items: list[CheckpointResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# --- Combined Emergency Plan Schemas ---

class EmergencyPlanResponse(BaseModel):
    """Combined emergency plan response."""
    building_id: str
    building_name: str
    procedures: list[ProcedureResponse]
    routes: list[RouteResponse]
    checkpoints: list[CheckpointResponse]
    total_procedures: int
    total_routes: int
    total_checkpoints: int


class EmergencyPlanExportResponse(BaseModel):
    """Emergency plan export response with metadata."""
    building_id: str
    building_name: str
    building_address: str
    exported_at: str
    exported_by: str
    procedures: list[ProcedureResponse]
    routes: list[RouteResponse]
    checkpoints: list[CheckpointResponse]
    metadata: dict


# ==================== Helper Functions ====================

def procedure_to_response(procedure: EmergencyProcedure) -> ProcedureResponse:
    """Convert database procedure model to response."""
    return ProcedureResponse(
        id=str(procedure.id),
        building_id=str(procedure.building_id),
        name=procedure.name,
        description=procedure.description,
        procedure_type=procedure.procedure_type.value,
        priority=procedure.priority,
        steps=procedure.steps,
        contacts=procedure.contacts,
        equipment_needed=procedure.equipment_needed,
        estimated_duration_minutes=procedure.estimated_duration_minutes,
        is_active=procedure.is_active,
        created_at=procedure.created_at.isoformat() if procedure.created_at else datetime.utcnow().isoformat(),
        updated_at=procedure.updated_at.isoformat() if procedure.updated_at else datetime.utcnow().isoformat(),
    )


def route_to_response(route: EvacuationRoute) -> RouteResponse:
    """Convert database route model to response."""
    return RouteResponse(
        id=str(route.id),
        building_id=str(route.building_id),
        floor_plan_id=str(route.floor_plan_id) if route.floor_plan_id else None,
        name=route.name,
        description=route.description,
        route_type=route.route_type,
        waypoints=route.waypoints,
        color=route.color,
        line_width=route.line_width,
        is_active=route.is_active,
        capacity=route.capacity,
        estimated_time_seconds=route.estimated_time_seconds,
        accessibility_features=route.accessibility_features,
        created_at=route.created_at.isoformat() if route.created_at else datetime.utcnow().isoformat(),
        updated_at=route.updated_at.isoformat() if route.updated_at else datetime.utcnow().isoformat(),
    )


def checkpoint_to_response(checkpoint: EmergencyCheckpoint) -> CheckpointResponse:
    """Convert database checkpoint model to response."""
    return CheckpointResponse(
        id=str(checkpoint.id),
        building_id=str(checkpoint.building_id),
        floor_plan_id=str(checkpoint.floor_plan_id) if checkpoint.floor_plan_id else None,
        name=checkpoint.name,
        checkpoint_type=checkpoint.checkpoint_type.value,
        position_x=checkpoint.position_x,
        position_y=checkpoint.position_y,
        capacity=checkpoint.capacity,
        equipment=checkpoint.equipment,
        responsible_person=checkpoint.responsible_person,
        contact_info=checkpoint.contact_info,
        instructions=checkpoint.instructions,
        is_active=checkpoint.is_active,
        created_at=checkpoint.created_at.isoformat() if checkpoint.created_at else datetime.utcnow().isoformat(),
        updated_at=checkpoint.updated_at.isoformat() if checkpoint.updated_at else datetime.utcnow().isoformat(),
    )


async def get_building_or_404(db: AsyncSession, building_id: str) -> BuildingModel:
    """Get building by ID or raise 404."""
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    result = await db.execute(
        select(BuildingModel).where(BuildingModel.id == building_uuid)
    )
    building = result.scalar_one_or_none()

    if not building:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Building not found",
        )

    return building


async def validate_floor_plan(db: AsyncSession, building_id: uuid.UUID, floor_plan_id: str | None) -> uuid.UUID | None:
    """Validate floor plan belongs to building, return UUID or None."""
    if not floor_plan_id:
        return None

    try:
        fp_uuid = uuid.UUID(floor_plan_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid floor_plan_id format",
        )

    result = await db.execute(
        select(FloorPlanModel).where(
            and_(
                FloorPlanModel.id == fp_uuid,
                FloorPlanModel.building_id == building_id,
            )
        )
    )
    floor_plan = result.scalar_one_or_none()

    if not floor_plan:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Floor plan not found or does not belong to this building",
        )

    return fp_uuid


# ==================== Emergency Procedure Endpoints ====================

@router.get("/buildings/{building_id}/procedures", response_model=PaginatedProcedureResponse)
async def list_procedures(
    building_id: str,
    procedure_type: str | None = Query(None, description="Filter by procedure type"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedProcedureResponse:
    """List emergency procedures for a building."""
    building = await get_building_or_404(db, building_id)

    # Build query
    query = select(EmergencyProcedure).where(
        and_(
            EmergencyProcedure.building_id == building.id,
            EmergencyProcedure.deleted_at.is_(None),
        )
    )

    # Apply filters
    if procedure_type:
        try:
            pt = ProcedureType(procedure_type)
            query = query.where(EmergencyProcedure.procedure_type == pt)
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid procedure_type: {procedure_type}",
            )

    if is_active is not None:
        query = query.where(EmergencyProcedure.is_active == is_active)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.order_by(EmergencyProcedure.priority, EmergencyProcedure.name)
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    procedures = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedProcedureResponse(
        items=[procedure_to_response(p) for p in procedures],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/procedures/{procedure_id}", response_model=ProcedureResponse)
async def get_procedure(
    procedure_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ProcedureResponse:
    """Get a single emergency procedure by ID."""
    try:
        proc_uuid = uuid.UUID(procedure_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid procedure_id format",
        )

    result = await db.execute(
        select(EmergencyProcedure).where(
            and_(
                EmergencyProcedure.id == proc_uuid,
                EmergencyProcedure.deleted_at.is_(None),
            )
        )
    )
    procedure = result.scalar_one_or_none()

    if not procedure:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Procedure not found",
        )

    return procedure_to_response(procedure)


@router.post("/buildings/{building_id}/procedures", response_model=ProcedureResponse, status_code=http_status.HTTP_201_CREATED)
async def create_procedure(
    building_id: str,
    data: ProcedureCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ProcedureResponse:
    """Create a new emergency procedure for a building."""
    building = await get_building_or_404(db, building_id)

    # Parse procedure type
    try:
        procedure_type = ProcedureType(data.procedure_type)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid procedure_type: {data.procedure_type}",
        )

    procedure = EmergencyProcedure(
        building_id=building.id,
        name=data.name,
        description=data.description,
        procedure_type=procedure_type,
        priority=data.priority,
        steps=data.steps,
        contacts=data.contacts,
        equipment_needed=data.equipment_needed,
        estimated_duration_minutes=data.estimated_duration_minutes,
        is_active=data.is_active,
    )

    db.add(procedure)
    await db.commit()
    await db.refresh(procedure)

    return procedure_to_response(procedure)


@router.patch("/procedures/{procedure_id}", response_model=ProcedureResponse)
async def update_procedure(
    procedure_id: str,
    data: ProcedureUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ProcedureResponse:
    """Update an emergency procedure."""
    try:
        proc_uuid = uuid.UUID(procedure_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid procedure_id format",
        )

    result = await db.execute(
        select(EmergencyProcedure).where(
            and_(
                EmergencyProcedure.id == proc_uuid,
                EmergencyProcedure.deleted_at.is_(None),
            )
        )
    )
    procedure = result.scalar_one_or_none()

    if not procedure:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Procedure not found",
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "procedure_type" and value is not None:
            try:
                value = ProcedureType(value)
            except ValueError:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid procedure_type: {value}",
                )
        setattr(procedure, field, value)

    procedure.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(procedure)

    return procedure_to_response(procedure)


@router.delete("/procedures/{procedure_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_procedure(
    procedure_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Soft delete an emergency procedure."""
    try:
        proc_uuid = uuid.UUID(procedure_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid procedure_id format",
        )

    result = await db.execute(
        select(EmergencyProcedure).where(
            and_(
                EmergencyProcedure.id == proc_uuid,
                EmergencyProcedure.deleted_at.is_(None),
            )
        )
    )
    procedure = result.scalar_one_or_none()

    if not procedure:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Procedure not found",
        )

    procedure.deleted_at = datetime.utcnow()
    await db.commit()


# ==================== Evacuation Route Endpoints ====================

@router.get("/buildings/{building_id}/routes", response_model=PaginatedRouteResponse)
async def list_routes(
    building_id: str,
    floor_plan_id: str | None = Query(None, description="Filter by floor plan"),
    route_type: str | None = Query(None, description="Filter by route type"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedRouteResponse:
    """List evacuation routes for a building."""
    building = await get_building_or_404(db, building_id)

    # Build query
    query = select(EvacuationRoute).where(EvacuationRoute.building_id == building.id)

    # Apply filters
    if floor_plan_id:
        fp_uuid = await validate_floor_plan(db, building.id, floor_plan_id)
        query = query.where(EvacuationRoute.floor_plan_id == fp_uuid)

    if route_type:
        # Validate route type
        valid_types = [rt.value for rt in RouteType]
        if route_type not in valid_types:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid route_type: {route_type}. Must be one of: {valid_types}",
            )
        query = query.where(EvacuationRoute.route_type == route_type)

    if is_active is not None:
        query = query.where(EvacuationRoute.is_active == is_active)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.order_by(EvacuationRoute.route_type, EvacuationRoute.name)
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    routes = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedRouteResponse(
        items=[route_to_response(r) for r in routes],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/routes/{route_id}", response_model=RouteResponse)
async def get_route(
    route_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RouteResponse:
    """Get a single evacuation route by ID."""
    try:
        route_uuid = uuid.UUID(route_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid route_id format",
        )

    result = await db.execute(
        select(EvacuationRoute).where(EvacuationRoute.id == route_uuid)
    )
    route = result.scalar_one_or_none()

    if not route:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Route not found",
        )

    return route_to_response(route)


@router.post("/buildings/{building_id}/routes", response_model=RouteResponse, status_code=http_status.HTTP_201_CREATED)
async def create_route(
    building_id: str,
    data: RouteCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RouteResponse:
    """Create a new evacuation route for a building."""
    building = await get_building_or_404(db, building_id)

    # Validate floor plan if provided
    floor_plan_uuid = await validate_floor_plan(db, building.id, data.floor_plan_id)

    # Validate route type
    valid_types = [rt.value for rt in RouteType]
    if data.route_type not in valid_types:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid route_type: {data.route_type}. Must be one of: {valid_types}",
        )

    route = EvacuationRoute(
        building_id=building.id,
        floor_plan_id=floor_plan_uuid,
        name=data.name,
        description=data.description,
        route_type=data.route_type,
        waypoints=data.waypoints,
        color=data.color,
        line_width=data.line_width,
        is_active=data.is_active,
        capacity=data.capacity,
        estimated_time_seconds=data.estimated_time_seconds,
        accessibility_features=data.accessibility_features,
    )

    db.add(route)
    await db.commit()
    await db.refresh(route)

    return route_to_response(route)


@router.patch("/routes/{route_id}", response_model=RouteResponse)
async def update_route(
    route_id: str,
    data: RouteUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RouteResponse:
    """Update an evacuation route."""
    try:
        route_uuid = uuid.UUID(route_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid route_id format",
        )

    result = await db.execute(
        select(EvacuationRoute).where(EvacuationRoute.id == route_uuid)
    )
    route = result.scalar_one_or_none()

    if not route:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Route not found",
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "floor_plan_id" and value is not None:
            value = await validate_floor_plan(db, route.building_id, value)
        elif field == "route_type" and value is not None:
            valid_types = [rt.value for rt in RouteType]
            if value not in valid_types:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid route_type: {value}. Must be one of: {valid_types}",
                )
        setattr(route, field, value)

    route.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(route)

    return route_to_response(route)


@router.delete("/routes/{route_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_route(
    route_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Soft delete an evacuation route (set is_active=False)."""
    try:
        route_uuid = uuid.UUID(route_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid route_id format",
        )

    result = await db.execute(
        select(EvacuationRoute).where(EvacuationRoute.id == route_uuid)
    )
    route = result.scalar_one_or_none()

    if not route:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Route not found",
        )

    # Soft delete by setting is_active to False
    route.is_active = False
    route.updated_at = datetime.utcnow()
    await db.commit()


# ==================== Emergency Checkpoint Endpoints ====================

@router.get("/buildings/{building_id}/checkpoints", response_model=PaginatedCheckpointResponse)
async def list_checkpoints(
    building_id: str,
    floor_plan_id: str | None = Query(None, description="Filter by floor plan"),
    checkpoint_type: str | None = Query(None, description="Filter by checkpoint type"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedCheckpointResponse:
    """List emergency checkpoints for a building."""
    building = await get_building_or_404(db, building_id)

    # Build query
    query = select(EmergencyCheckpoint).where(EmergencyCheckpoint.building_id == building.id)

    # Apply filters
    if floor_plan_id:
        fp_uuid = await validate_floor_plan(db, building.id, floor_plan_id)
        query = query.where(EmergencyCheckpoint.floor_plan_id == fp_uuid)

    if checkpoint_type:
        try:
            ct = CheckpointType(checkpoint_type)
            query = query.where(EmergencyCheckpoint.checkpoint_type == ct)
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid checkpoint_type: {checkpoint_type}",
            )

    if is_active is not None:
        query = query.where(EmergencyCheckpoint.is_active == is_active)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.order_by(EmergencyCheckpoint.checkpoint_type, EmergencyCheckpoint.name)
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    checkpoints = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedCheckpointResponse(
        items=[checkpoint_to_response(c) for c in checkpoints],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/checkpoints/{checkpoint_id}", response_model=CheckpointResponse)
async def get_checkpoint(
    checkpoint_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CheckpointResponse:
    """Get a single emergency checkpoint by ID."""
    try:
        checkpoint_uuid = uuid.UUID(checkpoint_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid checkpoint_id format",
        )

    result = await db.execute(
        select(EmergencyCheckpoint).where(EmergencyCheckpoint.id == checkpoint_uuid)
    )
    checkpoint = result.scalar_one_or_none()

    if not checkpoint:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Checkpoint not found",
        )

    return checkpoint_to_response(checkpoint)


@router.post("/buildings/{building_id}/checkpoints", response_model=CheckpointResponse, status_code=http_status.HTTP_201_CREATED)
async def create_checkpoint(
    building_id: str,
    data: CheckpointCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CheckpointResponse:
    """Create a new emergency checkpoint for a building."""
    building = await get_building_or_404(db, building_id)

    # Validate floor plan if provided
    floor_plan_uuid = await validate_floor_plan(db, building.id, data.floor_plan_id)

    # Parse checkpoint type
    try:
        checkpoint_type = CheckpointType(data.checkpoint_type)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid checkpoint_type: {data.checkpoint_type}",
        )

    checkpoint = EmergencyCheckpoint(
        building_id=building.id,
        floor_plan_id=floor_plan_uuid,
        name=data.name,
        checkpoint_type=checkpoint_type,
        position_x=data.position_x,
        position_y=data.position_y,
        capacity=data.capacity,
        equipment=data.equipment,
        responsible_person=data.responsible_person,
        contact_info=data.contact_info,
        instructions=data.instructions,
        is_active=data.is_active,
    )

    db.add(checkpoint)
    await db.commit()
    await db.refresh(checkpoint)

    return checkpoint_to_response(checkpoint)


@router.patch("/checkpoints/{checkpoint_id}", response_model=CheckpointResponse)
async def update_checkpoint(
    checkpoint_id: str,
    data: CheckpointUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CheckpointResponse:
    """Update an emergency checkpoint."""
    try:
        checkpoint_uuid = uuid.UUID(checkpoint_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid checkpoint_id format",
        )

    result = await db.execute(
        select(EmergencyCheckpoint).where(EmergencyCheckpoint.id == checkpoint_uuid)
    )
    checkpoint = result.scalar_one_or_none()

    if not checkpoint:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Checkpoint not found",
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "floor_plan_id" and value is not None:
            value = await validate_floor_plan(db, checkpoint.building_id, value)
        elif field == "checkpoint_type" and value is not None:
            try:
                value = CheckpointType(value)
            except ValueError:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid checkpoint_type: {value}",
                )
        setattr(checkpoint, field, value)

    checkpoint.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(checkpoint)

    return checkpoint_to_response(checkpoint)


@router.delete("/checkpoints/{checkpoint_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_checkpoint(
    checkpoint_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Soft delete an emergency checkpoint (set is_active=False)."""
    try:
        checkpoint_uuid = uuid.UUID(checkpoint_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid checkpoint_id format",
        )

    result = await db.execute(
        select(EmergencyCheckpoint).where(EmergencyCheckpoint.id == checkpoint_uuid)
    )
    checkpoint = result.scalar_one_or_none()

    if not checkpoint:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Checkpoint not found",
        )

    # Soft delete by setting is_active to False
    checkpoint.is_active = False
    checkpoint.updated_at = datetime.utcnow()
    await db.commit()


# ==================== Combined Emergency Plan Endpoints ====================

@router.get("/buildings/{building_id}/emergency-plan", response_model=EmergencyPlanResponse)
async def get_emergency_plan(
    building_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> EmergencyPlanResponse:
    """Get the full emergency plan for a building (procedures, routes, checkpoints)."""
    building = await get_building_or_404(db, building_id)

    # Fetch all active procedures
    procedures_result = await db.execute(
        select(EmergencyProcedure).where(
            and_(
                EmergencyProcedure.building_id == building.id,
                EmergencyProcedure.deleted_at.is_(None),
                EmergencyProcedure.is_active == True,
            )
        ).order_by(EmergencyProcedure.priority, EmergencyProcedure.name)
    )
    procedures = procedures_result.scalars().all()

    # Fetch all active routes
    routes_result = await db.execute(
        select(EvacuationRoute).where(
            and_(
                EvacuationRoute.building_id == building.id,
                EvacuationRoute.is_active == True,
            )
        ).order_by(EvacuationRoute.route_type, EvacuationRoute.name)
    )
    routes = routes_result.scalars().all()

    # Fetch all active checkpoints
    checkpoints_result = await db.execute(
        select(EmergencyCheckpoint).where(
            and_(
                EmergencyCheckpoint.building_id == building.id,
                EmergencyCheckpoint.is_active == True,
            )
        ).order_by(EmergencyCheckpoint.checkpoint_type, EmergencyCheckpoint.name)
    )
    checkpoints = checkpoints_result.scalars().all()

    return EmergencyPlanResponse(
        building_id=str(building.id),
        building_name=building.name,
        procedures=[procedure_to_response(p) for p in procedures],
        routes=[route_to_response(r) for r in routes],
        checkpoints=[checkpoint_to_response(c) for c in checkpoints],
        total_procedures=len(procedures),
        total_routes=len(routes),
        total_checkpoints=len(checkpoints),
    )


@router.get("/buildings/{building_id}/emergency-plan/export", response_model=EmergencyPlanExportResponse)
async def export_emergency_plan(
    building_id: str,
    include_inactive: bool = Query(False, description="Include inactive items"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> EmergencyPlanExportResponse:
    """Export the emergency plan as JSON with metadata."""
    building = await get_building_or_404(db, building_id)

    # Build base queries
    procedures_query = select(EmergencyProcedure).where(
        and_(
            EmergencyProcedure.building_id == building.id,
            EmergencyProcedure.deleted_at.is_(None),
        )
    )

    routes_query = select(EvacuationRoute).where(
        EvacuationRoute.building_id == building.id
    )

    checkpoints_query = select(EmergencyCheckpoint).where(
        EmergencyCheckpoint.building_id == building.id
    )

    # Filter by active status unless include_inactive
    if not include_inactive:
        procedures_query = procedures_query.where(EmergencyProcedure.is_active == True)
        routes_query = routes_query.where(EvacuationRoute.is_active == True)
        checkpoints_query = checkpoints_query.where(EmergencyCheckpoint.is_active == True)

    # Execute queries
    procedures_result = await db.execute(
        procedures_query.order_by(EmergencyProcedure.priority, EmergencyProcedure.name)
    )
    procedures = procedures_result.scalars().all()

    routes_result = await db.execute(
        routes_query.order_by(EvacuationRoute.route_type, EvacuationRoute.name)
    )
    routes = routes_result.scalars().all()

    checkpoints_result = await db.execute(
        checkpoints_query.order_by(EmergencyCheckpoint.checkpoint_type, EmergencyCheckpoint.name)
    )
    checkpoints = checkpoints_result.scalars().all()

    # Build metadata
    metadata = {
        "version": "1.0",
        "format": "ERIOP Emergency Plan Export",
        "include_inactive": include_inactive,
        "total_procedures": len(procedures),
        "total_routes": len(routes),
        "total_checkpoints": len(checkpoints),
        "procedure_types": list(set(p.procedure_type.value for p in procedures)),
        "route_types": list(set(r.route_type for r in routes)),
        "checkpoint_types": list(set(c.checkpoint_type.value for c in checkpoints)),
    }

    return EmergencyPlanExportResponse(
        building_id=str(building.id),
        building_name=building.name,
        building_address=building.full_address,
        exported_at=datetime.utcnow().isoformat(),
        exported_by=current_user.email,
        procedures=[procedure_to_response(p) for p in procedures],
        routes=[route_to_response(r) for r in routes],
        checkpoints=[checkpoint_to_response(c) for c in checkpoints],
        metadata=metadata,
    )
