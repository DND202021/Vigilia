"""Tests for user management API endpoints."""

import pytest
from httpx import AsyncClient

from app.models.user import User, UserRole
from app.models.agency import Agency


class TestUsersAPI:
    """Tests for users API endpoints."""

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

    # ==================== User CRUD Tests ====================

    @pytest.mark.asyncio
    async def test_list_users(self, client: AsyncClient, admin_user: User):
        """Listing users should work for admins."""
        token = await self.get_admin_token(client)

        response = await client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    @pytest.mark.asyncio
    async def test_list_users_no_permission(self, client: AsyncClient, test_user: User):
        """Regular users cannot list users without permission."""
        token = await self.get_auth_token(client)

        response = await client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Responders don't have USER_READ permission
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_user(self, client: AsyncClient, admin_user: User, test_user: User):
        """Getting a user by ID should work for admins."""
        token = await self.get_admin_token(client)

        response = await client.get(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, client: AsyncClient, admin_user: User):
        """Getting a non-existent user should return 404."""
        token = await self.get_admin_token(client)

        response = await client.get(
            "/api/v1/users/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_user(self, client: AsyncClient, admin_user: User):
        """Creating a user should work for admins."""
        token = await self.get_admin_token(client)

        response = await client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": "newuser@example.com",
                "password": "NewUserPass123!",
                "full_name": "New Test User",
                "role": "dispatcher",
                "badge_number": "12345",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New Test User"
        assert data["role"] == "dispatcher"
        assert data["badge_number"] == "12345"

    @pytest.mark.asyncio
    async def test_create_user_weak_password(self, client: AsyncClient, admin_user: User):
        """Creating a user with weak password should fail."""
        token = await self.get_admin_token(client)

        response = await client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": "weakpassuser@example.com",
                "password": "weak",
                "full_name": "Weak Pass User",
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, client: AsyncClient, admin_user: User, test_user: User):
        """Creating a user with duplicate email should fail."""
        token = await self.get_admin_token(client)

        response = await client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": test_user.email,
                "password": "NewUserPass123!",
                "full_name": "Duplicate Email User",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_user(self, client: AsyncClient, admin_user: User, test_user: User):
        """Updating a user should work for admins."""
        token = await self.get_admin_token(client)

        response = await client.patch(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "full_name": "Updated Test User",
                "badge_number": "98765",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Test User"
        assert data["badge_number"] == "98765"

    @pytest.mark.asyncio
    async def test_delete_user(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Deleting a user should work for admins."""
        token = await self.get_admin_token(client)

        # Create a user to delete
        create_response = await client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": "todelete@example.com",
                "password": "ToDeletePass123!",
                "full_name": "To Delete User",
            },
        )
        user_id = create_response.json()["id"]

        # Delete the user
        response = await client.delete(
            f"/api/v1/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 204

        # Verify user is gone
        get_response = await client.get(
            f"/api/v1/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_cannot_delete_self(self, client: AsyncClient, admin_user: User):
        """Users cannot delete themselves."""
        token = await self.get_admin_token(client)

        response = await client.delete(
            f"/api/v1/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "cannot delete your own" in response.json()["detail"].lower()

    # ==================== User Actions Tests ====================

    @pytest.mark.asyncio
    async def test_activate_user(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Activating a user should work."""
        token = await self.get_admin_token(client)

        # Create an inactive user
        create_response = await client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": "inactive@example.com",
                "password": "InactivePass123!",
                "full_name": "Inactive User",
                "is_active": False,
            },
        )
        user_id = create_response.json()["id"]
        assert create_response.json()["is_active"] is False

        # Activate the user
        response = await client.post(
            f"/api/v1/users/{user_id}/activate",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is True

    @pytest.mark.asyncio
    async def test_deactivate_user(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Deactivating a user should work."""
        token = await self.get_admin_token(client)

        # Create an active user
        create_response = await client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": "todeactivate@example.com",
                "password": "DeactivatePass123!",
                "full_name": "To Deactivate User",
            },
        )
        user_id = create_response.json()["id"]

        # Deactivate the user
        response = await client.post(
            f"/api/v1/users/{user_id}/deactivate",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_cannot_deactivate_self(self, client: AsyncClient, admin_user: User):
        """Users cannot deactivate themselves."""
        token = await self.get_admin_token(client)

        response = await client.post(
            f"/api/v1/users/{admin_user.id}/deactivate",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "cannot deactivate your own" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_verify_user(self, client: AsyncClient, admin_user: User, test_user: User):
        """Verifying a user should work."""
        token = await self.get_admin_token(client)

        response = await client.post(
            f"/api/v1/users/{test_user.id}/verify",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["is_verified"] is True

    @pytest.mark.asyncio
    async def test_reset_password(self, client: AsyncClient, admin_user: User, test_user: User):
        """Resetting a user's password should work."""
        token = await self.get_admin_token(client)

        response = await client.post(
            f"/api/v1/users/{test_user.id}/reset-password",
            headers={"Authorization": f"Bearer {token}"},
            json={"new_password": "NewSecurePass123!"},
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Password has been reset successfully"

        # Verify new password works
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "NewSecurePass123!",
            },
        )
        assert login_response.status_code == 200

    # ==================== Role Management Tests ====================

    @pytest.mark.asyncio
    async def test_change_role(self, client: AsyncClient, admin_user: User, test_user: User):
        """Changing a user's role should work."""
        token = await self.get_admin_token(client)

        response = await client.post(
            f"/api/v1/users/{test_user.id}/role",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "dispatcher"},
        )

        assert response.status_code == 200
        assert response.json()["role"] == "dispatcher"

    @pytest.mark.asyncio
    async def test_change_role_invalid(self, client: AsyncClient, admin_user: User, test_user: User):
        """Changing to invalid role should fail."""
        token = await self.get_admin_token(client)

        response = await client.post(
            f"/api/v1/users/{test_user.id}/role",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "invalid_role"},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_list_roles(self, client: AsyncClient, test_user: User):
        """Listing roles should work for any authenticated user."""
        token = await self.get_auth_token(client)

        response = await client.get(
            "/api/v1/users/roles",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any(r["name"] == "dispatcher" for r in data)

    @pytest.mark.asyncio
    async def test_get_role(self, client: AsyncClient, test_user: User):
        """Getting a specific role should work."""
        token = await self.get_auth_token(client)

        response = await client.get(
            "/api/v1/users/roles/dispatcher",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "dispatcher"
        assert "permissions" in data

    @pytest.mark.asyncio
    async def test_list_permissions(self, client: AsyncClient, test_user: User):
        """Listing permissions should work for any authenticated user."""
        token = await self.get_auth_token(client)

        response = await client.get(
            "/api/v1/users/permissions",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any(p["name"] == "incident:create" for p in data)

    @pytest.mark.asyncio
    async def test_get_my_permissions(self, client: AsyncClient, test_user: User):
        """Getting current user's permissions should work."""
        token = await self.get_auth_token(client)

        response = await client.get(
            "/api/v1/users/me/permissions",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        # Responder should have incident:read permission
        assert "incident:read" in data

    # ==================== Stats Tests ====================

    @pytest.mark.asyncio
    async def test_get_user_stats(self, client: AsyncClient, admin_user: User):
        """Getting user statistics should work for admins."""
        token = await self.get_admin_token(client)

        response = await client.get(
            "/api/v1/users/stats",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "active" in data
        assert "inactive" in data
        assert "by_role" in data
