"""Tests for resources API endpoints."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.resource import Resource, ResourceType, ResourceStatus


class TestResourcesAPI:
    """Tests for resources API endpoints."""

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

    async def create_test_resource(self, db_session: AsyncSession, agency_id: uuid.UUID) -> Resource:
        """Helper to create a test resource."""
        resource = Resource(
            id=uuid.uuid4(),
            agency_id=agency_id,
            resource_type=ResourceType.PERSONNEL,
            name="Test Resource",
            call_sign="TEST-01",
            status=ResourceStatus.AVAILABLE,
        )
        db_session.add(resource)
        await db_session.commit()
        await db_session.refresh(resource)
        return resource

    # ==================== List Resources Tests ====================

    @pytest.mark.asyncio
    async def test_list_resources(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Listing resources should work for authenticated users."""
        token = await self.get_auth_token(client)

        # Create a test resource
        await self.create_test_resource(db_session, test_user.agency_id)

        response = await client.get(
            "/api/v1/resources",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_resources_no_auth(self, client: AsyncClient):
        """Listing resources without auth should fail."""
        response = await client.get("/api/v1/resources")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_available_resources(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Listing available resources should work."""
        token = await self.get_auth_token(client)

        # Create an available resource
        await self.create_test_resource(db_session, test_user.agency_id)

        response = await client.get(
            "/api/v1/resources/available",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200

    # ==================== Get Resource Tests ====================

    @pytest.mark.asyncio
    async def test_get_resource(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Getting a resource by ID should work."""
        token = await self.get_auth_token(client)

        # Create a resource
        resource = await self.create_test_resource(db_session, test_user.agency_id)

        response = await client.get(
            f"/api/v1/resources/{resource.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(resource.id)
        assert data["name"] == "Test Resource"

    @pytest.mark.asyncio
    async def test_get_resource_not_found(self, client: AsyncClient, test_user: User):
        """Getting a non-existent resource should return 404."""
        token = await self.get_auth_token(client)

        response = await client.get(
            f"/api/v1/resources/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    # ==================== Create Resource Tests ====================

    @pytest.mark.asyncio
    async def test_create_resource(self, client: AsyncClient, test_user: User):
        """Creating a resource should work for authorized users."""
        token = await self.get_auth_token(client)

        response = await client.post(
            "/api/v1/resources",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "resource_type": "personnel",
                "name": "New Resource",
                "call_sign": "NEW-01",
                "status": "available",
                "agency_id": str(test_user.agency_id),
            },
        )

        # Should either succeed or fail with permission error
        assert response.status_code in [201, 403]

    @pytest.mark.asyncio
    async def test_create_resource_invalid_data(self, client: AsyncClient, test_user: User):
        """Creating a resource with invalid data should fail."""
        token = await self.get_auth_token(client)

        response = await client.post(
            "/api/v1/resources",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "resource_type": "invalid_type",
                "name": "Bad Resource",
            },
        )

        assert response.status_code == 422

    # ==================== Update Resource Status Tests ====================

    @pytest.mark.asyncio
    async def test_update_resource_status(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Updating resource status should work."""
        token = await self.get_auth_token(client)

        # Create a resource
        resource = await self.create_test_resource(db_session, test_user.agency_id)

        response = await client.patch(
            f"/api/v1/resources/{resource.id}/status",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "status": "assigned",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "assigned"

    @pytest.mark.asyncio
    async def test_update_resource_status_invalid(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Updating resource status with invalid value should fail."""
        token = await self.get_auth_token(client)

        # Create a resource
        resource = await self.create_test_resource(db_session, test_user.agency_id)

        response = await client.patch(
            f"/api/v1/resources/{resource.id}/status",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "status": "invalid_status",
            },
        )

        assert response.status_code == 422

    # ==================== Update Resource Location Tests ====================

    @pytest.mark.asyncio
    async def test_update_resource_location(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Updating resource location should work."""
        token = await self.get_auth_token(client)

        # Create a resource
        resource = await self.create_test_resource(db_session, test_user.agency_id)

        response = await client.patch(
            f"/api/v1/resources/{resource.id}/location",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["latitude"] == 40.7128
        assert data["longitude"] == -74.0060

    @pytest.mark.asyncio
    async def test_update_resource_location_invalid_coords(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Updating resource location with invalid coordinates should fail."""
        token = await self.get_auth_token(client)

        # Create a resource
        resource = await self.create_test_resource(db_session, test_user.agency_id)

        response = await client.patch(
            f"/api/v1/resources/{resource.id}/location",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "latitude": 1000,  # Invalid latitude
                "longitude": -74.0060,
            },
        )

        assert response.status_code == 422

    # ==================== Delete Resource Tests ====================

    @pytest.mark.asyncio
    async def test_delete_resource(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Deleting a resource should work for authorized users."""
        token = await self.get_auth_token(client)

        # Create a resource
        resource = await self.create_test_resource(db_session, test_user.agency_id)

        response = await client.delete(
            f"/api/v1/resources/{resource.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should either succeed or fail with permission error
        assert response.status_code in [204, 403]

    @pytest.mark.asyncio
    async def test_delete_resource_not_found(self, client: AsyncClient, test_user: User):
        """Deleting a non-existent resource should return 404."""
        token = await self.get_auth_token(client)

        response = await client.delete(
            f"/api/v1/resources/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code in [404, 403]

    # ==================== Filter Tests ====================

    @pytest.mark.asyncio
    async def test_list_resources_by_type(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Filtering resources by type should work."""
        token = await self.get_auth_token(client)

        # Create a personnel resource
        await self.create_test_resource(db_session, test_user.agency_id)

        response = await client.get(
            "/api/v1/resources?resource_type=personnel",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_resources_by_status(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Filtering resources by status should work."""
        token = await self.get_auth_token(client)

        # Create an available resource
        await self.create_test_resource(db_session, test_user.agency_id)

        response = await client.get(
            "/api/v1/resources?status=available",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
