"""Device provisioning service for generating credentials and registering devices."""

import base64
import secrets
import uuid
from datetime import datetime, timezone

from passlib.context import CryptContext
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
