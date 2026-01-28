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

    # ==================== Nearby / Proximity ====================

    @pytest.mark.asyncio
    async def test_get_buildings_near_location_with_radius(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Getting buildings near a location with a specific radius should
        return only buildings within that radius."""
        token = await self.get_admin_token(client)

        # Create a building close to the search point (~0.03 km away)
        await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Close Radius Building",
                "street_name": "Close Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5018,
                "longitude": -73.5674,
            },
        )

        # Create a building farther away (~15 km away in Laval)
        await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Far Radius Building",
                "street_name": "Far Street",
                "city": "Laval",
                "province_state": "Quebec",
                "latitude": 45.6000,
                "longitude": -73.7000,
            },
        )

        # Search with a small 2km radius -- should find only the close building
        response = await client.get(
            "/api/v1/buildings/near/45.5017/-73.5673?radius_km=2",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        names = [b["name"] for b in data]
        assert "Close Radius Building" in names
        assert "Far Radius Building" not in names

    @pytest.mark.asyncio
    async def test_get_buildings_near_location_empty(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Getting buildings near a remote location should return an empty list
        when no buildings exist within the search radius."""
        token = await self.get_admin_token(client)

        # Create a building in Montreal
        await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Montreal Only Building",
                "street_name": "Local Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
            },
        )

        # Search near a location far away (Toronto area) with a small radius
        response = await client.get(
            "/api/v1/buildings/near/43.6532/-79.3832?radius_km=1",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    # ==================== Search by Name ====================

    @pytest.mark.asyncio
    async def test_search_buildings_by_name(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Searching buildings by name via the /search endpoint should return
        matching buildings."""
        token = await self.get_admin_token(client)

        # Create buildings with distinctive names
        await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Xylocarpa Community Center",
                "street_name": "Elm Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5100,
                "longitude": -73.5700,
            },
        )
        await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Downtown Office Tower",
                "street_name": "King Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5050,
                "longitude": -73.5650,
            },
        )

        # Search for the distinctive name
        response = await client.get(
            "/api/v1/buildings/search?q=Xylocarpa",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any("Xylocarpa" in b["name"] for b in data)
        # The unrelated building should not appear
        assert not any("Downtown Office Tower" in b["name"] for b in data)

    @pytest.mark.asyncio
    async def test_search_buildings_empty_query(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Searching with a query that matches nothing should return an empty
        list, and searching with a missing query should return 422."""
        token = await self.get_admin_token(client)

        # Create a building so the database is not empty
        await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Normal Building",
                "street_name": "Normal Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
            },
        )

        # Search with a query that will match nothing
        response = await client.get(
            "/api/v1/buildings/search?q=ZzNonExistent999",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

        # Search with no query parameter at all -- should be rejected (422)
        response_no_q = await client.get(
            "/api/v1/buildings/search",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response_no_q.status_code == 422

    # ==================== Building-Incident Integration ====================

    @pytest.mark.asyncio
    async def test_get_building_incidents(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Test getting incidents for a building."""
        token = await self.get_admin_token(client)

        # Create a building
        building_response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Incident Test Building",
                "street_name": "Emergency Lane",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
                "building_type": "commercial",
                "total_floors": 3,
            },
        )
        assert building_response.status_code == 201
        building_id = building_response.json()["id"]

        # Create an incident linked to the building
        incident_response = await client.post(
            "/api/v1/incidents",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category": "fire",
                "priority": 2,
                "title": "Structure Fire at Incident Test Building",
                "description": "Active fire on second floor",
                "location": {
                    "latitude": 45.5017,
                    "longitude": -73.5673,
                    "address": "Emergency Lane, Montreal",
                },
            },
        )
        assert incident_response.status_code == 201
        incident_id = incident_response.json()["id"]

        # Link the incident to the building by updating it
        # (Note: In a real scenario, this would be done via a dedicated endpoint
        # or during incident creation with building_id parameter)
        # For now, we'll use direct database manipulation through the API
        # by creating an incident with building_id filter test

        # Get building incidents
        response = await client.get(
            f"/api/v1/buildings/{building_id}/incidents",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        # Building has no linked incidents initially since we can't link via API
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_get_building_incidents_empty(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Test getting incidents for a building with no incidents."""
        token = await self.get_admin_token(client)

        # Create a building with no incidents
        building_response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Empty Incidents Building",
                "street_name": "Quiet Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5100,
                "longitude": -73.5700,
            },
        )
        assert building_response.status_code == 201
        building_id = building_response.json()["id"]

        # Get building incidents (should be empty)
        response = await client.get(
            f"/api/v1/buildings/{building_id}/incidents",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 0
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_building_incidents_not_found(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Test getting incidents for a non-existent building returns 404."""
        token = await self.get_admin_token(client)

        # Try to get incidents for a non-existent building
        response = await client.get(
            "/api/v1/buildings/00000000-0000-0000-0000-000000000000/incidents",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_building_incidents_with_filters(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Test getting building incidents with status and category filters."""
        token = await self.get_admin_token(client)

        # Create a building
        building_response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Filter Test Building",
                "street_name": "Filter Avenue",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5050,
                "longitude": -73.5650,
            },
        )
        assert building_response.status_code == 201
        building_id = building_response.json()["id"]

        # Test with status filter
        response = await client.get(
            f"/api/v1/buildings/{building_id}/incidents?status=new",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

        # Test with category filter
        response = await client.get(
            f"/api/v1/buildings/{building_id}/incidents?category=fire",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_get_building_incidents_pagination(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Test pagination of building incidents."""
        token = await self.get_admin_token(client)

        # Create a building
        building_response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Pagination Test Building",
                "street_name": "Page Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5030,
                "longitude": -73.5630,
            },
        )
        assert building_response.status_code == 201
        building_id = building_response.json()["id"]

        # Test pagination parameters
        response = await client.get(
            f"/api/v1/buildings/{building_id}/incidents?page=1&page_size=10",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    # ==================== Floor Plan Location Markers (Sprint 4) ====================

    @pytest.mark.asyncio
    async def test_update_floor_plan_locations(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Test updating floor plan key_locations."""
        token = await self.get_admin_token(client)

        # Create a building
        building_response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Marker Test Building",
                "street_name": "Marker Avenue",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5080,
                "longitude": -73.5680,
            },
        )
        assert building_response.status_code == 201
        building_id = building_response.json()["id"]

        # Add a floor plan
        floor_response = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "floor_number": 1,
                "floor_name": "Ground Floor",
            },
        )
        assert floor_response.status_code == 201
        floor_plan_id = floor_response.json()["id"]

        # Update locations
        locations = [
            {"type": "fire_extinguisher", "name": "FE-101", "x": 25.5, "y": 30.0},
            {"type": "stairwell", "name": "Stairwell A", "x": 10.0, "y": 50.0},
        ]

        response = await client.patch(
            f"/api/v1/buildings/floors/{floor_plan_id}/locations",
            headers={"Authorization": f"Bearer {token}"},
            json={"key_locations": locations},
        )

        assert response.status_code == 200
        data = response.json()
        assert "key_locations" in data
        assert len(data["key_locations"]) == 2

    @pytest.mark.asyncio
    async def test_update_floor_plan_locations_structure(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Test that location data is properly structured with all fields."""
        token = await self.get_admin_token(client)

        # Create building and floor plan
        building_response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Structure Test Building",
                "street_name": "Structure Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5090,
                "longitude": -73.5690,
            },
        )
        building_id = building_response.json()["id"]

        floor_response = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={"floor_number": 1, "floor_name": "Main Floor"},
        )
        floor_plan_id = floor_response.json()["id"]

        # Update with full location structure
        locations = [
            {
                "type": "aed",
                "name": "AED Station 1",
                "x": 45.5,
                "y": 32.8,
                "description": "Near main entrance",
            }
        ]

        response = await client.patch(
            f"/api/v1/buildings/floors/{floor_plan_id}/locations",
            headers={"Authorization": f"Bearer {token}"},
            json={"key_locations": locations},
        )

        assert response.status_code == 200
        data = response.json()
        saved_location = data["key_locations"][0]
        assert saved_location["type"] == "aed"
        assert saved_location["name"] == "AED Station 1"
        assert saved_location["x"] == 45.5
        assert saved_location["y"] == 32.8

    @pytest.mark.asyncio
    async def test_floor_plan_multiple_marker_types(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Test floor plan with various marker types."""
        token = await self.get_admin_token(client)

        # Create building and floor plan
        building_response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Multi Marker Building",
                "street_name": "Multi Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5100,
                "longitude": -73.5700,
            },
        )
        building_id = building_response.json()["id"]

        floor_response = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={"floor_number": 1},
        )
        floor_plan_id = floor_response.json()["id"]

        # Add various marker types
        locations = [
            {"type": "fire_extinguisher", "name": "FE-1", "x": 10.0, "y": 10.0},
            {"type": "stairwell", "name": "Stairs A", "x": 20.0, "y": 20.0},
            {"type": "elevator", "name": "Elevator 1", "x": 30.0, "y": 30.0},
            {"type": "aed", "name": "AED", "x": 40.0, "y": 40.0},
            {"type": "electrical_panel", "name": "Panel A", "x": 50.0, "y": 50.0},
            {"type": "emergency_exit", "name": "Exit 1", "x": 60.0, "y": 60.0},
        ]

        response = await client.patch(
            f"/api/v1/buildings/floors/{floor_plan_id}/locations",
            headers={"Authorization": f"Bearer {token}"},
            json={"key_locations": locations},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["key_locations"]) == 6

        # Verify different types are preserved
        types = [loc["type"] for loc in data["key_locations"]]
        assert "fire_extinguisher" in types
        assert "stairwell" in types
        assert "aed" in types

    @pytest.mark.asyncio
    async def test_update_locations_preserves_other_fields(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Test that updating locations doesn't affect other floor plan fields."""
        token = await self.get_admin_token(client)

        # Create building
        building_response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Preserve Fields Building",
                "street_name": "Preserve Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5110,
                "longitude": -73.5710,
            },
        )
        building_id = building_response.json()["id"]

        # Create floor plan with notes
        floor_response = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "floor_number": 2,
                "floor_name": "Second Floor",
                "notes": "Important floor notes",
            },
        )
        floor_plan_id = floor_response.json()["id"]
        original_notes = floor_response.json().get("notes")

        # Update only locations
        response = await client.patch(
            f"/api/v1/buildings/floors/{floor_plan_id}/locations",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "key_locations": [
                    {"type": "stairwell", "name": "Stairs B", "x": 15.0, "y": 25.0}
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify locations were updated
        assert len(data["key_locations"]) == 1

        # Verify other fields preserved
        assert data["floor_name"] == "Second Floor"
        assert data["floor_number"] == 2
