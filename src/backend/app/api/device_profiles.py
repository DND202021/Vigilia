"""Device Profile Management API endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.services.device_profile_service import DeviceProfileService, DeviceProfileError

router = APIRouter()


# ==================== Schemas ====================

class DeviceProfileCreate(BaseModel):
    """Create device profile request."""
    name: str = Field(..., min_length=1, max_length=200)
    device_type: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    telemetry_schema: list = Field(default_factory=list)
    attributes_server: dict = Field(default_factory=dict)
    attributes_client: dict = Field(default_factory=dict)
    alert_rules: list = Field(default_factory=list)
    default_config: dict = Field(default_factory=dict)
    is_default: bool = False


class DeviceProfileUpdate(BaseModel):
    """Update device profile request."""
    name: str | None = Field(None, max_length=200)
    device_type: str | None = None
    description: str | None = None
    telemetry_schema: list | None = None
    attributes_server: dict | None = None
    attributes_client: dict | None = None
    alert_rules: list | None = None
    default_config: dict | None = None
    is_default: bool | None = None


class DeviceProfileResponse(BaseModel):
    """Device profile response."""
    id: str
    name: str
    device_type: str
    description: str | None
    telemetry_schema: list
    attributes_server: dict
    attributes_client: dict
    alert_rules: list
    default_config: dict
    is_default: bool
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


# ==================== Helpers ====================

def profile_to_response(profile) -> DeviceProfileResponse:
    """Convert DeviceProfile model to response."""
    return DeviceProfileResponse(
        id=str(profile.id),
        name=profile.name,
        device_type=profile.device_type,
        description=profile.description,
        telemetry_schema=profile.telemetry_schema,
        attributes_server=profile.attributes_server,
        attributes_client=profile.attributes_client,
        alert_rules=profile.alert_rules,
        default_config=profile.default_config,
        is_default=profile.is_default,
        created_at=profile.created_at.isoformat() if profile.created_at else "",
        updated_at=profile.updated_at.isoformat() if profile.updated_at else "",
    )


# ==================== Endpoints ====================

@router.post("", response_model=DeviceProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_device_profile(
    data: DeviceProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DeviceProfileResponse:
    """Create a new device profile."""
    service = DeviceProfileService(db)
    try:
        profile = await service.create_profile(
            name=data.name,
            device_type=data.device_type,
            description=data.description,
            telemetry_schema=data.telemetry_schema,
            attributes_server=data.attributes_server,
            attributes_client=data.attributes_client,
            alert_rules=data.alert_rules,
            default_config=data.default_config,
            is_default=data.is_default,
        )
    except DeviceProfileError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return profile_to_response(profile)


@router.get("", response_model=list[DeviceProfileResponse])
async def list_device_profiles(
    device_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[DeviceProfileResponse]:
    """List device profiles with optional filters."""
    service = DeviceProfileService(db)
    profiles = await service.list_profiles(device_type=device_type)

    # Apply pagination
    start = (page - 1) * page_size
    end = start + page_size
    paginated_profiles = profiles[start:end]

    return [profile_to_response(p) for p in paginated_profiles]


@router.get("/{profile_id}", response_model=DeviceProfileResponse)
async def get_device_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DeviceProfileResponse:
    """Get device profile by ID."""
    try:
        profile_uuid = uuid.UUID(profile_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid profile ID")

    service = DeviceProfileService(db)
    profile = await service.get_profile(profile_uuid)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device profile not found")

    return profile_to_response(profile)


@router.patch("/{profile_id}", response_model=DeviceProfileResponse)
async def update_device_profile(
    profile_id: str,
    data: DeviceProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DeviceProfileResponse:
    """Update device profile."""
    try:
        profile_uuid = uuid.UUID(profile_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid profile ID")

    service = DeviceProfileService(db)
    updates = data.model_dump(exclude_unset=True)

    try:
        profile = await service.update_profile(profile_uuid, **updates)
    except DeviceProfileError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return profile_to_response(profile)


@router.delete("/{profile_id}")
async def delete_device_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Soft delete device profile."""
    try:
        profile_uuid = uuid.UUID(profile_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid profile ID")

    service = DeviceProfileService(db)
    try:
        await service.delete_profile(profile_uuid)
    except DeviceProfileError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return {"message": "Device profile deleted"}


@router.post("/seed", response_model=list[DeviceProfileResponse], status_code=status.HTTP_201_CREATED)
async def seed_default_profiles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[DeviceProfileResponse]:
    """Seed default device profiles (idempotent)."""
    service = DeviceProfileService(db)
    profiles = await service.seed_default_profiles()

    return [profile_to_response(p) for p in profiles]
