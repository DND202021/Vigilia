"""Tests for floor plan upload API endpoints."""

import io
import pytest
from httpx import AsyncClient

from app.models.user import User
from app.models.agency import Agency


class TestFloorPlanUploadAPI:
    """Tests for floor plan upload API endpoints."""

    async def get_admin_token(self, client: AsyncClient) -> str:
        """Helper to get admin auth token."""
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "AdminPassword123!",
            },
        )
        return login_response.json()["access_token"]

    async def create_test_building(self, client: AsyncClient, token: str) -> str:
        """Helper to create a test building and return its ID."""
        response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Upload Test Building",
                "street_name": "Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
                "total_floors": 5,
                "basement_levels": 1,
            },
        )
        return response.json()["id"]

    # ==================== Floor Plan Creation (Without File Upload) ====================

    @pytest.mark.asyncio
    async def test_add_floor_plan(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test adding a floor plan without file upload."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "floor_number": 0,
                "floor_name": "Ground Floor",
                "floor_area_sqm": 500.0,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["floor_number"] == 0
        assert data["floor_name"] == "Ground Floor"
        assert data["floor_area_sqm"] == 500.0
        assert "id" in data

    @pytest.mark.asyncio
    async def test_add_floor_plan_basement(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test adding a basement floor plan."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "floor_number": -1,
                "floor_name": "Basement 1",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["floor_number"] == -1
        assert data["floor_name"] == "Basement 1"

    @pytest.mark.asyncio
    async def test_add_floor_plan_with_locations(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test adding a floor plan with location markers."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "floor_number": 0,
                "floor_name": "Ground",
                "key_locations": [
                    {"name": "Lobby", "x": 50, "y": 50, "type": "custom"},
                    {"name": "Stairwell A", "x": 10, "y": 20, "type": "stairwell"},
                ],
                "emergency_exits": [
                    {"name": "Main Exit", "x": 5, "y": 50},
                    {"name": "Side Exit", "x": 95, "y": 50},
                ],
                "fire_equipment": [
                    {"name": "Fire Extinguisher 1", "x": 25, "y": 30, "type": "fire_extinguisher"},
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["key_locations"]) == 2
        assert len(data["emergency_exits"]) == 2
        assert len(data["fire_equipment"]) == 1

    @pytest.mark.asyncio
    async def test_add_floor_plan_duplicate(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test adding duplicate floor number fails."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # First floor plan
        response1 = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={"floor_number": 0},
        )
        assert response1.status_code == 201

        # Duplicate
        response2 = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={"floor_number": 0},
        )
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_add_floor_plan_no_auth(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test adding floor plan without auth fails."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            json={"floor_number": 0},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_add_floor_plan_building_not_found(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test adding floor plan to non-existent building fails."""
        token = await self.get_admin_token(client)
        fake_id = "00000000-0000-0000-0000-000000000000"

        response = await client.post(
            f"/api/v1/buildings/{fake_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={"floor_number": 0},
        )
        # API returns 400 for invalid building reference
        assert response.status_code in [400, 404]

    # ==================== Floor Plan Update Tests ====================

    @pytest.mark.asyncio
    async def test_update_floor_plan_info(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test updating floor plan general information."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # First create a floor plan
        floor_response = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={"floor_number": 0, "floor_name": "Ground"},
        )
        assert floor_response.status_code == 201
        floor_plan_id = floor_response.json()["id"]

        # Update floor plan info
        response = await client.patch(
            f"/api/v1/buildings/floors/{floor_plan_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "floor_name": "Updated Ground Floor",
                "floor_area_sqm": 500.0,
                "notes": "Main entrance and lobby area",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["floor_name"] == "Updated Ground Floor"
        assert data["floor_area_sqm"] == 500.0
        assert data["notes"] == "Main entrance and lobby area"

    @pytest.mark.asyncio
    async def test_update_floor_plan_locations(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test updating floor plan location markers."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create floor plan
        floor_response = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={"floor_number": 0, "floor_name": "Ground"},
        )
        floor_plan_id = floor_response.json()["id"]

        # Update locations
        response = await client.patch(
            f"/api/v1/buildings/floors/{floor_plan_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "key_locations": [
                    {"name": "Reception", "x": 50, "y": 20, "type": "custom"},
                ],
                "emergency_exits": [
                    {"name": "Front Exit", "x": 50, "y": 95},
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["key_locations"]) == 1
        assert data["key_locations"][0]["name"] == "Reception"

    @pytest.mark.asyncio
    async def test_update_floor_plan_not_found(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test updating non-existent floor plan returns 404."""
        token = await self.get_admin_token(client)

        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.patch(
            f"/api/v1/buildings/floors/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"floor_name": "Test"},
        )

        assert response.status_code == 404

    # ==================== Floor Plan Retrieval Tests ====================

    @pytest.mark.asyncio
    async def test_get_floor_plans(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test getting all floor plans for a building."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Add multiple floor plans
        for i in range(3):
            await client.post(
                f"/api/v1/buildings/{building_id}/floors",
                headers={"Authorization": f"Bearer {token}"},
                json={"floor_number": i, "floor_name": f"Floor {i}"},
            )

        # Get all floor plans
        response = await client.get(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_get_floor_plan_by_number(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test getting a specific floor plan by number."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Add floor plan
        await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={"floor_number": 2, "floor_name": "Second Floor"},
        )

        # Get by number
        response = await client.get(
            f"/api/v1/buildings/{building_id}/floors/2",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["floor_number"] == 2
        assert data["floor_name"] == "Second Floor"

    @pytest.mark.asyncio
    async def test_get_floor_plan_not_found(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test getting non-existent floor plan returns 404."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.get(
            f"/api/v1/buildings/{building_id}/floors/99",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    # ==================== Floor Plan Deletion Tests ====================

    @pytest.mark.asyncio
    async def test_delete_floor_plan(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test deleting a floor plan."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Add floor plan
        floor_response = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={"floor_number": 0, "floor_name": "Ground"},
        )
        floor_plan_id = floor_response.json()["id"]

        # Delete
        response = await client.delete(
            f"/api/v1/buildings/floors/{floor_plan_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 204

        # Verify deleted
        get_response = await client.get(
            f"/api/v1/buildings/{building_id}/floors/0",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_floor_plan_not_found(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test deleting non-existent floor plan returns 404."""
        token = await self.get_admin_token(client)

        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.delete(
            f"/api/v1/buildings/floors/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
