"""Device provisioning service for generating credentials and registering devices."""

import base64
import csv
import secrets
import uuid
from datetime import datetime, timezone
from io import StringIO

from passlib.context import CryptContext
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.certificate_authority import CertificateAuthority, CertificateAuthorityError
from app.core.config import settings
from app.models.building import Building
from app.models.device import IoTDevice
from app.models.device_credentials import DeviceCredentials, CredentialType
from app.models.device_profile import DeviceProfile


# Password hashing context for access tokens
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class DeviceProvisioningError(Exception):
    """Device provisioning related errors."""
    pass


class DeviceProvisionRow(BaseModel):
    """CSV row validation schema for bulk provisioning."""
    name: str = Field(..., min_length=1, max_length=200, description="Device name")
    device_type: str = Field(
        ...,
        pattern="^(microphone|camera|sensor|gateway)$",
        description="Device type"
    )
    building_id: str = Field(..., description="Building UUID")
    profile_id: str | None = Field(None, description="Optional device profile UUID")
    credential_type: str = Field(
        default="access_token",
        pattern="^(access_token|x509)$",
        description="Credential type"
    )

    @field_validator("building_id")
    @classmethod
    def validate_building_id(cls, v: str) -> str:
        """Validate building_id is valid UUID format."""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError(f"Invalid UUID format: {v}")
        return v

    @field_validator("profile_id")
    @classmethod
    def validate_profile_id(cls, v: str | None) -> str | None:
        """Validate profile_id is valid UUID format if provided."""
        if v is not None:
            try:
                uuid.UUID(v)
            except ValueError:
                raise ValueError(f"Invalid UUID format: {v}")
        return v


class DeviceProvisioningService:
    """Service for provisioning devices with unique credentials.

    Handles both access token and X.509 certificate credential types.
    Creates IoTDevice and DeviceCredentials records in a single transaction.
    """

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: SQLAlchemy async session
        """
        self.db = db

    async def provision_device(
        self,
        name: str,
        device_type: str,
        building_id: uuid.UUID,
        agency_id: uuid.UUID,
        credential_type: str = "access_token",
        profile_id: uuid.UUID | None = None,
        **kwargs
    ) -> tuple[IoTDevice, dict]:
        """Provision a new device with unique credentials.

        Creates IoTDevice record with provisioning_status=pending and generates
        credentials (access token or X.509 certificate) stored in DeviceCredentials.

        Args:
            name: Device name (1-200 chars)
            device_type: Device type (microphone, camera, sensor, gateway)
            building_id: UUID of building where device is located
            agency_id: UUID of agency owning the device (for validation)
            credential_type: "access_token" or "x509" (default: access_token)
            profile_id: Optional device profile UUID
            **kwargs: Additional device fields (serial_number, manufacturer, model, etc.)

        Returns:
            Tuple of (device, credentials_dict) where credentials_dict contains
            one-time secrets that must be returned to admin immediately.

        Raises:
            DeviceProvisioningError: If building not found, agency mismatch,
                profile not found, or credential generation fails
        """
        # Validate building exists and belongs to agency
        result = await self.db.execute(
            select(Building).where(Building.id == building_id)
        )
        building = result.scalar_one_or_none()

        if not building:
            raise DeviceProvisioningError(
                f"Building {building_id} not found"
            )

        if building.agency_id != agency_id:
            raise DeviceProvisioningError(
                f"Building {building_id} does not belong to agency {agency_id}"
            )

        # Validate profile_id if provided
        if profile_id:
            result = await self.db.execute(
                select(DeviceProfile).where(DeviceProfile.id == profile_id)
            )
            profile = result.scalar_one_or_none()

            if not profile:
                raise DeviceProvisioningError(
                    f"Device profile {profile_id} not found"
                )

        # Create IoTDevice record
        device = IoTDevice(
            id=uuid.uuid4(),
            name=name,
            device_type=device_type,
            building_id=building_id,
            profile_id=profile_id,
            provisioning_status="pending",
            status="offline",
            **kwargs  # serial_number, manufacturer, model, etc.
        )
        self.db.add(device)

        # Generate credentials based on type
        credentials_dict = {}

        if credential_type == "access_token":
            # Generate cryptographically secure access token
            access_token = secrets.token_urlsafe(32)  # 256 bits
            token_hash = pwd_context.hash(access_token)

            # Create DeviceCredentials record with hashed token
            credentials = DeviceCredentials(
                id=uuid.uuid4(),
                device_id=device.id,
                credential_type=CredentialType.ACCESS_TOKEN.value,
                access_token_hash=token_hash,
                is_active=True,
            )
            self.db.add(credentials)

            # Return plaintext token ONCE (never stored, never retrievable)
            credentials_dict = {
                "access_token": access_token,
                "credential_type": "access_token",
            }

        elif credential_type == "x509":
            try:
                # Initialize Certificate Authority
                ca = CertificateAuthority(
                    ca_cert_path=settings.ca_cert_path,
                    ca_key_path=settings.ca_key_path,
                )

                # Generate device certificate
                cert_pem, key_pem = ca.generate_device_certificate(
                    device_id=str(device.id),
                    agency_id=str(agency_id),
                    validity_days=365,
                )

                # Parse certificate to get expiry date
                from cryptography import x509
                cert = x509.load_pem_x509_certificate(cert_pem)
                certificate_expiry = cert.not_valid_after_utc

                # Create DeviceCredentials record with certificate
                credentials = DeviceCredentials(
                    id=uuid.uuid4(),
                    device_id=device.id,
                    credential_type=CredentialType.X509.value,
                    certificate_pem=cert_pem.decode("utf-8"),
                    certificate_cn=f"device_{device.id}",
                    certificate_expiry=certificate_expiry,
                    is_active=True,
                )
                self.db.add(credentials)

                # Return certificate and private key (base64-encoded for JSON transport)
                credentials_dict = {
                    "certificate_pem": base64.b64encode(cert_pem).decode("utf-8"),
                    "private_key_pem": base64.b64encode(key_pem).decode("utf-8"),
                    "certificate_cn": f"device_{device.id}",
                    "certificate_expiry": certificate_expiry.isoformat(),
                    "credential_type": "x509",
                }

            except CertificateAuthorityError as e:
                raise DeviceProvisioningError(
                    f"Failed to generate X.509 certificate: {e}"
                )

        else:
            raise DeviceProvisioningError(
                f"Invalid credential_type: {credential_type}. "
                f"Must be 'access_token' or 'x509'"
            )

        # Commit transaction
        await self.db.commit()
        await self.db.refresh(device)
        await self.db.refresh(credentials)

        return device, credentials_dict

    async def revoke_credentials(
        self,
        device_id: uuid.UUID,
        agency_id: uuid.UUID,
    ) -> DeviceCredentials:
        """Revoke device credentials and suspend device.

        Sets DeviceCredentials.is_active=False and device.provisioning_status=suspended.
        Revoked devices will be rejected on next MQTT auth attempt (within 2h session expiry).

        Args:
            device_id: UUID of device to revoke
            agency_id: UUID of agency (for authorization check)

        Returns:
            Updated DeviceCredentials record

        Raises:
            DeviceProvisioningError: If device not found, wrong agency, or already revoked
        """
        # Query device credentials with joins
        result = await self.db.execute(
            select(DeviceCredentials, IoTDevice, Building)
            .join(IoTDevice, DeviceCredentials.device_id == IoTDevice.id)
            .join(Building, IoTDevice.building_id == Building.id)
            .where(DeviceCredentials.device_id == device_id)
        )
        row = result.one_or_none()

        if not row:
            raise DeviceProvisioningError(f"Device {device_id} not found or not provisioned")

        credentials, device, building = row

        # Verify agency ownership
        if building.agency_id != agency_id:
            raise DeviceProvisioningError(f"Device {device_id} does not belong to agency {agency_id}")

        # Check if already revoked
        if not credentials.is_active:
            raise DeviceProvisioningError(f"Credentials for device {device_id} are already revoked")

        # Revoke credentials
        credentials.is_active = False
        device.provisioning_status = "suspended"

        await self.db.commit()
        await self.db.refresh(credentials)

        return credentials

    async def reactivate_credentials(
        self,
        device_id: uuid.UUID,
        agency_id: uuid.UUID,
    ) -> DeviceCredentials:
        """Reactivate previously revoked device credentials.

        Sets DeviceCredentials.is_active=True and device.provisioning_status=active.
        Note: Sets status to "active" not "pending" since device was previously activated.

        Args:
            device_id: UUID of device to reactivate
            agency_id: UUID of agency (for authorization check)

        Returns:
            Updated DeviceCredentials record

        Raises:
            DeviceProvisioningError: If device not found, wrong agency, or already active
        """
        # Query device credentials with joins
        result = await self.db.execute(
            select(DeviceCredentials, IoTDevice, Building)
            .join(IoTDevice, DeviceCredentials.device_id == IoTDevice.id)
            .join(Building, IoTDevice.building_id == Building.id)
            .where(DeviceCredentials.device_id == device_id)
        )
        row = result.one_or_none()

        if not row:
            raise DeviceProvisioningError(f"Device {device_id} not found or not provisioned")

        credentials, device, building = row

        # Verify agency ownership
        if building.agency_id != agency_id:
            raise DeviceProvisioningError(f"Device {device_id} does not belong to agency {agency_id}")

        # Check if already active
        if credentials.is_active:
            raise DeviceProvisioningError(f"Credentials for device {device_id} are already active")

        # Reactivate credentials
        credentials.is_active = True
        device.provisioning_status = "active"  # Not "pending" - device was previously activated

        await self.db.commit()
        await self.db.refresh(credentials)

        return credentials

    async def bulk_provision_devices(
        self,
        csv_content: str,
        agency_id: uuid.UUID,
    ) -> list[dict]:
        """Provision multiple devices from CSV content.

        Args:
            csv_content: CSV file content as string
            agency_id: UUID of agency owning the devices

        Returns:
            List of per-row results with status (success/error), device_id, or error message

        Raises:
            DeviceProvisioningError: If CSV has missing required headers or exceeds row limit
        """
        # Parse CSV
        reader = csv.DictReader(StringIO(csv_content))

        # Validate required headers
        required_headers = {"name", "device_type", "building_id"}
        if reader.fieldnames is None:
            raise DeviceProvisioningError("CSV file is empty or has no headers")

        actual_headers = set(reader.fieldnames)
        missing_headers = required_headers - actual_headers
        if missing_headers:
            raise DeviceProvisioningError(
                f"Missing required CSV headers: {', '.join(sorted(missing_headers))}"
            )

        # Collect all rows first to check row count limit
        rows = list(reader)
        if len(rows) > 1000:
            raise DeviceProvisioningError(
                f"CSV exceeds maximum of 1000 rows (found {len(rows)} rows)"
            )

        # Process each row
        results = []
        for row_num, row in enumerate(rows, start=2):  # Start at 2 to account for header
            try:
                # Validate row with Pydantic
                validated_row = DeviceProvisionRow(**row)

                # Provision device
                device, credentials = await self.provision_device(
                    name=validated_row.name,
                    device_type=validated_row.device_type,
                    building_id=uuid.UUID(validated_row.building_id),
                    agency_id=agency_id,
                    credential_type=validated_row.credential_type,
                    profile_id=uuid.UUID(validated_row.profile_id) if validated_row.profile_id else None,
                )

                # Append success result (no credentials for security)
                results.append({
                    "row": row_num,
                    "status": "success",
                    "device_id": str(device.id),
                    "name": validated_row.name,
                    "credential_type": validated_row.credential_type,
                })

            except Exception as e:
                # Append error result and continue to next row
                results.append({
                    "row": row_num,
                    "status": "error",
                    "error": str(e),
                })

        return results
