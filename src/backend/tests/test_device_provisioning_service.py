"""Tests for DeviceProvisioningService."""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building, BuildingType
from app.models.device import IoTDevice
from app.models.device_profile import DeviceProfile
from app.models.device_credentials import DeviceCredentials, CredentialType
from app.models.agency import Agency
from app.services.device_provisioning_service import (
    DeviceProvisioningService,
    DeviceProvisioningError,
    DeviceProvisionRow,
)


class TestDeviceProvisionRow:
    """Tests for DeviceProvisionRow validation."""

    def test_valid_row(self):
        """Test valid provision row."""
        row = DeviceProvisionRow(
            name="Test Device",
            device_type="sensor",
            building_id=str(uuid.uuid4()),
        )
        assert row.name == "Test Device"
        assert row.device_type == "sensor"
        assert row.credential_type == "access_token"

    def test_valid_row_with_profile(self):
        """Test valid provision row with profile."""
        profile_id = str(uuid.uuid4())
        row = DeviceProvisionRow(
            name="Test Device",
            device_type="camera",
            building_id=str(uuid.uuid4()),
            profile_id=profile_id,
            credential_type="x509",
        )
        assert row.profile_id == profile_id
        assert row.credential_type == "x509"

    def test_invalid_building_id(self):
        """Test invalid building ID format."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            DeviceProvisionRow(
                name="Test Device",
                device_type="sensor",
                building_id="not-a-uuid",
            )

    def test_invalid_profile_id(self):
        """Test invalid profile ID format."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            DeviceProvisionRow(
                name="Test Device",
                device_type="sensor",
                building_id=str(uuid.uuid4()),
                profile_id="not-a-uuid",
            )

    def test_invalid_device_type(self):
        """Test invalid device type."""
        with pytest.raises(ValueError):
            DeviceProvisionRow(
                name="Test Device",
                device_type="invalid_type",
                building_id=str(uuid.uuid4()),
            )

    def test_invalid_credential_type(self):
        """Test invalid credential type."""
        with pytest.raises(ValueError):
            DeviceProvisionRow(
                name="Test Device",
                device_type="sensor",
                building_id=str(uuid.uuid4()),
                credential_type="invalid",
            )

    def test_empty_name(self):
        """Test empty name validation."""
        with pytest.raises(ValueError):
            DeviceProvisionRow(
                name="",
                device_type="sensor",
                building_id=str(uuid.uuid4()),
            )


class TestDeviceProvisioningService:
    """Tests for DeviceProvisioningService."""

    @pytest.fixture
    def agency_id(self):
        """Create test agency ID."""
        return uuid.uuid4()

    @pytest.mark.asyncio
    async def test_provision_device_access_token(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Test provisioning device with access token credentials."""
        # Create building
        building = Building(
            id=uuid.uuid4(),
            name="Test Building",
            building_type=BuildingType.COMMERCIAL,
            street_name="Test St",
            city="Montreal",
            province_state="Quebec",
            full_address="123 Test St, Montreal, Quebec",
            latitude=45.5017,
            longitude=-73.5673,
            agency_id=test_agency.id,
        )
        db_session.add(building)
        await db_session.commit()

        service = DeviceProvisioningService(db_session)

        device, credentials = await service.provision_device(
            name="Sensor 001",
            device_type="sensor",
            building_id=building.id,
            agency_id=test_agency.id,
            credential_type="access_token",
        )

        assert device is not None
        assert device.name == "Sensor 001"
        assert device.device_type == "sensor"
        assert device.provisioning_status == "pending"
        assert device.status == "offline"

        assert credentials is not None
        assert credentials["credential_type"] == "access_token"
        assert "access_token" in credentials
        assert len(credentials["access_token"]) > 32  # URL-safe base64

    @pytest.mark.asyncio
    async def test_provision_device_with_profile(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Test provisioning device with profile."""
        # Create building
        building = Building(
            id=uuid.uuid4(),
            name="Test Building",
            building_type=BuildingType.COMMERCIAL,
            street_name="Test St",
            city="Montreal",
            province_state="Quebec",
            full_address="123 Test St, Montreal, Quebec",
            latitude=45.5017,
            longitude=-73.5673,
            agency_id=test_agency.id,
        )
        db_session.add(building)

        # Create profile
        profile = DeviceProfile(
            id=uuid.uuid4(),
            name="Sensor Profile",
            device_type="sensor",
            alert_rules=[
                {"name": "High Temp", "metric": "temperature", "condition": "gt", "threshold": 80}
            ],
        )
        db_session.add(profile)
        await db_session.commit()

        service = DeviceProvisioningService(db_session)

        device, credentials = await service.provision_device(
            name="Sensor 002",
            device_type="sensor",
            building_id=building.id,
            agency_id=test_agency.id,
            profile_id=profile.id,
        )

        assert device.profile_id == profile.id

    @pytest.mark.asyncio
    async def test_provision_device_building_not_found(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Test provisioning with non-existent building."""
        service = DeviceProvisioningService(db_session)

        with pytest.raises(DeviceProvisioningError, match="Building .* not found"):
            await service.provision_device(
                name="Sensor 003",
                device_type="sensor",
                building_id=uuid.uuid4(),
                agency_id=test_agency.id,
            )

    @pytest.mark.asyncio
    async def test_provision_device_wrong_agency(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Test provisioning with building from different agency."""
        # Create building for different agency
        other_agency_id = uuid.uuid4()
        building = Building(
            id=uuid.uuid4(),
            name="Other Agency Building",
            building_type=BuildingType.COMMERCIAL,
            street_name="Other St",
            city="Montreal",
            province_state="Quebec",
            full_address="456 Other St, Montreal, Quebec",
            latitude=45.5017,
            longitude=-73.5673,
            agency_id=other_agency_id,
        )
        db_session.add(building)
        await db_session.commit()

        service = DeviceProvisioningService(db_session)

        with pytest.raises(DeviceProvisioningError, match="does not belong to agency"):
            await service.provision_device(
                name="Sensor 004",
                device_type="sensor",
                building_id=building.id,
                agency_id=test_agency.id,
            )

    @pytest.mark.asyncio
    async def test_provision_device_profile_not_found(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Test provisioning with non-existent profile."""
        building = Building(
            id=uuid.uuid4(),
            name="Test Building",
            building_type=BuildingType.COMMERCIAL,
            street_name="Test St",
            city="Montreal",
            province_state="Quebec",
            full_address="123 Test St, Montreal, Quebec",
            latitude=45.5017,
            longitude=-73.5673,
            agency_id=test_agency.id,
        )
        db_session.add(building)
        await db_session.commit()

        service = DeviceProvisioningService(db_session)

        with pytest.raises(DeviceProvisioningError, match="Device profile .* not found"):
            await service.provision_device(
                name="Sensor 005",
                device_type="sensor",
                building_id=building.id,
                agency_id=test_agency.id,
                profile_id=uuid.uuid4(),
            )

    @pytest.mark.asyncio
    async def test_provision_device_invalid_credential_type(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Test provisioning with invalid credential type."""
        building = Building(
            id=uuid.uuid4(),
            name="Test Building",
            building_type=BuildingType.COMMERCIAL,
            street_name="Test St",
            city="Montreal",
            province_state="Quebec",
            full_address="123 Test St, Montreal, Quebec",
            latitude=45.5017,
            longitude=-73.5673,
            agency_id=test_agency.id,
        )
        db_session.add(building)
        await db_session.commit()

        service = DeviceProvisioningService(db_session)

        with pytest.raises(DeviceProvisioningError, match="Invalid credential_type"):
            await service.provision_device(
                name="Sensor 006",
                device_type="sensor",
                building_id=building.id,
                agency_id=test_agency.id,
                credential_type="invalid",
            )

    @pytest.mark.asyncio
    async def test_revoke_credentials(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Test revoking device credentials."""
        # Create building and device
        building = Building(
            id=uuid.uuid4(),
            name="Test Building",
            building_type=BuildingType.COMMERCIAL,
            street_name="Test St",
            city="Montreal",
            province_state="Quebec",
            full_address="123 Test St, Montreal, Quebec",
            latitude=45.5017,
            longitude=-73.5673,
            agency_id=test_agency.id,
        )
        db_session.add(building)
        await db_session.flush()

        service = DeviceProvisioningService(db_session)

        # Provision device
        device, _ = await service.provision_device(
            name="Device to Revoke",
            device_type="sensor",
            building_id=building.id,
            agency_id=test_agency.id,
        )

        # Revoke credentials
        credentials = await service.revoke_credentials(
            device_id=device.id,
            agency_id=test_agency.id,
        )

        assert credentials.is_active is False

        # Verify device status
        await db_session.refresh(device)
        assert device.provisioning_status == "suspended"

    @pytest.mark.asyncio
    async def test_revoke_credentials_device_not_found(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Test revoking credentials for non-existent device."""
        service = DeviceProvisioningService(db_session)

        with pytest.raises(DeviceProvisioningError, match="not found or not provisioned"):
            await service.revoke_credentials(
                device_id=uuid.uuid4(),
                agency_id=test_agency.id,
            )

    @pytest.mark.asyncio
    async def test_revoke_credentials_already_revoked(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Test revoking already revoked credentials."""
        building = Building(
            id=uuid.uuid4(),
            name="Test Building",
            building_type=BuildingType.COMMERCIAL,
            street_name="Test St",
            city="Montreal",
            province_state="Quebec",
            full_address="123 Test St, Montreal, Quebec",
            latitude=45.5017,
            longitude=-73.5673,
            agency_id=test_agency.id,
        )
        db_session.add(building)
        await db_session.flush()

        service = DeviceProvisioningService(db_session)

        # Provision and revoke
        device, _ = await service.provision_device(
            name="Already Revoked Device",
            device_type="sensor",
            building_id=building.id,
            agency_id=test_agency.id,
        )
        await service.revoke_credentials(device.id, test_agency.id)

        # Try to revoke again
        with pytest.raises(DeviceProvisioningError, match="already revoked"):
            await service.revoke_credentials(device.id, test_agency.id)

    @pytest.mark.asyncio
    async def test_reactivate_credentials(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Test reactivating revoked credentials."""
        building = Building(
            id=uuid.uuid4(),
            name="Test Building",
            building_type=BuildingType.COMMERCIAL,
            street_name="Test St",
            city="Montreal",
            province_state="Quebec",
            full_address="123 Test St, Montreal, Quebec",
            latitude=45.5017,
            longitude=-73.5673,
            agency_id=test_agency.id,
        )
        db_session.add(building)
        await db_session.flush()

        service = DeviceProvisioningService(db_session)

        # Provision and revoke
        device, _ = await service.provision_device(
            name="Device to Reactivate",
            device_type="sensor",
            building_id=building.id,
            agency_id=test_agency.id,
        )
        await service.revoke_credentials(device.id, test_agency.id)

        # Reactivate
        credentials = await service.reactivate_credentials(
            device_id=device.id,
            agency_id=test_agency.id,
        )

        assert credentials.is_active is True

        # Verify device status
        await db_session.refresh(device)
        assert device.provisioning_status == "active"

    @pytest.mark.asyncio
    async def test_reactivate_already_active(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Test reactivating already active credentials."""
        building = Building(
            id=uuid.uuid4(),
            name="Test Building",
            building_type=BuildingType.COMMERCIAL,
            street_name="Test St",
            city="Montreal",
            province_state="Quebec",
            full_address="123 Test St, Montreal, Quebec",
            latitude=45.5017,
            longitude=-73.5673,
            agency_id=test_agency.id,
        )
        db_session.add(building)
        await db_session.flush()

        service = DeviceProvisioningService(db_session)

        # Provision without revoking
        device, _ = await service.provision_device(
            name="Active Device",
            device_type="sensor",
            building_id=building.id,
            agency_id=test_agency.id,
        )

        # Try to reactivate (already active)
        with pytest.raises(DeviceProvisioningError, match="already active"):
            await service.reactivate_credentials(device.id, test_agency.id)

    @pytest.mark.asyncio
    async def test_bulk_provision_devices(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Test bulk device provisioning from CSV."""
        # Create building
        building = Building(
            id=uuid.uuid4(),
            name="Test Building",
            building_type=BuildingType.COMMERCIAL,
            street_name="Test St",
            city="Montreal",
            province_state="Quebec",
            full_address="123 Test St, Montreal, Quebec",
            latitude=45.5017,
            longitude=-73.5673,
            agency_id=test_agency.id,
        )
        db_session.add(building)
        await db_session.commit()

        csv_content = f"""name,device_type,building_id,credential_type
Sensor 001,sensor,{building.id},access_token
Camera 001,camera,{building.id},access_token
Gateway 001,gateway,{building.id},access_token
"""

        service = DeviceProvisioningService(db_session)
        results = await service.bulk_provision_devices(csv_content, test_agency.id)

        assert len(results) == 3
        assert all(r["status"] == "success" for r in results)
        assert results[0]["name"] == "Sensor 001"
        assert results[1]["name"] == "Camera 001"
        assert results[2]["name"] == "Gateway 001"

    @pytest.mark.asyncio
    async def test_bulk_provision_missing_headers(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Test bulk provisioning with missing CSV headers."""
        csv_content = """name,device_type
Sensor,sensor
"""

        service = DeviceProvisioningService(db_session)

        with pytest.raises(DeviceProvisioningError, match="Missing required CSV headers"):
            await service.bulk_provision_devices(csv_content, test_agency.id)

    @pytest.mark.asyncio
    async def test_bulk_provision_empty_csv(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Test bulk provisioning with empty CSV."""
        csv_content = ""

        service = DeviceProvisioningService(db_session)

        with pytest.raises(DeviceProvisioningError, match="empty or has no headers"):
            await service.bulk_provision_devices(csv_content, test_agency.id)

    @pytest.mark.asyncio
    async def test_bulk_provision_exceeds_limit(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Test bulk provisioning with too many rows."""
        building_id = uuid.uuid4()
        # Generate 1001 rows (exceeds 1000 limit)
        rows = ["name,device_type,building_id"]
        for i in range(1001):
            rows.append(f"Sensor{i},sensor,{building_id}")
        csv_content = "\n".join(rows)

        service = DeviceProvisioningService(db_session)

        with pytest.raises(DeviceProvisioningError, match="exceeds maximum of 1000 rows"):
            await service.bulk_provision_devices(csv_content, test_agency.id)

    @pytest.mark.asyncio
    async def test_bulk_provision_mixed_results(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Test bulk provisioning with some valid and some invalid rows."""
        building = Building(
            id=uuid.uuid4(),
            name="Test Building",
            building_type=BuildingType.COMMERCIAL,
            street_name="Test St",
            city="Montreal",
            province_state="Quebec",
            full_address="123 Test St, Montreal, Quebec",
            latitude=45.5017,
            longitude=-73.5673,
            agency_id=test_agency.id,
        )
        db_session.add(building)
        await db_session.commit()

        csv_content = f"""name,device_type,building_id,credential_type
Sensor OK,sensor,{building.id},access_token
Invalid Building,sensor,{uuid.uuid4()},access_token
Sensor OK 2,sensor,{building.id},access_token
"""

        service = DeviceProvisioningService(db_session)
        results = await service.bulk_provision_devices(csv_content, test_agency.id)

        assert len(results) == 3
        assert results[0]["status"] == "success"
        assert results[1]["status"] == "error"
        assert "not found" in results[1]["error"]
        assert results[2]["status"] == "success"
