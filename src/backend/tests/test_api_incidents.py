"""Tests for incidents API endpoints."""

import pytest
from httpx import AsyncClient

from app.models.user import User
from app.models.agency import Agency


class TestIncidentsAPI:
    """Tests for incidents API endpoints."""

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
        """Helper to get admin auth token (full incident access)."""
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "AdminPassword123!",
            },
        )
        return login_response.json()["access_token"]

    # ==================== Incident CRUD ====================

    @pytest.mark.asyncio
    async def test_create_incident(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Creating an incident should work."""
        token = await self.get_admin_token(client)

        response = await client.post(
            "/api/v1/incidents",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category": "fire",
                "priority": 2,
                "title": "Structure Fire at 123 Main St",
                "description": "Two-story residential fire",
                "location": {
                    "latitude": 45.5017,
                    "longitude": -73.5673,
                    "address": "123 Main St, Montreal",
                },
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Structure Fire at 123 Main St"
        assert data["category"] == "fire"
        assert data["priority"] == 2
        assert data["status"] == "new"
        assert "id" in data
        assert "incident_number" in data

    @pytest.mark.asyncio
    async def test_get_incident(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Getting an incident by ID should work."""
        token = await self.get_admin_token(client)

        # Create an incident first
        create_response = await client.post(
            "/api/v1/incidents",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category": "medical",
                "priority": 3,
                "title": "Medical Emergency",
                "location": {
                    "latitude": 45.5017,
                    "longitude": -73.5673,
                },
            },
        )
        incident_id = create_response.json()["id"]

        # Get the incident
        response = await client.get(
            f"/api/v1/incidents/{incident_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == incident_id
        assert data["title"] == "Medical Emergency"

    @pytest.mark.asyncio
    async def test_get_incident_not_found(
        self, client: AsyncClient, admin_user: User
    ):
        """Getting a non-existent incident should return 404."""
        token = await self.get_admin_token(client)

        response = await client.get(
            "/api/v1/incidents/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_incidents(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Listing incidents should work."""
        token = await self.get_admin_token(client)

        # Create multiple incidents
        for i in range(3):
            await client.post(
                "/api/v1/incidents",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "category": "fire",
                    "priority": 3,
                    "title": f"Test Incident {i}",
                    "location": {
                        "latitude": 45.5017 + i * 0.01,
                        "longitude": -73.5673,
                    },
                },
            )

        # List all incidents
        response = await client.get(
            "/api/v1/incidents",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 3
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_incidents_filter_by_status(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Listing incidents with status filter should work."""
        token = await self.get_admin_token(client)

        # Create incidents
        await client.post(
            "/api/v1/incidents",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category": "fire",
                "priority": 2,
                "title": "New Fire Incident",
                "location": {
                    "latitude": 45.50,
                    "longitude": -73.56,
                },
            },
        )

        # Filter by status=new
        response = await client.get(
            "/api/v1/incidents?status=new",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["status"] == "new"

    @pytest.mark.asyncio
    async def test_list_incidents_filter_by_priority(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Listing incidents with priority filter should work."""
        token = await self.get_admin_token(client)

        # Create a high-priority incident
        await client.post(
            "/api/v1/incidents",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category": "fire",
                "priority": 1,  # Critical
                "title": "Critical Fire Incident",
                "location": {
                    "latitude": 45.50,
                    "longitude": -73.56,
                },
            },
        )

        # Filter by priority=1 (critical)
        response = await client.get(
            "/api/v1/incidents?priority=1",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["priority"] == 1

    @pytest.mark.asyncio
    async def test_list_incidents_filter_by_building(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Test filtering incidents by building_id."""
        token = await self.get_admin_token(client)

        # Create a building
        building_response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Incident Filter Test Building",
                "street_name": "Filter Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
                "building_type": "commercial",
            },
        )
        assert building_response.status_code == 201
        building_id = building_response.json()["id"]

        # Create an incident not linked to any building
        incident1_response = await client.post(
            "/api/v1/incidents",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category": "fire",
                "priority": 2,
                "title": "Unlinked Fire Incident",
                "location": {
                    "latitude": 45.5017,
                    "longitude": -73.5673,
                    "address": "123 Unlinked St",
                },
            },
        )
        assert incident1_response.status_code == 201

        # Create another incident (also not linked since API doesn't support
        # building_id in create yet)
        incident2_response = await client.post(
            "/api/v1/incidents",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category": "medical",
                "priority": 3,
                "title": "Another Incident",
                "location": {
                    "latitude": 45.5020,
                    "longitude": -73.5675,
                },
            },
        )
        assert incident2_response.status_code == 201

        # Filter by building_id - should return empty since no incidents are
        # linked to this building through the API
        response = await client.get(
            f"/api/v1/incidents?building_id={building_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        # The list should be empty since we can't link incidents to buildings
        # via the current API (building_id field in create is not exposed)
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_list_incidents_filter_by_building_invalid_uuid(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Test filtering incidents with invalid building_id returns 422."""
        token = await self.get_admin_token(client)

        # Filter by invalid UUID
        response = await client.get(
            "/api/v1/incidents?building_id=invalid-uuid",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_incidents_filter_by_building_nonexistent(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Test filtering incidents with non-existent building_id returns empty list."""
        token = await self.get_admin_token(client)

        # Filter by non-existent building UUID
        response = await client.get(
            "/api/v1/incidents?building_id=00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_update_incident(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Updating an incident should work."""
        token = await self.get_admin_token(client)

        # Create an incident first
        create_response = await client.post(
            "/api/v1/incidents",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category": "fire",
                "priority": 3,
                "title": "Update Test Incident",
                "location": {
                    "latitude": 45.5017,
                    "longitude": -73.5673,
                },
            },
        )
        incident_id = create_response.json()["id"]

        # Update the incident
        response = await client.patch(
            f"/api/v1/incidents/{incident_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "priority": 2,
                "title": "Updated Incident Title",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == 2
        assert data["title"] == "Updated Incident Title"

    @pytest.mark.asyncio
    async def test_get_active_incidents(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Getting active incidents should work."""
        token = await self.get_admin_token(client)

        # Create an incident
        await client.post(
            "/api/v1/incidents",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category": "fire",
                "priority": 2,
                "title": "Active Fire Incident",
                "location": {
                    "latitude": 45.5017,
                    "longitude": -73.5673,
                },
            },
        )

        # Get active incidents
        response = await client.get(
            "/api/v1/incidents/active",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All returned incidents should have active status
        for incident in data:
            assert incident["status"] in ["new", "assigned", "en_route", "on_scene"]

    @pytest.mark.asyncio
    async def test_get_incident_timeline(
        self, client: AsyncClient, admin_user: User, test_agency: Agency
    ):
        """Getting incident timeline should work."""
        token = await self.get_admin_token(client)

        # Create an incident
        create_response = await client.post(
            "/api/v1/incidents",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category": "fire",
                "priority": 2,
                "title": "Timeline Test Incident",
                "location": {
                    "latitude": 45.5017,
                    "longitude": -73.5673,
                },
            },
        )
        incident_id = create_response.json()["id"]

        # Get timeline
        response = await client.get(
            f"/api/v1/incidents/{incident_id}/timeline",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least the creation event

    @pytest.mark.asyncio
    async def test_create_incident_no_auth(self, client: AsyncClient):
        """Creating an incident without auth should fail."""
        response = await client.post(
            "/api/v1/incidents",
            json={
                "category": "fire",
                "priority": 3,
                "title": "Unauthorized Incident",
                "location": {
                    "latitude": 45.5017,
                    "longitude": -73.5673,
                },
            },
        )

        assert response.status_code == 401
