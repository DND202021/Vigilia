"""Tests for channels API endpoints."""

import uuid
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient

from app.models.user import User
from app.models.channel import Channel, ChannelMember, ChannelType


class TestChannelsAPI:
    """Tests for channels API endpoints."""

    @pytest.mark.asyncio
    async def test_list_channels_not_authenticated(self, client: AsyncClient):
        """Test listing channels without authentication."""
        response = await client.get("/api/v1/channels")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_channels_empty(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test listing channels when user has none."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            "/api/v1/channels",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_create_channel_success(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test creating a new channel."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        response = await client.post(
            "/api/v1/channels",
            json={
                "name": "Test Channel",
                "description": "A test channel",
                "channel_type": "team",
                "is_private": False,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Channel"
        assert data["description"] == "A test channel"
        assert data["channel_type"] == "team"
        assert data["is_private"] is False
        assert len(data["members"]) == 1  # Creator is member

    @pytest.mark.asyncio
    async def test_create_channel_private(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test creating a private channel."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        response = await client.post(
            "/api/v1/channels",
            json={
                "name": "Private Channel",
                "channel_type": "team",
                "is_private": True,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        assert response.json()["is_private"] is True

    @pytest.mark.asyncio
    async def test_create_direct_channel_success(
        self, client: AsyncClient, test_user: User, admin_user: User, db_session
    ):
        """Test creating a direct message channel."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        response = await client.post(
            "/api/v1/channels/direct",
            json={"user_id": str(admin_user.id)},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["channel_type"] == "direct"
        assert len(data["members"]) == 2

    @pytest.mark.asyncio
    async def test_create_direct_channel_with_self(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test creating DM with self fails."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        response = await client.post(
            "/api/v1/channels/direct",
            json={"user_id": str(test_user.id)},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "yourself" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_channel_success(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test getting a channel."""
        # Login and create channel first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        create_response = await client.post(
            "/api/v1/channels",
            json={"name": "Get Test Channel", "channel_type": "team"},
            headers={"Authorization": f"Bearer {token}"},
        )
        channel_id = create_response.json()["id"]

        # Get the channel
        response = await client.get(
            f"/api/v1/channels/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Get Test Channel"

    @pytest.mark.asyncio
    async def test_get_channel_not_member(
        self, client: AsyncClient, test_user: User, admin_user: User, db_session
    ):
        """Test getting a channel when not a member."""
        # Login as admin and create channel
        admin_login = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin@example.com", "password": "AdminPassword123!"},
        )
        admin_token = admin_login.json()["access_token"]

        create_response = await client.post(
            "/api/v1/channels",
            json={"name": "Admin Channel", "channel_type": "team", "is_private": True},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        channel_id = create_response.json()["id"]

        # Login as regular user
        user_login = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        user_token = user_login.json()["access_token"]

        # Try to get admin's channel
        response = await client.get(
            f"/api/v1/channels/{channel_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_channel_success(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test updating a channel."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        create_response = await client.post(
            "/api/v1/channels",
            json={"name": "Original Name", "channel_type": "team"},
            headers={"Authorization": f"Bearer {token}"},
        )
        channel_id = create_response.json()["id"]

        # Update the channel
        response = await client.patch(
            f"/api/v1/channels/{channel_id}",
            json={"name": "Updated Name", "description": "New description"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
        assert response.json()["description"] == "New description"

    @pytest.mark.asyncio
    async def test_archive_channel(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test archiving a channel."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        create_response = await client.post(
            "/api/v1/channels",
            json={"name": "To Archive", "channel_type": "team"},
            headers={"Authorization": f"Bearer {token}"},
        )
        channel_id = create_response.json()["id"]

        # Archive the channel
        response = await client.patch(
            f"/api/v1/channels/{channel_id}",
            json={"is_archived": True},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["is_archived"] is True

    @pytest.mark.asyncio
    async def test_delete_channel_success(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test deleting a channel."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        create_response = await client.post(
            "/api/v1/channels",
            json={"name": "To Delete", "channel_type": "team"},
            headers={"Authorization": f"Bearer {token}"},
        )
        channel_id = create_response.json()["id"]

        # Delete the channel
        response = await client.delete(
            f"/api/v1/channels/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_add_member_success(
        self, client: AsyncClient, test_user: User, admin_user: User, db_session
    ):
        """Test adding a member to a channel."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        create_response = await client.post(
            "/api/v1/channels",
            json={"name": "Add Member Test", "channel_type": "team"},
            headers={"Authorization": f"Bearer {token}"},
        )
        channel_id = create_response.json()["id"]

        # Add admin as member
        response = await client.post(
            f"/api/v1/channels/{channel_id}/members",
            json={"user_id": str(admin_user.id), "is_admin": False},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_remove_member_success(
        self, client: AsyncClient, test_user: User, admin_user: User, db_session
    ):
        """Test removing a member from a channel."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        create_response = await client.post(
            "/api/v1/channels",
            json={
                "name": "Remove Member Test",
                "channel_type": "team",
                "member_ids": [str(admin_user.id)],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        channel_id = create_response.json()["id"]

        # Remove admin
        response = await client.delete(
            f"/api/v1/channels/{channel_id}/members/{admin_user.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_leave_channel_success(
        self, client: AsyncClient, test_user: User, admin_user: User, db_session
    ):
        """Test leaving a channel."""
        # Admin creates channel
        admin_login = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin@example.com", "password": "AdminPassword123!"},
        )
        admin_token = admin_login.json()["access_token"]

        create_response = await client.post(
            "/api/v1/channels",
            json={
                "name": "Leave Test",
                "channel_type": "team",
                "member_ids": [str(test_user.id)],
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        channel_id = create_response.json()["id"]

        # User leaves
        user_login = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        user_token = user_login.json()["access_token"]

        response = await client.post(
            f"/api/v1/channels/{channel_id}/leave",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_mute_channel_success(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test muting a channel."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        create_response = await client.post(
            "/api/v1/channels",
            json={"name": "Mute Test", "channel_type": "team"},
            headers={"Authorization": f"Bearer {token}"},
        )
        channel_id = create_response.json()["id"]

        # Mute channel
        response = await client.post(
            f"/api/v1/channels/{channel_id}/mute?muted=true",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["muted"] is True

    @pytest.mark.asyncio
    async def test_unmute_channel_success(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test unmuting a channel."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        create_response = await client.post(
            "/api/v1/channels",
            json={"name": "Unmute Test", "channel_type": "team"},
            headers={"Authorization": f"Bearer {token}"},
        )
        channel_id = create_response.json()["id"]

        # Unmute channel
        response = await client.post(
            f"/api/v1/channels/{channel_id}/mute?muted=false",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["muted"] is False

    @pytest.mark.asyncio
    async def test_list_channels_with_type_filter(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test listing channels with type filter."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        # Create team channel
        await client.post(
            "/api/v1/channels",
            json={"name": "Team Channel", "channel_type": "team"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # List only team channels
        response = await client.get(
            "/api/v1/channels?channel_type=team",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert all(c["channel_type"] == "team" for c in data)
