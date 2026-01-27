"""Building Information API endpoints."""

from datetime import datetime
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from starlette import status as http_status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.alert import Alert as AlertModel, AlertStatus as AlertStatusModel
from app.models.building import (
    Building as BuildingModel,
    BuildingType as BuildingTypeModel,
    OccupancyType as OccupancyTypeModel,
    ConstructionType as ConstructionTypeModel,
    HazardLevel as HazardLevelModel,
    FloorPlan as FloorPlanModel,
)
from app.services.building_service import BuildingService, BuildingError
from app.services.file_storage import get_file_storage, FileStorageError

router = APIRouter()


# ==================== Pydantic Schemas ====================

class BuildingLocation(BaseModel):
    """Geographic location for building."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class EmergencyContact(BaseModel):
    """Emergency contact information."""

    name: str | None = None
    phone: str | None = None


class BuildingCreateRequest(BaseModel):
    """Request to create a new building."""

    name: str = Field(..., min_length=1, max_length=200)
    civic_number: str | None = None
    street_name: str = Field(..., min_length=1, max_length=200)
    street_type: str | None = None
    unit_number: str | None = None
    city: str = Field(..., min_length=1, max_length=100)
    province_state: str = Field(..., min_length=1, max_length=100)
    postal_code: str | None = None
    country: str = "Canada"

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

    building_type: str = "other"
    occupancy_type: str | None = None
    construction_type: str = "unknown"

    year_built: int | None = None
    year_renovated: int | None = None
    total_floors: int = Field(1, ge=1)
    basement_levels: int = Field(0, ge=0)
    total_area_sqm: float | None = None
    building_height_m: float | None = None
    max_occupancy: int | None = None

    hazard_level: str = "low"
    has_sprinkler_system: bool = False
    has_fire_alarm: bool = False
    has_standpipe: bool = False
    has_elevator: bool = False
    elevator_count: int | None = None
    has_generator: bool = False

    primary_entrance: str | None = None
    secondary_entrances: list[str] | None = None
    roof_access: str | None = None
    staging_area: str | None = None
    key_box_location: str | None = None
    knox_box: bool = False

    has_hazmat: bool = False
    hazmat_details: list[dict] | None = None
    utilities_info: dict | None = None

    owner_name: str | None = None
    owner_phone: str | None = None
    owner_email: str | None = None
    manager_name: str | None = None
    manager_phone: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None

    special_needs_occupants: bool = False
    special_needs_details: str | None = None
    animals_present: bool = False
    animals_details: str | None = None
    security_features: list[str] | None = None

    pre_incident_plan: str | None = None
    tactical_notes: str | None = None

    external_id: str | None = None
    data_source: str | None = None


class BuildingUpdateRequest(BaseModel):
    """Request to update building information."""

    name: str | None = None
    civic_number: str | None = None
    street_name: str | None = None
    street_type: str | None = None
    unit_number: str | None = None
    city: str | None = None
    province_state: str | None = None
    postal_code: str | None = None
    country: str | None = None

    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)

    building_type: str | None = None
    occupancy_type: str | None = None
    construction_type: str | None = None

    year_built: int | None = None
    year_renovated: int | None = None
    total_floors: int | None = None
    basement_levels: int | None = None
    total_area_sqm: float | None = None
    building_height_m: float | None = None
    max_occupancy: int | None = None

    hazard_level: str | None = None
    has_sprinkler_system: bool | None = None
    has_fire_alarm: bool | None = None
    has_standpipe: bool | None = None
    has_elevator: bool | None = None
    elevator_count: int | None = None
    has_generator: bool | None = None

    primary_entrance: str | None = None
    secondary_entrances: list[str] | None = None
    roof_access: str | None = None
    staging_area: str | None = None
    key_box_location: str | None = None
    knox_box: bool | None = None

    has_hazmat: bool | None = None
    hazmat_details: list[dict] | None = None
    utilities_info: dict | None = None

    owner_name: str | None = None
    owner_phone: str | None = None
    owner_email: str | None = None
    manager_name: str | None = None
    manager_phone: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None

    special_needs_occupants: bool | None = None
    special_needs_details: str | None = None
    animals_present: bool | None = None
    animals_details: str | None = None
    security_features: list[str] | None = None

    pre_incident_plan: str | None = None
    tactical_notes: str | None = None


class BuildingResponse(BaseModel):
    """Building response model."""

    id: str
    name: str
    civic_number: str | None = None
    street_name: str
    street_type: str | None = None
    unit_number: str | None = None
    city: str
    province_state: str
    postal_code: str | None = None
    country: str
    full_address: str

    latitude: float
    longitude: float

    building_type: str
    occupancy_type: str | None = None
    construction_type: str

    year_built: int | None = None
    year_renovated: int | None = None
    total_floors: int
    basement_levels: int
    total_area_sqm: float | None = None
    building_height_m: float | None = None
    max_occupancy: int | None = None

    hazard_level: str
    has_sprinkler_system: bool
    has_fire_alarm: bool
    has_standpipe: bool
    has_elevator: bool
    elevator_count: int | None = None
    has_generator: bool

    primary_entrance: str | None = None
    secondary_entrances: list[str] | None = None
    roof_access: str | None = None
    staging_area: str | None = None
    key_box_location: str | None = None
    knox_box: bool

    has_hazmat: bool
    hazmat_details: list[dict] | None = None
    utilities_info: dict | None = None

    owner_name: str | None = None
    owner_phone: str | None = None
    owner_email: str | None = None
    manager_name: str | None = None
    manager_phone: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None

    special_needs_occupants: bool
    special_needs_details: str | None = None
    animals_present: bool
    animals_details: str | None = None
    security_features: list[str] | None = None

    pre_incident_plan: str | None = None
    tactical_notes: str | None = None

    bim_file_url: str | None = None
    has_bim_data: bool = False

    external_id: str | None = None
    data_source: str | None = None

    is_verified: bool
    verified_at: str | None = None

    agency_id: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class FloorPlanCreateRequest(BaseModel):
    """Request to create a floor plan."""

    floor_number: int
    floor_name: str | None = None
    plan_file_url: str | None = None
    file_type: str | None = None
    floor_area_sqm: float | None = None
    ceiling_height_m: float | None = None
    key_locations: list[dict] | None = None
    emergency_exits: list[dict] | None = None
    fire_equipment: list[dict] | None = None
    hazards: list[dict] | None = None
    notes: str | None = None


class FloorPlanResponse(BaseModel):
    """Floor plan response model."""

    id: str
    building_id: str
    floor_number: int
    floor_name: str | None = None
    plan_file_url: str | None = None
    plan_thumbnail_url: str | None = None
    file_type: str | None = None
    floor_area_sqm: float | None = None
    ceiling_height_m: float | None = None
    key_locations: list[dict] | None = None
    emergency_exits: list[dict] | None = None
    fire_equipment: list[dict] | None = None
    hazards: list[dict] | None = None
    notes: str | None = None
    has_bim_data: bool = False
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class PaginatedBuildingResponse(BaseModel):
    """Paginated building response."""

    items: list[BuildingResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class BIMImportRequest(BaseModel):
    """Request to import BIM data."""

    bim_data: dict
    bim_file_url: str | None = None


class BuildingStatsResponse(BaseModel):
    """Building statistics response."""

    total: int
    verified: int
    unverified: int
    by_type: dict[str, int]
    by_hazard_level: dict[str, int]
    with_hazmat: int
    with_sprinkler: int
    high_rise: int


# ==================== Helper Functions ====================

def building_to_response(building: BuildingModel) -> BuildingResponse:
    """Convert a database building model to response."""
    return BuildingResponse(
        id=str(building.id),
        name=building.name,
        civic_number=building.civic_number,
        street_name=building.street_name,
        street_type=building.street_type,
        unit_number=building.unit_number,
        city=building.city,
        province_state=building.province_state,
        postal_code=building.postal_code,
        country=building.country,
        full_address=building.full_address,
        latitude=building.latitude,
        longitude=building.longitude,
        building_type=building.building_type.value,
        occupancy_type=building.occupancy_type.value if building.occupancy_type else None,
        construction_type=building.construction_type.value,
        year_built=building.year_built,
        year_renovated=building.year_renovated,
        total_floors=building.total_floors,
        basement_levels=building.basement_levels,
        total_area_sqm=building.total_area_sqm,
        building_height_m=building.building_height_m,
        max_occupancy=building.max_occupancy,
        hazard_level=building.hazard_level.value,
        has_sprinkler_system=building.has_sprinkler_system,
        has_fire_alarm=building.has_fire_alarm,
        has_standpipe=building.has_standpipe,
        has_elevator=building.has_elevator,
        elevator_count=building.elevator_count,
        has_generator=building.has_generator,
        primary_entrance=building.primary_entrance,
        secondary_entrances=building.secondary_entrances,
        roof_access=building.roof_access,
        staging_area=building.staging_area,
        key_box_location=building.key_box_location,
        knox_box=building.knox_box,
        has_hazmat=building.has_hazmat,
        hazmat_details=building.hazmat_details,
        utilities_info=building.utilities_info,
        owner_name=building.owner_name,
        owner_phone=building.owner_phone,
        owner_email=building.owner_email,
        manager_name=building.manager_name,
        manager_phone=building.manager_phone,
        emergency_contact_name=building.emergency_contact_name,
        emergency_contact_phone=building.emergency_contact_phone,
        special_needs_occupants=building.special_needs_occupants,
        special_needs_details=building.special_needs_details,
        animals_present=building.animals_present,
        animals_details=building.animals_details,
        security_features=building.security_features,
        pre_incident_plan=building.pre_incident_plan,
        tactical_notes=building.tactical_notes,
        bim_file_url=building.bim_file_url,
        has_bim_data=building.bim_data is not None,
        external_id=building.external_id,
        data_source=building.data_source,
        is_verified=building.is_verified,
        verified_at=building.verified_at.isoformat() if building.verified_at else None,
        agency_id=str(building.agency_id),
        created_at=building.created_at.isoformat() if building.created_at else datetime.utcnow().isoformat(),
        updated_at=building.updated_at.isoformat() if building.updated_at else datetime.utcnow().isoformat(),
    )


def floor_plan_to_response(floor_plan: FloorPlanModel) -> FloorPlanResponse:
    """Convert a database floor plan model to response."""
    return FloorPlanResponse(
        id=str(floor_plan.id),
        building_id=str(floor_plan.building_id),
        floor_number=floor_plan.floor_number,
        floor_name=floor_plan.floor_name,
        plan_file_url=floor_plan.plan_file_url,
        plan_thumbnail_url=floor_plan.plan_thumbnail_url,
        file_type=floor_plan.file_type,
        floor_area_sqm=floor_plan.floor_area_sqm,
        ceiling_height_m=floor_plan.ceiling_height_m,
        key_locations=floor_plan.key_locations,
        emergency_exits=floor_plan.emergency_exits,
        fire_equipment=floor_plan.fire_equipment,
        hazards=floor_plan.hazards,
        notes=floor_plan.notes,
        has_bim_data=floor_plan.bim_floor_data is not None,
        created_at=floor_plan.created_at.isoformat() if floor_plan.created_at else datetime.utcnow().isoformat(),
        updated_at=floor_plan.updated_at.isoformat() if floor_plan.updated_at else datetime.utcnow().isoformat(),
    )


# ==================== Building Endpoints ====================

@router.get("", response_model=PaginatedBuildingResponse)
async def list_buildings(
    building_type: str | None = None,
    city: str | None = None,
    search: str | None = Query(None, description="Search by name or address"),
    near_lat: float | None = Query(None, ge=-90, le=90, description="Latitude for proximity search"),
    near_lng: float | None = Query(None, ge=-180, le=180, description="Longitude for proximity search"),
    radius_km: float = Query(5.0, ge=0.1, le=100, description="Search radius in km"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedBuildingResponse:
    """List buildings with optional filtering and pagination."""
    service = BuildingService(db)

    # Parse building type
    bt = None
    if building_type:
        try:
            bt = BuildingTypeModel(building_type)
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid building_type: {building_type}",
            )

    buildings, total = await service.list_buildings(
        agency_id=current_user.agency_id,
        building_type=bt,
        city=city,
        search_query=search,
        near_latitude=near_lat,
        near_longitude=near_lng,
        radius_km=radius_km,
        limit=page_size,
        offset=(page - 1) * page_size,
    )

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedBuildingResponse(
        items=[building_to_response(b) for b in buildings],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/search", response_model=list[BuildingResponse])
async def search_buildings(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[BuildingResponse]:
    """Quick search buildings by name or address."""
    service = BuildingService(db)
    buildings = await service.search_buildings(
        query=q,
        agency_id=current_user.agency_id,
        limit=limit,
    )
    return [building_to_response(b) for b in buildings]


@router.get("/stats", response_model=BuildingStatsResponse)
async def get_building_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BuildingStatsResponse:
    """Get building statistics for the agency."""
    service = BuildingService(db)
    stats = await service.get_building_stats(agency_id=current_user.agency_id)
    return BuildingStatsResponse(**stats)


@router.get("/near/{latitude}/{longitude}", response_model=list[BuildingResponse])
async def get_buildings_near_location(
    latitude: float,
    longitude: float,
    radius_km: float = Query(1.0, ge=0.1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[BuildingResponse]:
    """Get buildings near a specific location."""
    service = BuildingService(db)
    results = await service.get_buildings_near_incident(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
    )
    return [building_to_response(b) for b, _ in results]


@router.get("/{building_id}", response_model=BuildingResponse)
async def get_building(
    building_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BuildingResponse:
    """Get a building by ID."""
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    service = BuildingService(db)
    building = await service.get_building(building_uuid)

    if not building:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Building not found",
        )

    return building_to_response(building)


@router.post("", response_model=BuildingResponse, status_code=http_status.HTTP_201_CREATED)
async def create_building(
    data: BuildingCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BuildingResponse:
    """Create a new building."""
    service = BuildingService(db)

    # Parse enums
    try:
        building_type = BuildingTypeModel(data.building_type)
    except ValueError:
        building_type = BuildingTypeModel.OTHER

    occupancy_type = None
    if data.occupancy_type:
        try:
            occupancy_type = OccupancyTypeModel(data.occupancy_type)
        except ValueError:
            pass

    try:
        construction_type = ConstructionTypeModel(data.construction_type)
    except ValueError:
        construction_type = ConstructionTypeModel.UNKNOWN

    try:
        hazard_level = HazardLevelModel(data.hazard_level)
    except ValueError:
        hazard_level = HazardLevelModel.LOW

    try:
        building = await service.create_building(
            agency_id=current_user.agency_id,
            name=data.name,
            civic_number=data.civic_number,
            street_name=data.street_name,
            street_type=data.street_type,
            unit_number=data.unit_number,
            city=data.city,
            province_state=data.province_state,
            postal_code=data.postal_code,
            country=data.country,
            latitude=data.latitude,
            longitude=data.longitude,
            building_type=building_type,
            occupancy_type=occupancy_type,
            construction_type=construction_type,
            year_built=data.year_built,
            year_renovated=data.year_renovated,
            total_floors=data.total_floors,
            basement_levels=data.basement_levels,
            total_area_sqm=data.total_area_sqm,
            building_height_m=data.building_height_m,
            max_occupancy=data.max_occupancy,
            hazard_level=hazard_level,
            has_sprinkler_system=data.has_sprinkler_system,
            has_fire_alarm=data.has_fire_alarm,
            has_standpipe=data.has_standpipe,
            has_elevator=data.has_elevator,
            elevator_count=data.elevator_count,
            has_generator=data.has_generator,
            primary_entrance=data.primary_entrance,
            secondary_entrances=data.secondary_entrances,
            roof_access=data.roof_access,
            staging_area=data.staging_area,
            key_box_location=data.key_box_location,
            knox_box=data.knox_box,
            has_hazmat=data.has_hazmat,
            hazmat_details=data.hazmat_details,
            utilities_info=data.utilities_info,
            owner_name=data.owner_name,
            owner_phone=data.owner_phone,
            owner_email=data.owner_email,
            manager_name=data.manager_name,
            manager_phone=data.manager_phone,
            emergency_contact_name=data.emergency_contact_name,
            emergency_contact_phone=data.emergency_contact_phone,
            special_needs_occupants=data.special_needs_occupants,
            special_needs_details=data.special_needs_details,
            animals_present=data.animals_present,
            animals_details=data.animals_details,
            security_features=data.security_features,
            pre_incident_plan=data.pre_incident_plan,
            tactical_notes=data.tactical_notes,
            external_id=data.external_id,
            data_source=data.data_source,
        )
    except BuildingError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return building_to_response(building)


@router.patch("/{building_id}", response_model=BuildingResponse)
async def update_building(
    building_id: str,
    data: BuildingUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BuildingResponse:
    """Update a building."""
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    service = BuildingService(db)

    # Build updates dict, converting enum strings to enum values
    updates = {}
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            if field == 'building_type':
                try:
                    updates[field] = BuildingTypeModel(value)
                except ValueError:
                    pass
            elif field == 'occupancy_type':
                try:
                    updates[field] = OccupancyTypeModel(value)
                except ValueError:
                    pass
            elif field == 'construction_type':
                try:
                    updates[field] = ConstructionTypeModel(value)
                except ValueError:
                    pass
            elif field == 'hazard_level':
                try:
                    updates[field] = HazardLevelModel(value)
                except ValueError:
                    pass
            else:
                updates[field] = value

    try:
        building = await service.update_building(building_uuid, **updates)
    except BuildingError as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return building_to_response(building)


@router.delete("/{building_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_building(
    building_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Soft delete a building."""
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    service = BuildingService(db)
    try:
        await service.delete_building(building_uuid)
    except BuildingError as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{building_id}/verify", response_model=BuildingResponse)
async def verify_building(
    building_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BuildingResponse:
    """Mark a building as verified."""
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    service = BuildingService(db)
    try:
        building = await service.verify_building(
            building_uuid,
            verified_by_id=current_user.id,
        )
    except BuildingError as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return building_to_response(building)


# ==================== BIM Import Endpoint ====================

@router.post("/{building_id}/bim", response_model=BuildingResponse)
async def import_bim_data(
    building_id: str,
    data: BIMImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BuildingResponse:
    """Import BIM (Building Information Model) data for a building."""
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    service = BuildingService(db)
    try:
        building = await service.import_bim_data(
            building_uuid,
            bim_data=data.bim_data,
            bim_file_url=data.bim_file_url,
        )
    except BuildingError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return building_to_response(building)


# ==================== Floor Plan Endpoints ====================

@router.get("/{building_id}/floors", response_model=list[FloorPlanResponse])
async def get_building_floor_plans(
    building_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[FloorPlanResponse]:
    """Get all floor plans for a building."""
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    service = BuildingService(db)
    floor_plans = await service.get_building_floor_plans(building_uuid)
    return [floor_plan_to_response(fp) for fp in floor_plans]


@router.post("/{building_id}/floors", response_model=FloorPlanResponse, status_code=http_status.HTTP_201_CREATED)
async def add_floor_plan(
    building_id: str,
    data: FloorPlanCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FloorPlanResponse:
    """Add a floor plan to a building."""
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    service = BuildingService(db)
    try:
        floor_plan = await service.add_floor_plan(
            building_id=building_uuid,
            floor_number=data.floor_number,
            floor_name=data.floor_name,
            plan_file_url=data.plan_file_url,
            file_type=data.file_type,
            floor_area_sqm=data.floor_area_sqm,
            ceiling_height_m=data.ceiling_height_m,
            key_locations=data.key_locations,
            emergency_exits=data.emergency_exits,
            fire_equipment=data.fire_equipment,
            hazards=data.hazards,
            notes=data.notes,
        )
    except BuildingError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return floor_plan_to_response(floor_plan)


@router.get("/{building_id}/floors/{floor_number}", response_model=FloorPlanResponse)
async def get_floor_plan_by_number(
    building_id: str,
    floor_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FloorPlanResponse:
    """Get a specific floor plan by floor number."""
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    service = BuildingService(db)
    floor_plans = await service.get_building_floor_plans(building_uuid)

    for fp in floor_plans:
        if fp.floor_number == floor_number:
            return floor_plan_to_response(fp)

    raise HTTPException(
        status_code=http_status.HTTP_404_NOT_FOUND,
        detail=f"Floor plan for floor {floor_number} not found",
    )


@router.delete("/floors/{floor_plan_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_floor_plan(
    floor_plan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Delete a floor plan."""
    try:
        floor_plan_uuid = uuid.UUID(floor_plan_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid floor_plan_id format",
        )

    service = BuildingService(db)
    try:
        await service.delete_floor_plan(floor_plan_uuid)
    except BuildingError as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ==================== Floor Plan File Upload Endpoints ====================

class FloorPlanUploadResponse(BaseModel):
    """Response after uploading a floor plan file."""

    id: str
    floor_number: int
    floor_name: str | None
    plan_file_url: str
    plan_thumbnail_url: str | None
    file_type: str
    message: str


@router.post(
    "/{building_id}/floor-plans/upload",
    response_model=FloorPlanUploadResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def upload_floor_plan(
    building_id: str,
    floor_number: int = Query(..., description="Floor number (negative for basements)"),
    floor_name: str | None = Query(None, description="Optional floor name"),
    file: UploadFile = File(..., description="Floor plan image (PNG, JPG, PDF, SVG, DWG)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FloorPlanUploadResponse:
    """Upload a floor plan file for a building.

    Accepts PNG, JPG, PDF, SVG, and DWG files up to 50MB.
    Automatically generates thumbnails for image files.
    """
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    # Verify building exists
    service = BuildingService(db)
    building = await service.get_building(building_uuid)
    if not building:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Building not found",
        )

    # Read file content
    file_content = await file.read()

    # Get file storage service
    storage = get_file_storage()

    try:
        # Save file
        file_url, thumbnail_url, file_type = await storage.save_floor_plan(
            building_id=building_uuid,
            floor_number=floor_number,
            file_content=file_content,
            content_type=file.content_type or "application/octet-stream",
        )

        # Create or update floor plan record in database
        try:
            floor_plan = await service.add_floor_plan(
                building_id=building_uuid,
                floor_number=floor_number,
                floor_name=floor_name,
                plan_file_url=file_url,
                plan_thumbnail_url=thumbnail_url,
                file_type=file_type,
            )
        except BuildingError:
            # Floor plan exists, update it
            floor_plans = await service.get_building_floor_plans(building_uuid)
            existing = next(
                (fp for fp in floor_plans if fp.floor_number == floor_number),
                None
            )
            if existing:
                floor_plan = await service.update_floor_plan(
                    floor_plan_id=existing.id,
                    plan_file_url=file_url,
                    plan_thumbnail_url=thumbnail_url,
                    file_type=file_type,
                    floor_name=floor_name or existing.floor_name,
                )
            else:
                raise

        return FloorPlanUploadResponse(
            id=str(floor_plan.id),
            floor_number=floor_plan.floor_number,
            floor_name=floor_plan.floor_name,
            plan_file_url=file_url,
            plan_thumbnail_url=thumbnail_url,
            file_type=file_type,
            message="Floor plan uploaded successfully",
        )

    except FileStorageError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{building_id}/floor-plans/files/{filename}")
async def get_floor_plan_file(
    building_id: str,
    filename: str,
    current_user: User = Depends(get_current_active_user),
) -> FileResponse:
    """Serve a floor plan file.

    Returns the file with appropriate content type for display/download.
    """
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    storage = get_file_storage()
    file_path = storage.get_file_path(building_uuid, filename)

    if not file_path:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    content_type = storage.get_content_type(filename)

    return FileResponse(
        path=file_path,
        media_type=content_type,
        filename=filename,
    )


class FloorPlanUpdateRequest(BaseModel):
    """Request to update a floor plan."""

    floor_name: str | None = None
    floor_area_sqm: float | None = None
    ceiling_height_m: float | None = None
    key_locations: list[dict] | None = None
    emergency_exits: list[dict] | None = None
    fire_equipment: list[dict] | None = None
    hazards: list[dict] | None = None
    notes: str | None = None


@router.patch("/floors/{floor_plan_id}", response_model=FloorPlanResponse)
async def update_floor_plan(
    floor_plan_id: str,
    data: FloorPlanUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FloorPlanResponse:
    """Update floor plan information."""
    try:
        floor_plan_uuid = uuid.UUID(floor_plan_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid floor_plan_id format",
        )

    service = BuildingService(db)

    updates = {}
    if data.floor_name is not None:
        updates['floor_name'] = data.floor_name
    if data.floor_area_sqm is not None:
        updates['floor_area_sqm'] = data.floor_area_sqm
    if data.ceiling_height_m is not None:
        updates['ceiling_height_m'] = data.ceiling_height_m
    if data.key_locations is not None:
        updates['key_locations'] = data.key_locations
    if data.emergency_exits is not None:
        updates['emergency_exits'] = data.emergency_exits
    if data.fire_equipment is not None:
        updates['fire_equipment'] = data.fire_equipment
    if data.hazards is not None:
        updates['hazards'] = data.hazards
    if data.notes is not None:
        updates['notes'] = data.notes

    try:
        floor_plan = await service.update_floor_plan(floor_plan_uuid, **updates)
    except BuildingError as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return floor_plan_to_response(floor_plan)


@router.patch("/floors/{floor_plan_id}/locations", response_model=FloorPlanResponse)
async def update_floor_plan_locations(
    floor_plan_id: str,
    key_locations: list[dict] | None = None,
    emergency_exits: list[dict] | None = None,
    fire_equipment: list[dict] | None = None,
    hazards: list[dict] | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FloorPlanResponse:
    """Update key locations and emergency information on a floor plan.

    This endpoint is optimized for the floor plan marking tool.
    """
    try:
        floor_plan_uuid = uuid.UUID(floor_plan_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid floor_plan_id format",
        )

    service = BuildingService(db)

    updates = {}
    if key_locations is not None:
        updates['key_locations'] = key_locations
    if emergency_exits is not None:
        updates['emergency_exits'] = emergency_exits
    if fire_equipment is not None:
        updates['fire_equipment'] = fire_equipment
    if hazards is not None:
        updates['hazards'] = hazards

    try:
        floor_plan = await service.update_floor_plan(floor_plan_uuid, **updates)
    except BuildingError as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return floor_plan_to_response(floor_plan)


# ==================== Building & Floor Alert Endpoints ====================

class BuildingAlertResponse(BaseModel):
    """Alert response for building context."""

    id: str
    source: str
    severity: str
    status: str
    alert_type: str
    title: str
    description: str | None = None
    device_id: str | None = None
    floor_plan_id: str | None = None
    confidence: float | None = None
    risk_level: str | None = None
    occurrence_count: int = 1
    last_occurrence: str | None = None
    assigned_to_id: str | None = None
    created_at: str


class PaginatedBuildingAlertResponse(BaseModel):
    """Paginated building alert response."""

    items: list[BuildingAlertResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


def _alert_to_building_response(alert: AlertModel) -> BuildingAlertResponse:
    """Convert alert model to building alert response."""
    return BuildingAlertResponse(
        id=str(alert.id),
        source=alert.source.value if hasattr(alert.source, 'value') else alert.source,
        severity=alert.severity.value if hasattr(alert.severity, 'value') else alert.severity,
        status=alert.status.value if hasattr(alert.status, 'value') else alert.status,
        alert_type=alert.alert_type,
        title=alert.title,
        description=alert.description,
        device_id=str(alert.device_id) if alert.device_id else None,
        floor_plan_id=str(alert.floor_plan_id) if alert.floor_plan_id else None,
        confidence=alert.confidence,
        risk_level=alert.risk_level,
        occurrence_count=alert.occurrence_count or 1,
        last_occurrence=alert.last_occurrence.isoformat() if alert.last_occurrence else None,
        assigned_to_id=str(alert.assigned_to_id) if alert.assigned_to_id else None,
        created_at=alert.created_at.isoformat() if alert.created_at else datetime.utcnow().isoformat(),
    )


@router.get("/{building_id}/alerts", response_model=PaginatedBuildingAlertResponse)
async def get_building_alerts(
    building_id: str,
    severity: str | None = None,
    status: str | None = None,
    alert_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedBuildingAlertResponse:
    """Get all alerts for a specific building."""
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    query = select(AlertModel).where(AlertModel.building_id == building_uuid)

    if severity:
        query = query.where(AlertModel.severity == severity)
    if status:
        query = query.where(AlertModel.status == AlertStatusModel(status))
    if alert_type:
        query = query.where(AlertModel.alert_type == alert_type)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(AlertModel.created_at.desc())
    result = await db.execute(query)
    alerts = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedBuildingAlertResponse(
        items=[_alert_to_building_response(a) for a in alerts],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{building_id}/alert-count")
async def get_building_alert_count(
    building_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Get active alert count for a building (for list view badges)."""
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    count_result = await db.execute(
        select(func.count()).select_from(
            select(AlertModel).where(
                AlertModel.building_id == building_uuid,
                AlertModel.status.in_([AlertStatusModel.PENDING, AlertStatusModel.ACKNOWLEDGED]),
            ).subquery()
        )
    )
    count = count_result.scalar() or 0

    return {"building_id": building_id, "active_alert_count": count}


@router.get("/floors/{floor_plan_id}/alerts", response_model=PaginatedBuildingAlertResponse)
async def get_floor_plan_alerts(
    floor_plan_id: str,
    severity: str | None = None,
    alert_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedBuildingAlertResponse:
    """Get all alerts for a specific floor plan."""
    try:
        floor_uuid = uuid.UUID(floor_plan_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid floor_plan_id format",
        )

    query = select(AlertModel).where(AlertModel.floor_plan_id == floor_uuid)

    if severity:
        query = query.where(AlertModel.severity == severity)
    if alert_type:
        query = query.where(AlertModel.alert_type == alert_type)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(AlertModel.created_at.desc())
    result = await db.execute(query)
    alerts = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedBuildingAlertResponse(
        items=[_alert_to_building_response(a) for a in alerts],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
