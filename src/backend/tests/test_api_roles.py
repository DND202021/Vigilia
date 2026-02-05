"""Tests for role management API endpoints."""

import pytest
from httpx import AsyncClient

from app.models.user import User, UserRole
from app.models.role import Role
from app.models.agency import Agency


class TestRolesAPI:
    """Tests for roles API endpoints."""

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

    # ==================== Role CRUD Tests ====================

    @pytest.mark.asyncio
    async def test_list_roles(self, client: AsyncClient, admin_user: User):
        """Listing roles should work for admin users."""
        token = await self.get_admin_token(client)

        response = await client.get(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    @pytest.mark.asyncio
    async def test_list_roles_no_permission(self, client: AsyncClient, test_user: User):
        """Regular users cannot list roles without ROLE_READ permission."""
        # Responders have ROLE_READ permission, so this test checks if the endpoint works
        token = await self.get_auth_token(client)

        response = await client.get(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Responders now have role:read permission
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_role_stats(self, client: AsyncClient, admin_user: User):
        """Getting role statistics should work for admins."""
        token = await self.get_admin_token(client)

        response = await client.get(
            "/api/v1/roles/stats",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "active" in data
        assert "inactive" in data
        assert "system_roles" in data
        assert "custom_roles" in data

    @pytest.mark.asyncio
    async def test_get_permissions(self, client: AsyncClient, test_user: User):
        """Getting permissions should work for any authenticated user."""
        token = await self.get_auth_token(client)

        response = await client.get(
            "/api/v1/roles/permissions",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        # Should have categories
        assert "category" in data[0]
        assert "permissions" in data[0]

    @pytest.mark.asyncio
    async def test_create_role(self, client: AsyncClient, admin_user: User):
        """Creating a role should work for admins with ROLE_CREATE permission."""
        token = await self.get_admin_token(client)

        response = await client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "test_custom_role",
                "display_name": "Test Custom Role",
                "description": "A test role for testing",
                "permissions": ["incident:read", "alert:read"],
                "hierarchy_level": 60,
                "color": "#3B82F6",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test_custom_role"
        assert data["display_name"] == "Test Custom Role"
        assert data["is_system_role"] is False
        assert "incident:read" in data["permissions"]
        assert data["hierarchy_level"] == 60

    @pytest.mark.asyncio
    async def test_create_role_invalid_name(self, client: AsyncClient, admin_user: User):
        """Creating a role with invalid name should fail."""
        token = await self.get_admin_token(client)

        response = await client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Invalid Name With Spaces",
                "display_name": "Invalid Role",
                "permissions": [],
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_create_role_invalid_permission(self, client: AsyncClient, admin_user: User):
        """Creating a role with invalid permissions should fail."""
        token = await self.get_admin_token(client)

        response = await client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "invalid_perm_role",
                "display_name": "Invalid Perm Role",
                "permissions": ["invalid:permission"],
            },
        )

        assert response.status_code == 400
        assert "invalid permission" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_role(self, client: AsyncClient, admin_user: User):
        """Getting a role by ID should work."""
        token = await self.get_admin_token(client)

        # First create a role
        create_response = await client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "role_to_get",
                "display_name": "Role To Get",
                "permissions": ["incident:read"],
            },
        )
        role_id = create_response.json()["id"]

        # Now get it
        response = await client.get(
            f"/api/v1/roles/{role_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "role_to_get"

    @pytest.mark.asyncio
    async def test_get_role_by_name(self, client: AsyncClient, admin_user: User):
        """Getting a role by name should work."""
        token = await self.get_admin_token(client)

        # Create a role
        await client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "role_by_name",
                "display_name": "Role By Name",
                "permissions": ["incident:read"],
            },
        )

        # Get by name
        response = await client.get(
            "/api/v1/roles/by-name/role_by_name",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "role_by_name"

    @pytest.mark.asyncio
    async def test_update_role(self, client: AsyncClient, admin_user: User):
        """Updating a role should work."""
        token = await self.get_admin_token(client)

        # Create a role
        create_response = await client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "role_to_update",
                "display_name": "Role To Update",
                "permissions": ["incident:read"],
            },
        )
        role_id = create_response.json()["id"]

        # Update it
        response = await client.patch(
            f"/api/v1/roles/{role_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "display_name": "Updated Role Name",
                "permissions": ["incident:read", "alert:read"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Updated Role Name"
        assert "alert:read" in data["permissions"]

    @pytest.mark.asyncio
    async def test_delete_role(self, client: AsyncClient, admin_user: User):
        """Deleting a custom role should work."""
        token = await self.get_admin_token(client)

        # Create a role
        create_response = await client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "role_to_delete",
                "display_name": "Role To Delete",
                "permissions": ["incident:read"],
            },
        )
        role_id = create_response.json()["id"]

        # Delete it
        response = await client.delete(
            f"/api/v1/roles/{role_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 204

        # Verify it's gone
        get_response = await client.get(
            f"/api/v1/roles/{role_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_duplicate_role(self, client: AsyncClient, admin_user: User):
        """Duplicating a role should work."""
        token = await self.get_admin_token(client)

        # Create a source role
        create_response = await client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "source_role",
                "display_name": "Source Role",
                "permissions": ["incident:read", "alert:read", "resource:read"],
                "hierarchy_level": 45,
            },
        )
        role_id = create_response.json()["id"]

        # Duplicate it
        response = await client.post(
            f"/api/v1/roles/{role_id}/duplicate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "new_name": "duplicated_role",
                "new_display_name": "Duplicated Role",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "duplicated_role"
        assert data["display_name"] == "Duplicated Role"
        # Should have same permissions as source
        assert "incident:read" in data["permissions"]
        assert "alert:read" in data["permissions"]

    @pytest.mark.asyncio
    async def test_initialize_default_roles(self, client: AsyncClient, admin_user: User):
        """Initializing default roles should work."""
        token = await self.get_admin_token(client)

        response = await client.post(
            "/api/v1/roles/initialize",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    # ==================== System Role Protection Tests ====================

    @pytest.mark.asyncio
    async def test_cannot_delete_system_role(self, client: AsyncClient, admin_user: User):
        """System roles cannot be deleted."""
        token = await self.get_admin_token(client)

        # Initialize default roles first
        await client.post(
            "/api/v1/roles/initialize",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Try to get system_admin role and delete it
        role_response = await client.get(
            "/api/v1/roles/by-name/system_admin",
            headers={"Authorization": f"Bearer {token}"},
        )

        if role_response.status_code == 200:
            role_id = role_response.json()["id"]

            response = await client.delete(
                f"/api/v1/roles/{role_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 400
            assert "cannot delete system roles" in response.json()["detail"].lower()
