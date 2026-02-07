"""Device twin API endpoints for desired/reported config management."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.services.device_twin_service import (
    DeviceTwinService,
    DeviceNotFoundError,
)

router = APIRouter(tags=["Device Twin"])


class DeviceTwinConfigUpdate(BaseModel):
    """Request schema for updating desired config."""
    config: dict


class DeviceTwinDelta(BaseModel):
    """Delta between desired and reported configs."""
    is_synced: bool
    diff_summary: str
    differences: dict


class DeviceTwinResponse(BaseModel):
    """Response schema for device twin."""
    device_id: str
    desired_config: dict
    desired_version: int
    desired_updated_at: str | None
    reported_config: dict
    reported_version: int
    reported_updated_at: str | None
    is_synced: bool
    delta: DeviceTwinDelta


@router.get("/{device_id}/twin", response_model=DeviceTwinResponse)
async def get_device_twin(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get device twin with desired/reported config and sync delta."""
    from app.main import get_mqtt_service
    mqtt_service = await get_mqtt_service()
    service = DeviceTwinService(db, mqtt_service)

    try:
        twin_data = await service.get_twin_with_delta(device_id)
        return twin_data
    except DeviceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{device_id}/twin", response_model=DeviceTwinResponse)
async def update_device_twin(
    device_id: UUID,
    payload: DeviceTwinConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update desired config for device.

    Merges provided config with existing desired config (partial updates supported).
    Publishes to MQTT with retain flag and emits Socket.IO event.
    """
    from app.main import get_mqtt_service
    mqtt_service = await get_mqtt_service()
    service = DeviceTwinService(db, mqtt_service)

    try:
        await service.update_desired_config(device_id, payload.config)
        twin_data = await service.get_twin_with_delta(device_id)
        return twin_data
    except DeviceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
