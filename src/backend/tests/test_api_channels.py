"""Tests for channels API endpoints."""

import uuid
import pytest
from httpx import AsyncClient

from app.models.user import User
from app.models.channel import ChannelType


class TestChannelsAPI:
    """Tests for channels API endpoints."""

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

    # ==================== Channel CRUD Tests ====================

    @pytest.mark.asyncio
    async def test_list_channels(self, client: AsyncClient, test_user: User):
        """Listing channels should work for authenticated users."""
        token = await self.get_auth_token(client)

        response = await client.get(
            "/api/v1/channels",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_channels_no_auth(self, client: AsyncClient):
        """Listing channels without authentication should fail."""
        response = await client.get("/api/v1/channels")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_team_channel(self, client: AsyncClient, test_user: User):
        """Creating a team channel should work."""
        token = await self.get_auth_token(client)

        response = await client.post(
            "/api/v1/channels",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Test Team Channel",
                "description": "A test channel",
                "channel_type": "team",
                "is_private": False,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Team Channel"
        assert data["channel_type"] == "team"
        assert data["is_private"] is False

    @pytest.mark.asyncio
    async def test_create_broadcast_channel_no_permission(self, client: AsyncClient, test_user: User):
        """Creating a broadcast channel without permission should fail."""
        token = await self.get_auth_token(client)

        response = await client.post(
            "/api/v1/channels",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Test Broadcast",
                "channel_type": "broadcast",
            },
        )

        # Responder doesn't have broadcast permission
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_direct_channel(self, client: AsyncClient, test_user: User, admin_user: User):
        """Creating a direct message channel should work."""
        token = await self.get_auth_token(client)

        response = await client.post(
            "/api/v1/channels/direct",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": str(admin_user.id)},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["channel_type"] == "direct"

    @pytest.mark.asyncio
    async def test_create_direct_channel_with_self(self, client: AsyncClient, test_user: User):
        """Creating a DM channel with yourself should fail."""
        token = await self.get_auth_token(client)

        response = await client.post(
            "/api/v1/channels/direct",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": str(test_user.id)},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_channel(self, client: AsyncClient, test_user: User):
        """Getting a channel by ID should work for members."""
        token = await self.get_auth_token(client)

        # Create a channel first
        create_response = await client.post(
            "/api/v1/channels",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Test Channel", "channel_type": "team"},
        )
        channel_id = create_response.json()["id"]

        # Get the channel
        response = await client.get(
            f"/api/v1/channels/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == channel_id
        assert data["name"] == "Test Channel"

    @pytest.mark.asyncio
    async def test_get_channel_not_member(self, client: AsyncClient, test_user: User, admin_user: User):
        """Getting a channel you're not a member of should fail."""
        admin_token = await self.get_admin_token(client)

        # Admin creates a private channel
        create_response = await client.post(
            "/api/v1/channels",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Private Channel", "channel_type": "team", "is_private": True},
        )
        channel_id = create_response.json()["id"]

        # Test user tries to get it
        token = await self.get_auth_token(client)
        response = await client.get(
            f"/api/v1/channels/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_channel(self, client: AsyncClient, test_user: User):
        """Updating a channel should work for creator."""
        token = await self.get_auth_token(client)

        # Create a channel
        create_response = await client.post(
            "/api/v1/channels",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Original Name", "channel_type": "team"},
        )
        channel_id = create_response.json()["id"]

        # Update the channel
        response = await client.patch(
            f"/api/v1/channels/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Updated Name", "description": "New description"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "New description"

    @pytest.mark.asyncio
    async def test_delete_channel(self, client: AsyncClient, test_user: User):
        """Deleting a channel should work for creator."""
        token = await self.get_auth_token(client)

        # Create a channel
        create_response = await client.post(
            "/api/v1/channels",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "To Delete", "channel_type": "team"},
        )
        channel_id = create_response.json()["id"]

        # Delete the channel
        response = await client.delete(
            f"/api/v1/channels/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_channel_not_creator(self, client: AsyncClient, test_user: User, admin_user: User):
        """Deleting a channel by non-creator should fail."""
        admin_token = await self.get_admin_token(client)

        # Admin creates a channel
        create_response = await client.post(
            "/api/v1/channels",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Admin Channel", "channel_type": "team", "member_ids": [str(test_user.id)]},
        )
        channel_id = create_response.json()["id"]

        # Test user tries to delete
        token = await self.get_auth_token(client)
        response = await client.delete(
            f"/api/v1/channels/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    # ==================== Member Management Tests ====================

    @pytest.mark.asyncio
    async def test_add_member(self, client: AsyncClient, test_user: User, admin_user: User):
        """Adding a member to a channel should work for admins."""
        token = await self.get_auth_token(client)

        # Create a channel
        create_response = await client.post(
            "/api/v1/channels",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Test Channel", "channel_type": "team"},
        )
        channel_id = create_response.json()["id"]

        # Add admin as member
        response = await client.post(
            f"/api/v1/channels/{channel_id}/members",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": str(admin_user.id), "is_admin": False},
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_remove_member(self, client: AsyncClient, test_user: User, admin_user: User):
        """Removing a member should work for admins."""
        token = await self.get_auth_token(client)

        # Create a channel with admin as member
        create_response = await client.post(
            "/api/v1/channels",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Test Channel", "channel_type": "team", "member_ids": [str(admin_user.id)]},
        )
        channel_id = create_response.json()["id"]

        # Remove admin
        response = await client.delete(
            f"/api/v1/channels/{channel_id}/members/{admin_user.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_leave_channel(self, client: AsyncClient, test_user: User):
        """Leaving a channel should work."""
        token = await self.get_auth_token(client)

        # Create a channel
        create_response = await client.post(
            "/api/v1/channels",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Test Channel", "channel_type": "team"},
        )
        channel_id = create_response.json()["id"]

        # Leave the channel
        response = await client.post(
            f"/api/v1/channels/{channel_id}/leave",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_mute_channel(self, client: AsyncClient, test_user: User):
        """Muting a channel should work for members."""
        token = await self.get_auth_token(client)

        # Create a channel
        create_response = await client.post(
            "/api/v1/channels",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Test Channel", "channel_type": "team"},
        )
        channel_id = create_response.json()["id"]

        # Mute the channel
        response = await client.post(
            f"/api/v1/channels/{channel_id}/mute?muted=true",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["muted"] is True

    # ==================== Validation Tests ====================

    @pytest.mark.asyncio
    async def test_create_channel_invalid_name(self, client: AsyncClient, test_user: User):
        """Creating a channel with empty name should fail."""
        token = await self.get_auth_token(client)

        response = await client.post(
            "/api/v1/channels",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "", "channel_type": "team"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_channel_not_found(self, client: AsyncClient, test_user: User):
        """Getting a non-existent channel should return 404."""
        token = await self.get_auth_token(client)

        response = await client.get(
            f"/api/v1/channels/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code in [403, 404]  # Either not member or not found
