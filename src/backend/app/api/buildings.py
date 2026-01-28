"""Building Information API endpoints."""

from datetime import datetime, date
from typing import Any, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from starlette import status as http_status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.alert import Alert as AlertModel, AlertStatus as AlertStatusModel
from app.models.incident import Incident as IncidentModel
from app.models.building import (
    Building as BuildingModel,
    BuildingType as BuildingTypeModel,
    OccupancyType as OccupancyTypeModel,
    ConstructionType as ConstructionTypeModel,
    HazardLevel as HazardLevelModel,
    FloorPlan as FloorPlanModel,
)
from app.models.inspection import Inspection, InspectionType, InspectionStatus
from app.models.photo import BuildingPhoto
from app.models.document import BuildingDocument, DocumentCategory
from app.services.building_service import BuildingService, BuildingError
from app.services.building_analytics_service import BuildingAnalyticsService, BuildingAnalyticsError
from app.services.file_storage import get_file_storage, FileStorageError
from app.services.bim_parser import IFCParser, IFCParserError
from app.services.socketio import (
    emit_building_created,
    emit_building_updated,
    emit_floor_plan_uploaded,
    emit_floor_plan_updated,
    emit_markers_updated,
)

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

    # Emit WebSocket event for real-time updates
    building_response = building_to_response(building)
    try:
        await emit_building_created(building_response.model_dump())
    except Exception:
        pass  # Don't let emit failures break the API

    return building_response


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

    # Emit WebSocket event for real-time updates
    building_response = building_to_response(building)
    try:
        await emit_building_updated(building_response.model_dump(), str(building.id))
    except Exception:
        pass  # Don't let emit failures break the API

    return building_response


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


# ==================== BIM File Import Endpoint ====================

# Maximum IFC file size (100MB)
MAX_IFC_FILE_SIZE = 100 * 1024 * 1024


class BIMImportResponse(BaseModel):
    """Response from BIM file import."""

    success: bool
    message: str
    building_id: str
    bim_data: dict
    floors_created: int
    floors_updated: int
    locations_found: int
    ifc_schema: str | None = None


@router.post("/{building_id}/import-bim", response_model=BIMImportResponse)
async def import_bim_file(
    building_id: str,
    file: UploadFile = File(..., description="IFC file to import (.ifc)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BIMImportResponse:
    """Import BIM data from an IFC file.

    Accepts IFC2x3 and IFC4 format files. Extracts building information,
    floor data, and key locations (doors, stairs, elevators, fire equipment).

    The imported data will:
    - Update the building's bim_data field
    - Create FloorPlan records for each floor found in the IFC file
    - Extract key locations for emergency response planning

    Maximum file size: 100MB
    """
    import os
    import tempfile

    # Validate building_id format
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    # Validate file extension
    if not file.filename or not file.filename.lower().endswith('.ifc'):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="File must be an IFC file (.ifc)",
        )

    # Read file content with size limit check
    content = await file.read()
    file_size = len(content)

    if file_size > MAX_IFC_FILE_SIZE:
        max_mb = MAX_IFC_FILE_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {max_mb:.0f}MB",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="File is empty",
        )

    # Save file temporarily for parsing
    temp_path = None
    try:
        # Create temp file with proper extension for ifcopenshell
        with tempfile.NamedTemporaryFile(
            mode='wb',
            suffix='.ifc',
            delete=False,
        ) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        # Parse IFC file
        parser = IFCParser()
        try:
            bim_data = parser.parse_file(temp_path)
        except IFCParserError as e:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse IFC file: {str(e)}",
            )

        # Get building service
        service = BuildingService(db)

        # Verify building exists and user has access
        building = await service.get_building(building_uuid)
        if not building:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Building not found",
            )

        # Update building with BIM data
        try:
            building = await service.import_bim_data(
                building_uuid,
                bim_data=bim_data.to_dict(),
                bim_file_url=None,  # File stored temporarily, not persisted
            )
        except BuildingError as e:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        # Create or update floor plans from BIM floor data
        floors_created = 0
        floors_updated = 0

        # Get existing floor plans for the building
        existing_floors = await service.get_building_floor_plans(building_uuid)
        existing_floor_numbers = {fp.floor_number for fp in existing_floors}

        for floor_info in bim_data.floors:
            # Find key locations for this floor
            floor_key_locations = [
                loc.to_dict()
                for loc in bim_data.key_locations
                if loc.floor_number == floor_info.floor_number
            ]

            # Separate emergency exits from other locations
            emergency_exits = [
                loc for loc in floor_key_locations
                if loc.get('type') == 'door' and loc.get('properties', {}).get('is_emergency_exit')
            ]

            # Separate fire equipment
            fire_equipment = [
                loc for loc in floor_key_locations
                if loc.get('type') in ('fire_extinguisher', 'aed')
            ]

            # Other key locations (stairs, elevators, electrical panels)
            other_locations = [
                loc for loc in floor_key_locations
                if loc.get('type') in ('stairwell', 'elevator', 'electrical_panel', 'door')
                and not loc.get('properties', {}).get('is_emergency_exit')
            ]

            if floor_info.floor_number in existing_floor_numbers:
                # Update existing floor plan
                existing_fp = next(
                    fp for fp in existing_floors
                    if fp.floor_number == floor_info.floor_number
                )
                try:
                    await service.update_floor_plan(
                        floor_plan_id=existing_fp.id,
                        floor_name=floor_info.floor_name or existing_fp.floor_name,
                        floor_area_sqm=floor_info.area_sqm or existing_fp.floor_area_sqm,
                        ceiling_height_m=floor_info.ceiling_height_m or existing_fp.ceiling_height_m,
                        key_locations=other_locations or existing_fp.key_locations,
                        emergency_exits=emergency_exits or existing_fp.emergency_exits,
                        fire_equipment=fire_equipment or existing_fp.fire_equipment,
                        bim_floor_data=floor_info.to_dict(),
                    )
                    floors_updated += 1
                except BuildingError:
                    pass  # Skip if update fails
            else:
                # Create new floor plan
                try:
                    await service.add_floor_plan(
                        building_id=building_uuid,
                        floor_number=floor_info.floor_number,
                        floor_name=floor_info.floor_name,
                        floor_area_sqm=floor_info.area_sqm,
                        ceiling_height_m=floor_info.ceiling_height_m,
                        key_locations=other_locations if other_locations else None,
                        emergency_exits=emergency_exits if emergency_exits else None,
                        fire_equipment=fire_equipment if fire_equipment else None,
                        bim_floor_data=floor_info.to_dict(),
                    )
                    floors_created += 1
                except BuildingError:
                    pass  # Skip if floor already exists (race condition)

        await db.commit()

        # Emit WebSocket events for real-time updates
        building_response = building_to_response(building)
        try:
            await emit_building_updated(building_response.model_dump(), str(building.id))
        except Exception:
            pass  # Don't let emit failures break the API

        return BIMImportResponse(
            success=True,
            message=f"BIM data imported successfully from {file.filename}",
            building_id=str(building_uuid),
            bim_data=bim_data.to_dict(),
            floors_created=floors_created,
            floors_updated=floors_updated,
            locations_found=len(bim_data.key_locations),
            ifc_schema=bim_data.ifc_schema,
        )

    finally:
        # Clean up temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass  # Ignore cleanup errors


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

    # Emit WebSocket event for real-time updates
    floor_plan_response = floor_plan_to_response(floor_plan)
    try:
        await emit_floor_plan_uploaded(floor_plan_response.model_dump(), str(building_uuid))
    except Exception:
        pass  # Don't let emit failures break the API

    return floor_plan_response


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

        # Emit WebSocket event for real-time updates
        floor_plan_dict = floor_plan_to_response(floor_plan).model_dump()
        try:
            await emit_floor_plan_uploaded(floor_plan_dict, str(building_uuid))
        except Exception:
            pass  # Don't let emit failures break the API

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

    # Emit WebSocket event for real-time updates
    floor_plan_response = floor_plan_to_response(floor_plan)
    try:
        await emit_floor_plan_updated(floor_plan_response.model_dump(), str(floor_plan.building_id))
    except Exception:
        pass  # Don't let emit failures break the API

    return floor_plan_response


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

    # Emit WebSocket event for real-time marker updates
    try:
        await emit_markers_updated(str(floor_plan.id), str(floor_plan.building_id))
    except Exception:
        pass  # Don't let emit failures break the API

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


# ==================== Building Incident Endpoints ====================

class BuildingIncidentResponse(BaseModel):
    """Incident response for building context."""

    id: str
    incident_number: str
    category: str
    priority: int
    status: str
    title: str
    description: str | None = None
    latitude: float
    longitude: float
    address: str | None = None
    created_at: str
    updated_at: str


class PaginatedBuildingIncidentResponse(BaseModel):
    """Paginated building incident response."""

    items: list[BuildingIncidentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


def _incident_to_building_response(incident: IncidentModel) -> BuildingIncidentResponse:
    """Convert incident model to building incident response."""
    return BuildingIncidentResponse(
        id=str(incident.id),
        incident_number=incident.incident_number,
        category=incident.category.value if hasattr(incident.category, 'value') else incident.category,
        priority=incident.priority,
        status=incident.status.value if hasattr(incident.status, 'value') else incident.status,
        title=incident.title,
        description=incident.description,
        latitude=incident.latitude,
        longitude=incident.longitude,
        address=incident.address,
        created_at=incident.created_at.isoformat() if incident.created_at else datetime.utcnow().isoformat(),
        updated_at=incident.updated_at.isoformat() if incident.updated_at else datetime.utcnow().isoformat(),
    )


@router.get("/{building_id}/incidents", response_model=PaginatedBuildingIncidentResponse)
async def get_building_incidents(
    building_id: str,
    status: str | None = None,
    category: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedBuildingIncidentResponse:
    """Get incidents linked to a building."""
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

    query = select(IncidentModel).where(IncidentModel.building_id == building_uuid)

    if status:
        query = query.where(IncidentModel.status == status)
    if category:
        query = query.where(IncidentModel.category == category)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(IncidentModel.created_at.desc())
    result = await db.execute(query)
    incidents = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedBuildingIncidentResponse(
        items=[_incident_to_building_response(inc) for inc in incidents],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ==================== Inspection Endpoints ====================

@router.get("/{building_id}/inspections", response_model=dict)
async def get_building_inspections(
    building_id: str,
    inspection_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get inspections for a building."""
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    building = await db.get(BuildingModel, building_uuid)
    if not building:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Building not found")

    query = select(Inspection).where(Inspection.building_id == building_uuid)

    if inspection_type:
        try:
            type_enum = InspectionType(inspection_type)
            query = query.where(Inspection.inspection_type == type_enum)
        except ValueError:
            pass

    if status:
        try:
            status_enum = InspectionStatus(status)
            query = query.where(Inspection.status == status_enum)
        except ValueError:
            pass

    query = query.order_by(Inspection.scheduled_date.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    inspections = result.scalars().all()

    return {
        "items": [insp.to_dict() for insp in inspections],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post("/{building_id}/inspections", response_model=dict)
async def create_inspection(
    building_id: str,
    inspection_type: str,
    scheduled_date: str,
    inspector_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create an inspection for a building."""
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    building = await db.get(BuildingModel, building_uuid)
    if not building:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Building not found")

    try:
        type_enum = InspectionType(inspection_type)
    except ValueError:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid inspection type")

    try:
        sched_date = date.fromisoformat(scheduled_date)
    except ValueError:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid date format")

    inspection = Inspection(
        building_id=building_uuid,
        inspection_type=type_enum,
        scheduled_date=sched_date,
        inspector_name=inspector_name,
        created_by_id=current_user.id if current_user else None,
    )

    db.add(inspection)
    await db.commit()
    await db.refresh(inspection)

    return inspection.to_dict()


@router.get("/inspections/upcoming", response_model=dict)
async def get_upcoming_inspections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get all upcoming inspections (scheduled, future date)."""
    today = date.today()

    query = select(Inspection).where(
        Inspection.status == InspectionStatus.SCHEDULED,
        Inspection.scheduled_date >= today,
    ).order_by(Inspection.scheduled_date.asc())

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    inspections = result.scalars().all()

    return {
        "items": [insp.to_dict() for insp in inspections],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/inspections/overdue", response_model=dict)
async def get_overdue_inspections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get all overdue inspections (scheduled, past date)."""
    today = date.today()

    query = select(Inspection).where(
        Inspection.status == InspectionStatus.SCHEDULED,
        Inspection.scheduled_date < today,
    ).order_by(Inspection.scheduled_date.asc())

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    inspections = result.scalars().all()

    return {
        "items": [insp.to_dict() for insp in inspections],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/inspections/{inspection_id}", response_model=dict)
async def get_inspection(
    inspection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get an inspection by ID."""
    try:
        inspection_uuid = uuid.UUID(inspection_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid inspection_id format",
        )

    inspection = await db.get(Inspection, inspection_uuid)
    if not inspection:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Inspection not found")
    return inspection.to_dict()


@router.patch("/inspections/{inspection_id}", response_model=dict)
async def update_inspection(
    inspection_id: str,
    scheduled_date: Optional[str] = None,
    completed_date: Optional[str] = None,
    status: Optional[str] = None,
    inspector_name: Optional[str] = None,
    findings: Optional[str] = None,
    follow_up_required: Optional[bool] = None,
    follow_up_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update an inspection."""
    try:
        inspection_uuid = uuid.UUID(inspection_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid inspection_id format",
        )

    inspection = await db.get(Inspection, inspection_uuid)
    if not inspection:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    if scheduled_date is not None:
        try:
            inspection.scheduled_date = date.fromisoformat(scheduled_date)
        except ValueError:
            pass

    if completed_date is not None:
        try:
            inspection.completed_date = date.fromisoformat(completed_date)
        except ValueError:
            pass

    if status is not None:
        try:
            inspection.status = InspectionStatus(status)
        except ValueError:
            pass

    if inspector_name is not None:
        inspection.inspector_name = inspector_name

    if findings is not None:
        inspection.findings = findings

    if follow_up_required is not None:
        inspection.follow_up_required = follow_up_required

    if follow_up_date is not None:
        try:
            inspection.follow_up_date = date.fromisoformat(follow_up_date)
        except ValueError:
            pass

    await db.commit()
    await db.refresh(inspection)
    return inspection.to_dict()


@router.delete("/inspections/{inspection_id}")
async def delete_inspection(
    inspection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete an inspection."""
    try:
        inspection_uuid = uuid.UUID(inspection_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid inspection_id format",
        )

    inspection = await db.get(Inspection, inspection_uuid)
    if not inspection:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    await db.delete(inspection)
    await db.commit()

    return {"message": "Inspection deleted"}


# ==================== Document Endpoints ====================

@router.get("/{building_id}/documents", response_model=dict)
async def get_building_documents(
    building_id: str,
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get documents for a building."""
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    # Verify building exists
    building = await db.get(BuildingModel, building_uuid)
    if not building:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Building not found")

    query = select(BuildingDocument).where(BuildingDocument.building_id == building_uuid)

    if category:
        try:
            cat_enum = DocumentCategory(category)
            query = query.where(BuildingDocument.category == cat_enum)
        except ValueError:
            pass

    query = query.order_by(BuildingDocument.created_at.desc())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    documents = result.scalars().all()

    return {
        "items": [doc.to_dict() for doc in documents],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post("/{building_id}/documents/upload", response_model=dict)
async def upload_document(
    building_id: str,
    file: UploadFile = File(...),
    title: str = Form(...),
    category: str = Form("other"),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Upload a document for a building."""
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    # Verify building exists
    building = await db.get(BuildingModel, building_uuid)
    if not building:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Building not found")

    # Parse category
    try:
        cat_enum = DocumentCategory(category)
    except ValueError:
        cat_enum = DocumentCategory.OTHER

    # Get file storage service
    storage = get_file_storage()

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Validate file size (50MB max)
    max_size = 50 * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {max_size / (1024*1024):.0f}MB",
        )

    # Save file
    import uuid as uuid_module
    file_ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "bin"
    filename = f"doc_{uuid_module.uuid4().hex[:8]}.{file_ext}"

    # Use building documents path
    building_path = storage._get_building_path(building_uuid)
    docs_path = building_path.parent / "documents"
    docs_path.mkdir(parents=True, exist_ok=True)

    file_path = docs_path / filename
    with open(file_path, "wb") as f:
        f.write(content)

    file_url = f"/api/v1/buildings/{building_id}/documents/files/{filename}"

    # Create document record
    document = BuildingDocument(
        building_id=building_uuid,
        category=cat_enum,
        title=title,
        description=description,
        file_url=file_url,
        file_type=file_ext,
        file_size=file_size,
        uploaded_by_id=current_user.id if current_user else None,
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    return document.to_dict()


@router.get("/{building_id}/documents/files/{filename}")
async def serve_document_file(
    building_id: str,
    filename: str,
    current_user: User = Depends(get_current_active_user),
):
    """Serve a document file."""
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    storage = get_file_storage()
    building_path = storage._get_building_path(building_uuid)
    file_path = building_path.parent / "documents" / filename

    if not file_path.exists():
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="File not found")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=storage.get_content_type(filename),
    )


@router.get("/documents/{document_id}", response_model=dict)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a document by ID."""
    try:
        document_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid document_id format",
        )

    document = await db.get(BuildingDocument, document_uuid)
    if not document:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document.to_dict()


@router.patch("/documents/{document_id}", response_model=dict)
async def update_document(
    document_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a document."""
    try:
        document_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid document_id format",
        )

    document = await db.get(BuildingDocument, document_uuid)
    if not document:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Document not found")

    if title is not None:
        document.title = title
    if description is not None:
        document.description = description
    if category is not None:
        try:
            document.category = DocumentCategory(category)
        except ValueError:
            pass

    await db.commit()
    await db.refresh(document)
    return document.to_dict()


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a document."""
    try:
        document_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid document_id format",
        )

    document = await db.get(BuildingDocument, document_uuid)
    if not document:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Delete file
    storage = get_file_storage()
    building_path = storage._get_building_path(document.building_id)
    filename = document.file_url.split("/")[-1]
    file_path = building_path.parent / "documents" / filename
    if file_path.exists():
        file_path.unlink()

    await db.delete(document)
    await db.commit()

    return {"message": "Document deleted"}


# ==================== Building Photo Endpoints ====================

@router.get("/{building_id}/photos", response_model=dict)
async def get_building_photos(
    building_id: str,
    tags: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    floor_plan_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get photos for a building."""
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    building = await db.get(BuildingModel, building_uuid)
    if not building:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Building not found")

    query = select(BuildingPhoto).where(BuildingPhoto.building_id == building_uuid)

    if floor_plan_id:
        try:
            floor_uuid = uuid.UUID(floor_plan_id)
            query = query.where(BuildingPhoto.floor_plan_id == floor_uuid)
        except ValueError:
            pass

    # Tag filtering would require JSON operations - simplified for now

    query = query.order_by(BuildingPhoto.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    photos = result.scalars().all()

    return {
        "items": [photo.to_dict() for photo in photos],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post("/{building_id}/photos/upload", response_model=dict)
async def upload_photo(
    building_id: str,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    floor_plan_id: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    tags: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Upload a photo for a building."""
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    building = await db.get(BuildingModel, building_uuid)
    if not building:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Building not found")

    # Validate content type
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="File must be an image")

    storage = get_file_storage()

    content = await file.read()
    file_size = len(content)

    import uuid as uuid_module
    file_ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    filename = f"photo_{uuid_module.uuid4().hex[:8]}.{file_ext}"
    thumb_filename = f"photo_{uuid_module.uuid4().hex[:8]}_thumb.{file_ext}"

    # Save to photos directory
    building_path = storage._get_building_path(building_uuid)
    photos_path = building_path.parent / "photos"
    photos_path.mkdir(parents=True, exist_ok=True)

    file_path = photos_path / filename
    with open(file_path, "wb") as f:
        f.write(content)

    file_url = f"/api/v1/buildings/{building_id}/photos/files/{filename}"
    thumbnail_url = None

    # Generate thumbnail
    try:
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(content))
        img.thumbnail((300, 300))

        thumb_path = photos_path / thumb_filename
        img.save(thumb_path, quality=85)
        thumbnail_url = f"/api/v1/buildings/{building_id}/photos/files/{thumb_filename}"
    except Exception:
        pass  # Thumbnail generation failed, continue without

    # Parse tags
    tag_list = []
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    # Parse floor_plan_id
    floor_plan_uuid = None
    if floor_plan_id:
        try:
            floor_plan_uuid = uuid.UUID(floor_plan_id)
        except ValueError:
            pass

    photo = BuildingPhoto(
        building_id=building_uuid,
        floor_plan_id=floor_plan_uuid,
        title=title,
        description=description,
        file_url=file_url,
        thumbnail_url=thumbnail_url,
        latitude=latitude,
        longitude=longitude,
        uploaded_by_id=current_user.id if current_user else None,
        tags=tag_list,
    )

    db.add(photo)
    await db.commit()
    await db.refresh(photo)

    return photo.to_dict()


@router.get("/{building_id}/photos/files/{filename}")
async def serve_photo_file(
    building_id: str,
    filename: str,
    current_user: User = Depends(get_current_active_user),
):
    """Serve a photo file."""
    try:
        building_uuid = uuid.UUID(building_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid building_id format",
        )

    storage = get_file_storage()
    building_path = storage._get_building_path(building_uuid)
    file_path = building_path.parent / "photos" / filename

    if not file_path.exists():
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="File not found")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=storage.get_content_type(filename),
    )


@router.get("/photos/{photo_id}", response_model=dict)
async def get_photo(
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a photo by ID."""
    try:
        photo_uuid = uuid.UUID(photo_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid photo_id format",
        )

    photo = await db.get(BuildingPhoto, photo_uuid)
    if not photo:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Photo not found")
    return photo.to_dict()


@router.delete("/photos/{photo_id}")
async def delete_photo(
    photo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a photo."""
    try:
        photo_uuid = uuid.UUID(photo_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid photo_id format",
        )

    photo = await db.get(BuildingPhoto, photo_uuid)
    if not photo:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Photo not found")

    # Delete files
    storage = get_file_storage()
    building_path = storage._get_building_path(photo.building_id)

    filename = photo.file_url.split("/")[-1]
    file_path = building_path.parent / "photos" / filename
    if file_path.exists():
        file_path.unlink()

    if photo.thumbnail_url:
        thumb_filename = photo.thumbnail_url.split("/")[-1]
        thumb_path = building_path.parent / "photos" / thumb_filename
        if thumb_path.exists():
            thumb_path.unlink()

    await db.delete(photo)
    await db.commit()

    return {"message": "Photo deleted"}


# ==================== Building Analytics Endpoints ====================

@router.get("/{building_id}/analytics")
async def get_building_analytics(
    building_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Get complete analytics dashboard for a building."""
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

    try:
        analytics_service = BuildingAnalyticsService(db)
        return await analytics_service.get_building_overview(building_uuid)
    except BuildingAnalyticsError as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{building_id}/analytics/devices")
async def get_device_analytics(
    building_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Get device health analytics for a building."""
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

    try:
        analytics_service = BuildingAnalyticsService(db)
        return await analytics_service.get_device_health(building_uuid)
    except BuildingAnalyticsError as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{building_id}/analytics/incidents")
async def get_incident_analytics(
    building_id: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Get incident statistics for a building."""
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

    try:
        analytics_service = BuildingAnalyticsService(db)
        return await analytics_service.get_incident_stats(building_uuid, days=days)
    except BuildingAnalyticsError as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{building_id}/analytics/alerts")
async def get_alert_analytics(
    building_id: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Get alert breakdown for a building."""
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

    try:
        analytics_service = BuildingAnalyticsService(db)
        return await analytics_service.get_alert_breakdown(building_uuid, days=days)
    except BuildingAnalyticsError as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{building_id}/analytics/inspections")
async def get_inspection_analytics(
    building_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Get inspection compliance metrics for a building."""
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

    try:
        analytics_service = BuildingAnalyticsService(db)
        return await analytics_service.get_inspection_compliance(building_uuid)
    except BuildingAnalyticsError as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
