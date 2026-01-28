"""Tests for IoT devices API endpoints."""

import pytest
import uuid
from httpx import AsyncClient

from app.models.user import User
from app.models.agency import Agency
from app.models.building import Building


class TestIoTDevicesAPI:
    """Tests for IoT devices API endpoints."""

    async def get_admin_token(self, client: AsyncClient) -> str:
        """Helper to get admin auth token for API requests."""
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "AdminPassword123!",
            },
        )
        return login_response.json()["access_token"]

    async def create_test_building(
        self, client: AsyncClient, token: str, name: str = "Test Building"
    ) -> str:
        """Helper to create a building for device tests."""
        response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": name,
                "street_name": "Device Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
            },
        )
        return response.json()["id"]

    async def create_test_device(
        self,
        client: AsyncClient,
        token: str,
        building_id: str,
        name: str = "Test Device",
        device_type: str = "microphone",
    ) -> dict:
        """Helper to create a device for tests."""
        response = await client.post(
            "/api/v1/iot-devices",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": name,
                "device_type": device_type,
                "building_id": building_id,
                "serial_number": f"SN-{uuid.uuid4().hex[:8].upper()}",
                "ip_address": "192.168.1.100",
                "manufacturer": "Axis",
            },
        )
        return response.json()

    # ==================== List Devices ====================

    @pytest.mark.asyncio
    async def test_list_iot_devices(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """GET /api/v1/iot-devices returns paginated list."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create multiple devices
        for i in range(3):
            await self.create_test_device(
                client, token, building_id, name=f"Device {i}"
            )

        # List devices
        response = await client.get(
            "/api/v1/iot-devices",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert len(data["items"]) >= 3
        assert data["total"] >= 3

    @pytest.mark.asyncio
    async def test_list_iot_devices_filter_building(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Filter IoT devices by building_id."""
        token = await self.get_admin_token(client)

        # Create two buildings
        building1_id = await self.create_test_building(
            client, token, name="Building 1"
        )
        building2_id = await self.create_test_building(
            client, token, name="Building 2"
        )

        # Create devices in each building
        await self.create_test_device(
            client, token, building1_id, name="B1 Device"
        )
        await self.create_test_device(
            client, token, building2_id, name="B2 Device"
        )

        # Filter by building1
        response = await client.get(
            f"/api/v1/iot-devices?building_id={building1_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1
        for item in data["items"]:
            assert item["building_id"] == building1_id

    @pytest.mark.asyncio
    async def test_list_iot_devices_filter_type(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Filter IoT devices by device_type."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create devices of different types
        await self.create_test_device(
            client, token, building_id, name="Microphone 1", device_type="microphone"
        )
        await self.create_test_device(
            client, token, building_id, name="Camera 1", device_type="camera"
        )

        # Filter by microphone
        response = await client.get(
            "/api/v1/iot-devices?device_type=microphone",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["device_type"] == "microphone"

    @pytest.mark.asyncio
    async def test_list_iot_devices_filter_status(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Filter IoT devices by status."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create a device (default status is 'offline')
        await self.create_test_device(client, token, building_id)

        # Filter by offline status
        response = await client.get(
            "/api/v1/iot-devices?status=offline",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["status"] == "offline"

    # ==================== Get Device ====================

    @pytest.mark.asyncio
    async def test_get_iot_device(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """GET /api/v1/iot-devices/{id} returns device details."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)
        device = await self.create_test_device(
            client, token, building_id, name="Get Test Device"
        )

        # Get the device
        response = await client.get(
            f"/api/v1/iot-devices/{device['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == device["id"]
        assert data["name"] == "Get Test Device"
        assert data["building_id"] == building_id

    @pytest.mark.asyncio
    async def test_get_iot_device_not_found(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """GET /api/v1/iot-devices/{id} returns 404 for non-existent device."""
        token = await self.get_admin_token(client)

        response = await client.get(
            "/api/v1/iot-devices/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    # ==================== Create Device ====================

    @pytest.mark.asyncio
    async def test_create_iot_device(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """POST /api/v1/iot-devices creates a new device."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.post(
            "/api/v1/iot-devices",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "New Microphone",
                "device_type": "microphone",
                "building_id": building_id,
                "serial_number": "SN-12345678",
                "ip_address": "192.168.1.50",
                "mac_address": "AA:BB:CC:DD:EE:FF",
                "model": "AXIS M12-E",
                "firmware_version": "10.12.114",
                "manufacturer": "Axis",
                "latitude": 45.5017,
                "longitude": -73.5673,
                "location_name": "Main Lobby",
                "config": {"sensitivity": 0.8},
                "capabilities": ["audio_detection", "noise_level"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Microphone"
        assert data["device_type"] == "microphone"
        assert data["building_id"] == building_id
        assert data["serial_number"] == "SN-12345678"
        assert data["ip_address"] == "192.168.1.50"
        assert data["mac_address"] == "AA:BB:CC:DD:EE:FF"
        assert data["manufacturer"] == "Axis"
        assert data["status"] == "offline"  # Default status
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_iot_device_invalid_type(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """POST /api/v1/iot-devices returns 400 for invalid device_type."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.post(
            "/api/v1/iot-devices",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Invalid Device",
                "device_type": "invalid_type",
                "building_id": building_id,
            },
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    # ==================== Update Device ====================

    @pytest.mark.asyncio
    async def test_update_iot_device(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """PATCH /api/v1/iot-devices/{id} updates device."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)
        device = await self.create_test_device(
            client, token, building_id, name="Update Test Device"
        )

        # Update the device
        response = await client.patch(
            f"/api/v1/iot-devices/{device['id']}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Updated Device Name",
                "firmware_version": "11.0.0",
                "location_name": "Second Floor",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Device Name"
        assert data["firmware_version"] == "11.0.0"
        assert data["location_name"] == "Second Floor"

    @pytest.mark.asyncio
    async def test_update_iot_device_not_found(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """PATCH /api/v1/iot-devices/{id} returns 404 for non-existent device."""
        token = await self.get_admin_token(client)

        response = await client.patch(
            "/api/v1/iot-devices/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Updated Name"},
        )

        assert response.status_code == 404

    # ==================== Delete Device ====================

    @pytest.mark.asyncio
    async def test_delete_iot_device(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """DELETE /api/v1/iot-devices/{id} returns 204."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)
        device = await self.create_test_device(
            client, token, building_id, name="Delete Test Device"
        )

        # Delete the device
        response = await client.delete(
            f"/api/v1/iot-devices/{device['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 204

        # Verify it's gone
        get_response = await client.get(
            f"/api/v1/iot-devices/{device['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_iot_device_not_found(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """DELETE /api/v1/iot-devices/{id} returns 404 for non-existent device."""
        token = await self.get_admin_token(client)

        response = await client.delete(
            "/api/v1/iot-devices/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    # ==================== Position Update ====================

    @pytest.mark.asyncio
    async def test_update_device_position(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """PATCH /api/v1/iot-devices/{id}/position updates device position."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)
        device = await self.create_test_device(
            client, token, building_id, name="Position Test Device"
        )

        # Create a floor plan
        floor_response = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={"floor_number": 1, "floor_name": "Ground Floor"},
        )
        floor_plan_id = floor_response.json()["id"]

        # Update position
        response = await client.patch(
            f"/api/v1/iot-devices/{device['id']}/position",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "floor_plan_id": floor_plan_id,
                "position_x": 50.5,
                "position_y": 75.3,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["floor_plan_id"] == floor_plan_id
        assert data["position_x"] == 50.5
        assert data["position_y"] == 75.3

    # ==================== Config Update ====================

    @pytest.mark.asyncio
    async def test_update_device_config(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """PATCH /api/v1/iot-devices/{id}/config updates device configuration."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)
        device = await self.create_test_device(
            client, token, building_id, name="Config Test Device"
        )

        # Update config
        new_config = {
            "sensitivity": 0.9,
            "threshold": 80,
            "detection_types": ["gunshot", "glass_break", "scream"],
        }

        response = await client.patch(
            f"/api/v1/iot-devices/{device['id']}/config",
            headers={"Authorization": f"Bearer {token}"},
            json={"config": new_config},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["config"] == new_config

    # ==================== Device Status ====================

    @pytest.mark.asyncio
    async def test_get_device_status(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """GET /api/v1/iot-devices/{id}/status returns device status."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)
        device = await self.create_test_device(
            client, token, building_id, name="Status Test Device"
        )

        response = await client.get(
            f"/api/v1/iot-devices/{device['id']}/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "device_id" in data
        assert "status" in data
        assert data["device_id"] == device["id"]
        assert data["status"] == "offline"  # Default status

    # ==================== Authentication ====================

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: AsyncClient):
        """API returns 401 without authentication."""
        # Test list endpoint
        list_response = await client.get("/api/v1/iot-devices")
        assert list_response.status_code == 401

        # Test get endpoint
        get_response = await client.get(
            "/api/v1/iot-devices/00000000-0000-0000-0000-000000000000"
        )
        assert get_response.status_code == 401

        # Test create endpoint
        create_response = await client.post(
            "/api/v1/iot-devices",
            json={
                "name": "Test",
                "device_type": "microphone",
                "building_id": "00000000-0000-0000-0000-000000000000",
            },
        )
        assert create_response.status_code == 401

        # Test update endpoint
        update_response = await client.patch(
            "/api/v1/iot-devices/00000000-0000-0000-0000-000000000000",
            json={"name": "Updated"},
        )
        assert update_response.status_code == 401

        # Test delete endpoint
        delete_response = await client.delete(
            "/api/v1/iot-devices/00000000-0000-0000-0000-000000000000"
        )
        assert delete_response.status_code == 401

        # Test position endpoint
        position_response = await client.patch(
            "/api/v1/iot-devices/00000000-0000-0000-0000-000000000000/position",
            json={
                "floor_plan_id": "00000000-0000-0000-0000-000000000000",
                "position_x": 50,
                "position_y": 50,
            },
        )
        assert position_response.status_code == 401

        # Test config endpoint
        config_response = await client.patch(
            "/api/v1/iot-devices/00000000-0000-0000-0000-000000000000/config",
            json={"config": {}},
        )
        assert config_response.status_code == 401

        # Test status endpoint
        status_response = await client.get(
            "/api/v1/iot-devices/00000000-0000-0000-0000-000000000000/status"
        )
        assert status_response.status_code == 401

    # ==================== Additional Edge Cases ====================

    @pytest.mark.asyncio
    async def test_create_device_with_position(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Create device with floor plan position."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create a floor plan
        floor_response = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={"floor_number": 1, "floor_name": "Ground Floor"},
        )
        floor_plan_id = floor_response.json()["id"]

        # Create device with position
        response = await client.post(
            "/api/v1/iot-devices",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Positioned Device",
                "device_type": "camera",
                "building_id": building_id,
                "floor_plan_id": floor_plan_id,
                "position_x": 25.0,
                "position_y": 75.0,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["floor_plan_id"] == floor_plan_id
        assert data["position_x"] == 25.0
        assert data["position_y"] == 75.0

    @pytest.mark.asyncio
    async def test_list_devices_pagination(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Test pagination of device list."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create multiple devices
        for i in range(5):
            await self.create_test_device(
                client, token, building_id, name=f"Page Device {i}"
            )

        # Request first page with small page size
        response = await client.get(
            "/api/v1/iot-devices?page=1&page_size=2",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["items"]) <= 2
        assert data["total"] >= 5
        assert data["total_pages"] >= 3

    @pytest.mark.asyncio
    async def test_update_device_partial(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Test partial update of device (only specified fields change)."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create device with specific values
        create_response = await client.post(
            "/api/v1/iot-devices",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Partial Update Device",
                "device_type": "sensor",
                "building_id": building_id,
                "ip_address": "192.168.1.100",
                "model": "Original Model",
            },
        )
        device = create_response.json()

        # Update only the name
        response = await client.patch(
            f"/api/v1/iot-devices/{device['id']}",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "New Name Only"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name Only"
        # Other fields should remain unchanged
        assert data["ip_address"] == "192.168.1.100"
        assert data["model"] == "Original Model"
        assert data["device_type"] == "sensor"

    @pytest.mark.asyncio
    async def test_get_device_status_not_found(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """GET /api/v1/iot-devices/{id}/status returns 404 for non-existent device."""
        token = await self.get_admin_token(client)

        response = await client.get(
            "/api/v1/iot-devices/00000000-0000-0000-0000-000000000000/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_position_not_found(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """PATCH /api/v1/iot-devices/{id}/position returns 404 for non-existent device."""
        token = await self.get_admin_token(client)

        response = await client.patch(
            "/api/v1/iot-devices/00000000-0000-0000-0000-000000000000/position",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "floor_plan_id": "00000000-0000-0000-0000-000000000001",
                "position_x": 50,
                "position_y": 50,
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_config_not_found(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """PATCH /api/v1/iot-devices/{id}/config returns 404 for non-existent device."""
        token = await self.get_admin_token(client)

        response = await client.patch(
            "/api/v1/iot-devices/00000000-0000-0000-0000-000000000000/config",
            headers={"Authorization": f"Bearer {token}"},
            json={"config": {"key": "value"}},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_device_all_types(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Test creating devices of all valid types."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        valid_types = ["microphone", "camera", "sensor", "gateway", "other"]

        for device_type in valid_types:
            response = await client.post(
                "/api/v1/iot-devices",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "name": f"Test {device_type}",
                    "device_type": device_type,
                    "building_id": building_id,
                },
            )

            assert response.status_code == 201, f"Failed to create {device_type}"
            data = response.json()
            assert data["device_type"] == device_type
