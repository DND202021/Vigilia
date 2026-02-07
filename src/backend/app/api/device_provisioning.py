"""Device Provisioning API endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.models.device import IoTDevice
from app.models.user import User
from app.services.device_provisioning_service import (
    DeviceProvisioningService,
    DeviceProvisioningError,
)

router = APIRouter()


# ==================== Schemas ====================

class DeviceProvisionRequest(BaseModel):
    """Request to provision a new device."""
    name: str = Field(..., min_length=1, max_length=200, description="Device name")
    device_type: str = Field(
        ...,
        pattern="^(microphone|camera|sensor|gateway)$",
        description="Device type"
    )
    building_id: str = Field(..., description="Building UUID where device is located")
    profile_id: str | None = Field(None, description="Optional device profile UUID")
    credential_type: str = Field(
        default="access_token",
        pattern="^(access_token|x509)$",
        description="Credential type: access_token or x509"
    )
    serial_number: str | None = Field(None, max_length=100, description="Device serial number")
    manufacturer: str | None = Field(None, max_length=100, description="Manufacturer name")
    model: str | None = Field(None, max_length=100, description="Device model")


class DeviceProvisionResponse(BaseModel):
    """Response after provisioning a device."""
    device_id: str = Field(..., description="UUID of provisioned device")
    name: str
    device_type: str
    building_id: str
    provisioning_status: str
    credential_type: str

    # One-time credentials (never retrievable after this response)
    access_token: str | None = Field(
        None,
        description="Returned only once during provisioning. Store securely. Never logged or stored plaintext."
    )
    certificate_pem: str | None = Field(None, description="Base64-encoded X.509 certificate (PEM format)")
    private_key_pem: str | None = Field(None, description="Base64-encoded private key (PEM format)")
    certificate_cn: str | None = Field(None, description="Certificate Common Name")
    certificate_expiry: str | None = Field(None, description="Certificate expiry timestamp (ISO format)")

    model_config = ConfigDict(from_attributes=True)


class DeviceStatusResponse(BaseModel):
    """Device provisioning status response."""
    id: str
    name: str
    device_type: str
    provisioning_status: str
    status: str
    last_seen: str | None

    model_config = ConfigDict(from_attributes=True)


# ==================== Endpoints ====================

@router.post("", response_model=DeviceProvisionResponse, status_code=status.HTTP_201_CREATED)
async def provision_device(
    data: DeviceProvisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DeviceProvisionResponse:
    """Provision a new device with unique credentials.

    Generates either an access token or X.509 certificate for device authentication.
    Credentials are returned ONCE and cannot be retrieved later.

    **Access Token Flow:**
    1. Generates cryptographically secure 256-bit token
    2. Stores bcrypt hash in database
    3. Returns plaintext token (store securely!)

    **X.509 Certificate Flow:**
    1. Generates 2048-bit RSA key pair
    2. Signs certificate with internal CA
    3. Returns base64-encoded certificate + private key PEM

    **Security Notes:**
    - Access tokens are never stored in plaintext
    - Certificates have 1-year validity
    - Device is assigned provisioning_status=pending until first MQTT connection
    """
    # Extract agency_id from current user
    agency_id = current_user.agency_id

    # Validate UUID formats
    try:
        building_uuid = uuid.UUID(data.building_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid building_id format: {data.building_id}"
        )

    profile_uuid = None
    if data.profile_id:
        try:
            profile_uuid = uuid.UUID(data.profile_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid profile_id format: {data.profile_id}"
            )

    # Provision device
    service = DeviceProvisioningService(db)
    try:
        device, credentials = await service.provision_device(
            name=data.name,
            device_type=data.device_type,
            building_id=building_uuid,
            agency_id=agency_id,
            credential_type=data.credential_type,
            profile_id=profile_uuid,
            serial_number=data.serial_number,
            manufacturer=data.manufacturer,
            model=data.model,
        )
    except DeviceProvisioningError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Build response with device info + one-time credentials
    response_data = {
        "device_id": str(device.id),
        "name": device.name,
        "device_type": device.device_type,
        "building_id": str(device.building_id),
        "provisioning_status": device.provisioning_status,
        "credential_type": data.credential_type,
    }

    # Add credential-specific fields
    if data.credential_type == "access_token":
        response_data["access_token"] = credentials.get("access_token")
    elif data.credential_type == "x509":
        response_data["certificate_pem"] = credentials.get("certificate_pem")
        response_data["private_key_pem"] = credentials.get("private_key_pem")
        response_data["certificate_cn"] = credentials.get("certificate_cn")
        response_data["certificate_expiry"] = credentials.get("certificate_expiry")

    return DeviceProvisionResponse(**response_data)


@router.get("/{device_id}", response_model=DeviceStatusResponse)
async def get_device_provisioning_status(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DeviceStatusResponse:
    """Get device provisioning status.

    Returns basic device information including provisioning_status and status.
    Does NOT return credentials for security reasons.
    """
    # Validate UUID format
    try:
        device_uuid = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid device_id format: {device_id}"
        )

    # Query device
    result = await db.execute(
        select(IoTDevice).where(IoTDevice.id == device_uuid)
    )
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )

    # Build response (no credentials exposed)
    return DeviceStatusResponse(
        id=str(device.id),
        name=device.name,
        device_type=device.device_type,
        provisioning_status=device.provisioning_status or "unprovisioned",
        status=device.status,
        last_seen=device.last_seen.isoformat() if device.last_seen else None,
    )
