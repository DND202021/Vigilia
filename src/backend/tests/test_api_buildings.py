"""Tests for buildings API endpoints."""

import pytest
from httpx import AsyncClient

from app.models.user import User
from app.models.agency import Agency


class TestBuildingsAPI:
    """Tests for buildings API endpoints."""

    async def get_auth_token(self, client: AsyncClient) -> str:
        """Helper to get auth token for API requests (read-only access)."""
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!",
            },
        )
        return login_response.json()["access_token"]

    async def get_admin_token(self, client: AsyncClient) -> str:
        """Helper to get admin auth token (full building access)."""
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "AdminPassword123!",
            },
        )
        return login_response.json()["access_token"]

    # ==================== Building CRUD ====================

    @pytest.mark.asyncio
    async def test_create_building(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Creating a building should work."""
        token = await self.get_admin_token(client)

        response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Test Building",
                "civic_number": "123",
                "street_name": "Main Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
                "building_type": "commercial",
                "total_floors": 5,
                "has_elevator": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Building"
        assert data["city"] == "Montreal"
        assert data["building_type"] == "commercial"
        assert data["total_floors"] == 5
        assert data["has_elevator"] is True
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_building_minimal(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Creating a building with minimal fields should work."""
        token = await self.get_admin_token(client)

        response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Minimal Building",
                "street_name": "Test Street",
                "city": "Laval",
                "province_state": "Quebec",
                "latitude": 45.57,
                "longitude": -73.75,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Building"
        assert data["hazard_level"] == "low"  # Default
        assert data["is_verified"] is False

    @pytest.mark.asyncio
    async def test_create_building_no_auth(self, client: AsyncClient):
        """Creating a building without auth should fail."""
        response = await client.post(
            "/api/v1/buildings",
            json={
                "name": "Test Building",
                "street_name": "Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_building(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Getting a building by ID should work."""
        token = await self.get_admin_token(client)

        # Create a building first
        create_response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Get Test Building",
                "street_name": "Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
            },
        )
        building_id = create_response.json()["id"]

        # Get the building
        response = await client.get(
            f"/api/v1/buildings/{building_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == building_id
        assert data["name"] == "Get Test Building"

    @pytest.mark.asyncio
    async def test_get_building_not_found(self, client: AsyncClient, admin_user: User):
        """Getting a non-existent building should return 404."""
        token = await self.get_admin_token(client)

        response = await client.get(
            "/api/v1/buildings/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_buildings(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Listing buildings should work."""
        token = await self.get_admin_token(client)

        # Create multiple buildings
        for i in range(3):
            await client.post(
                "/api/v1/buildings",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "name": f"Building {i}",
                    "street_name": f"Street {i}",
                    "city": "Montreal",
                    "province_state": "Quebec",
                    "latitude": 45.5017 + i * 0.01,
                    "longitude": -73.5673,
                },
            )

        # List all buildings
        response = await client.get(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 3
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_buildings_filter_by_type(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Listing buildings with type filter should work."""
        token = await self.get_admin_token(client)

        # Create buildings of different types
        await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Healthcare Building",
                "street_name": "Hospital Road",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.50,
                "longitude": -73.56,
                "building_type": "healthcare",
            },
        )

        # Filter by healthcare
        response = await client.get(
            "/api/v1/buildings?building_type=healthcare",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["building_type"] == "healthcare"

    @pytest.mark.asyncio
    async def test_update_building(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Updating a building should work."""
        token = await self.get_admin_token(client)

        # Create a building first
        create_response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Update Test Building",
                "street_name": "Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
            },
        )
        building_id = create_response.json()["id"]

        # Update the building
        response = await client.patch(
            f"/api/v1/buildings/{building_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Updated Building Name",
                "has_sprinkler_system": True,
                "hazard_level": "high",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Building Name"
        assert data["has_sprinkler_system"] is True
        assert data["hazard_level"] == "high"

    @pytest.mark.asyncio
    async def test_delete_building(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Deleting a building should work."""
        token = await self.get_admin_token(client)

        # Create a building first
        create_response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Delete Test Building",
                "street_name": "Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
            },
        )
        building_id = create_response.json()["id"]

        # Delete the building
        response = await client.delete(
            f"/api/v1/buildings/{building_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 204

        # Verify it's gone
        get_response = await client.get(
            f"/api/v1/buildings/{building_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_verify_building(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Verifying a building should work."""
        token = await self.get_admin_token(client)

        # Create a building first
        create_response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Verify Test Building",
                "street_name": "Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
            },
        )
        building_id = create_response.json()["id"]
        assert create_response.json()["is_verified"] is False

        # Verify the building
        response = await client.post(
            f"/api/v1/buildings/{building_id}/verify",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_verified"] is True
        assert data["verified_at"] is not None

    @pytest.mark.asyncio
    async def test_get_building_stats(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Getting building statistics should work."""
        token = await self.get_admin_token(client)

        # Create some buildings
        await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Stats Building 1",
                "street_name": "Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
                "has_hazmat": True,
            },
        )

        response = await client.get(
            "/api/v1/buildings/stats",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "verified" in data
        assert "with_hazmat" in data
        assert data["total"] >= 1

    # ==================== Floor Plans ====================

    @pytest.mark.asyncio
    async def test_add_floor_plan(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Adding a floor plan should work."""
        token = await self.get_admin_token(client)

        # Create a building first
        create_response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Floor Plan Test Building",
                "street_name": "Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
                "total_floors": 3,
            },
        )
        building_id = create_response.json()["id"]

        # Add a floor plan
        response = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "floor_number": 1,
                "floor_name": "Ground Floor",
                "floor_area_sqm": 500.0,
                "ceiling_height_m": 3.5,
                "key_locations": [
                    {"type": "stairwell", "name": "Main Stairs", "x": 100, "y": 200},
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["floor_number"] == 1
        assert data["floor_name"] == "Ground Floor"
        assert data["floor_area_sqm"] == 500.0
        assert len(data["key_locations"]) == 1

    @pytest.mark.asyncio
    async def test_get_floor_plans(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Getting floor plans for a building should work."""
        token = await self.get_admin_token(client)

        # Create a building
        create_response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Multi-Floor Building",
                "street_name": "Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
                "total_floors": 3,
                "basement_levels": 1,
            },
        )
        building_id = create_response.json()["id"]

        # Add multiple floor plans
        for floor_num in [-1, 0, 1, 2]:
            await client.post(
                f"/api/v1/buildings/{building_id}/floors",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "floor_number": floor_num,
                },
            )

        # Get floor plans
        response = await client.get(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        # Should be sorted by floor number
        assert data[0]["floor_number"] == -1
        assert data[1]["floor_number"] == 0
        assert data[2]["floor_number"] == 1
        assert data[3]["floor_number"] == 2

    @pytest.mark.asyncio
    async def test_get_floor_plan_by_number(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Getting a specific floor plan by number should work."""
        token = await self.get_admin_token(client)

        # Create a building
        create_response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Floor Number Test Building",
                "street_name": "Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
                "total_floors": 2,
            },
        )
        building_id = create_response.json()["id"]

        # Add a floor plan
        await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "floor_number": 1,
                "floor_name": "First Floor",
                "notes": "Test notes",
            },
        )

        # Get by floor number
        response = await client.get(
            f"/api/v1/buildings/{building_id}/floors/1",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["floor_number"] == 1
        assert data["floor_name"] == "First Floor"

    @pytest.mark.asyncio
    async def test_update_floor_plan(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Updating a floor plan should work."""
        token = await self.get_admin_token(client)

        # Create a building
        create_response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Update Floor Test Building",
                "street_name": "Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
                "total_floors": 2,
            },
        )
        building_id = create_response.json()["id"]

        # Add a floor plan
        floor_response = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "floor_number": 0,
                "floor_name": "Ground",
            },
        )
        floor_plan_id = floor_response.json()["id"]

        # Update the floor plan
        response = await client.patch(
            f"/api/v1/buildings/floors/{floor_plan_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "floor_name": "Updated Ground Floor",
                "floor_area_sqm": 750.0,
                "notes": "Updated notes",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["floor_name"] == "Updated Ground Floor"
        assert data["floor_area_sqm"] == 750.0
        assert data["notes"] == "Updated notes"

    @pytest.mark.asyncio
    async def test_delete_floor_plan(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Deleting a floor plan should work."""
        token = await self.get_admin_token(client)

        # Create a building
        create_response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Delete Floor Test Building",
                "street_name": "Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
                "total_floors": 2,
            },
        )
        building_id = create_response.json()["id"]

        # Add a floor plan
        floor_response = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "floor_number": 0,
            },
        )
        floor_plan_id = floor_response.json()["id"]

        # Delete the floor plan
        response = await client.delete(
            f"/api/v1/buildings/floors/{floor_plan_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 204

        # Verify it's gone
        get_response = await client.get(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert len(get_response.json()) == 0

    @pytest.mark.asyncio
    async def test_add_duplicate_floor_plan(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Adding a duplicate floor plan should fail."""
        token = await self.get_admin_token(client)

        # Create a building
        create_response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Duplicate Floor Test Building",
                "street_name": "Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
            },
        )
        building_id = create_response.json()["id"]

        # Add a floor plan
        await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={"floor_number": 0},
        )

        # Try to add duplicate
        response = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={"floor_number": 0},
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    # ==================== Search ====================

    @pytest.mark.asyncio
    async def test_search_buildings(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Searching buildings should work."""
        token = await self.get_admin_token(client)

        # Create a building with a unique name
        await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "UniqueSearchName Fire Station",
                "street_name": "Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
            },
        )

        # Search
        response = await client.get(
            "/api/v1/buildings/search?q=UniqueSearchName",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any("UniqueSearchName" in b["name"] for b in data)

    @pytest.mark.asyncio
    async def test_get_buildings_near_location(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Getting buildings near a location should work."""
        token = await self.get_admin_token(client)

        # Create a building at a specific location
        await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Near Location Building",
                "street_name": "Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
            },
        )

        # Search near that location
        response = await client.get(
            "/api/v1/buildings/near/45.5017/-73.5673?radius_km=1",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    # ==================== BIM Import ====================

    @pytest.mark.asyncio
    async def test_import_bim_data(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Importing BIM data should work."""
        token = await self.get_admin_token(client)

        # Create a building
        create_response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "BIM Test Building",
                "street_name": "Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
            },
        )
        building_id = create_response.json()["id"]

        # Import BIM data
        bim_data = {
            "total_area": 1500.0,
            "height": 10.5,
            "floors": [
                {"number": 0, "name": "Ground Floor", "area": 750.0},
                {"number": 1, "name": "First Floor", "area": 750.0},
            ],
        }

        response = await client.post(
            f"/api/v1/buildings/{building_id}/bim",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "bim_data": bim_data,
                "bim_file_url": "https://example.com/building.ifc",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_bim_data"] is True
        assert data["total_area_sqm"] == 1500.0
        assert data["building_height_m"] == 10.5

        # Check floor plans were created
        floors_response = await client.get(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert len(floors_response.json()) == 2
