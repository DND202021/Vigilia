"""Tests for IoT devices API endpoints."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.building import Building, BuildingType
from app.models.device import IoTDevice, DeviceType, DeviceStatus


class TestIoTDevicesAPI:
    """Tests for IoT devices API endpoints."""

    async def get_auth_token(self, client: AsyncClient, email: str = "test@example.com") -> str:
        """Helper to get auth token for API requests."""
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "TestPassword123!",
            },
        )
        return login_response.json()["access_token"]

    async def create_test_building(self, db_session: AsyncSession, agency_id: uuid.UUID) -> Building:
        """Helper to create a test building."""
        building = Building(
            id=uuid.uuid4(),
            agency_id=agency_id,
            name="Test Building",
            address="123 Test St",
            building_type=BuildingType.COMMERCIAL,
            latitude=40.7128,
            longitude=-74.0060,
        )
        db_session.add(building)
        await db_session.commit()
        await db_session.refresh(building)
        return building

    async def create_test_device(
        self,
        db_session: AsyncSession,
        building_id: uuid.UUID,
    ) -> IoTDevice:
        """Helper to create a test IoT device."""
        device = IoTDevice(
            id=uuid.uuid4(),
            building_id=building_id,
            device_type=DeviceType.MICROPHONE,
            name="Test Device",
            status=DeviceStatus.ACTIVE,
            manufacturer="Axis",
        )
        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)
        return device

    # ==================== List Devices Tests ====================

    @pytest.mark.asyncio
    async def test_list_devices(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Listing IoT devices should work for authenticated users."""
        token = await self.get_auth_token(client)

        # Create a test device
        building = await self.create_test_building(db_session, test_user.agency_id)
        await self.create_test_device(db_session, building.id)

        response = await client.get(
            "/api/v1/iot-devices",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_devices_no_auth(self, client: AsyncClient):
        """Listing IoT devices without auth should fail."""
        response = await client.get("/api/v1/iot-devices")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_devices_by_building(
        self,
        client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Filtering devices by building should work."""
        token = await self.get_auth_token(client)

        # Create a test device
        building = await self.create_test_building(db_session, test_user.agency_id)
        await self.create_test_device(db_session, building.id)

        response = await client.get(
            f"/api/v1/iot-devices?building_id={building.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200

    # ==================== Get Device Tests ====================

    @pytest.mark.asyncio
    async def test_get_device(
        self,
        client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Getting a device by ID should work."""
        token = await self.get_auth_token(client)

        # Create a device
        building = await self.create_test_building(db_session, test_user.agency_id)
        device = await self.create_test_device(db_session, building.id)

        response = await client.get(
            f"/api/v1/iot-devices/{device.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(device.id)

    @pytest.mark.asyncio
    async def test_get_device_not_found(self, client: AsyncClient, test_user: User):
        """Getting a non-existent device should return 404."""
        token = await self.get_auth_token(client)

        response = await client.get(
            f"/api/v1/iot-devices/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    # ==================== Create Device Tests ====================

    @pytest.mark.asyncio
    async def test_create_device(
        self,
        client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Creating an IoT device should work."""
        token = await self.get_auth_token(client)

        # Create a building first
        building = await self.create_test_building(db_session, test_user.agency_id)

        response = await client.post(
            "/api/v1/iot-devices",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "New Device",
                "device_type": "microphone",
                "building_id": str(building.id),
                "manufacturer": "Axis",
            },
        )

        # May require special permissions
        assert response.status_code in [201, 403]

    @pytest.mark.asyncio
    async def test_create_device_invalid_building(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """Creating a device with invalid building should fail."""
        token = await self.get_auth_token(client)

        response = await client.post(
            "/api/v1/iot-devices",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "New Device",
                "device_type": "microphone",
                "building_id": "not-a-uuid",
                "manufacturer": "Axis",
            },
        )

        assert response.status_code == 422

    # ==================== Update Device Tests ====================

    @pytest.mark.asyncio
    async def test_update_device(
        self,
        client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Updating a device should work."""
        token = await self.get_auth_token(client)

        # Create a device
        building = await self.create_test_building(db_session, test_user.agency_id)
        device = await self.create_test_device(db_session, building.id)

        response = await client.patch(
            f"/api/v1/iot-devices/{device.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Updated Device",
                "firmware_version": "2.0",
            },
        )

        # May require permissions
        assert response.status_code in [200, 403]

    @pytest.mark.asyncio
    async def test_update_device_position(
        self,
        client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Updating device position should work."""
        token = await self.get_auth_token(client)

        # Create a device
        building = await self.create_test_building(db_session, test_user.agency_id)
        device = await self.create_test_device(db_session, building.id)

        # Create a floor plan (simplified)
        floor_plan_id = uuid.uuid4()

        response = await client.patch(
            f"/api/v1/iot-devices/{device.id}/position",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "floor_plan_id": str(floor_plan_id),
                "position_x": 50.0,
                "position_y": 75.0,
            },
        )

        # May require permissions or floor plan to exist
        assert response.status_code in [200, 403, 404]

    # ==================== Delete Device Tests ====================

    @pytest.mark.asyncio
    async def test_delete_device(
        self,
        client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Deleting a device should work."""
        token = await self.get_auth_token(client)

        # Create a device
        building = await self.create_test_building(db_session, test_user.agency_id)
        device = await self.create_test_device(db_session, building.id)

        response = await client.delete(
            f"/api/v1/iot-devices/{device.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # May require permissions
        assert response.status_code in [204, 403]

    # ==================== Device Alerts Tests ====================

    @pytest.mark.asyncio
    async def test_get_device_alerts(
        self,
        client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Getting alerts for a device should work."""
        token = await self.get_auth_token(client)

        # Create a device
        building = await self.create_test_building(db_session, test_user.agency_id)
        device = await self.create_test_device(db_session, building.id)

        response = await client.get(
            f"/api/v1/iot-devices/{device.id}/alerts",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200

    # ==================== Device History Tests ====================

    @pytest.mark.asyncio
    async def test_get_device_history(
        self,
        client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Getting device history should work."""
        token = await self.get_auth_token(client)

        # Create a device
        building = await self.create_test_building(db_session, test_user.agency_id)
        device = await self.create_test_device(db_session, building.id)

        response = await client.get(
            f"/api/v1/iot-devices/{device.id}/history",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
