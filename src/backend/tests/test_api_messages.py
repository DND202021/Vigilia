"""Tests for messages API endpoints."""

import uuid
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from app.models.user import User
from app.models.channel import Channel, ChannelMember, ChannelType


class TestMessagesAPI:
    """Tests for messages API endpoints."""

    @pytest.mark.asyncio
    async def test_get_channel_messages_not_authenticated(self, client: AsyncClient):
        """Test getting messages without authentication."""
        channel_id = uuid.uuid4()
        response = await client.get(f"/api/v1/messages/channel/{channel_id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_send_message_success(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test sending a message to a channel."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        # Create a channel first
        channel_response = await client.post(
            "/api/v1/channels",
            json={"name": "Message Test Channel", "channel_type": "team"},
            headers={"Authorization": f"Bearer {token}"},
        )
        channel_id = channel_response.json()["id"]

        # Send a message
        with patch("app.api.messages.sio") as mock_sio:
            mock_sio.emit = AsyncMock()
            response = await client.post(
                f"/api/v1/messages/channel/{channel_id}",
                json={
                    "content": "Hello, world!",
                    "message_type": "text",
                    "priority": "normal",
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "Hello, world!"
        assert data["message_type"] == "text"
        assert data["priority"] == "normal"

    @pytest.mark.asyncio
    async def test_send_message_not_member(
        self, client: AsyncClient, test_user: User, admin_user: User, db_session
    ):
        """Test sending message to channel user is not member of."""
        # Admin creates a channel
        admin_login = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin@example.com", "password": "AdminPassword123!"},
        )
        admin_token = admin_login.json()["access_token"]

        channel_response = await client.post(
            "/api/v1/channels",
            json={"name": "Admin Only Channel", "channel_type": "team", "is_private": True},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        channel_id = channel_response.json()["id"]

        # Regular user tries to send message
        user_login = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        user_token = user_login.json()["access_token"]

        response = await client.post(
            f"/api/v1/messages/channel/{channel_id}",
            json={"content": "Hello!"},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_send_message_with_location(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test sending a message with location data."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        # Create channel
        channel_response = await client.post(
            "/api/v1/channels",
            json={"name": "Location Test Channel", "channel_type": "team"},
            headers={"Authorization": f"Bearer {token}"},
        )
        channel_id = channel_response.json()["id"]

        # Send message with location
        with patch("app.api.messages.sio") as mock_sio:
            mock_sio.emit = AsyncMock()
            response = await client.post(
                f"/api/v1/messages/channel/{channel_id}",
                json={
                    "content": "I am here",
                    "message_type": "location",
                    "location_lat": 45.5017,
                    "location_lng": -73.5673,
                    "location_address": "123 Test St, Montreal",
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["location_lat"] == 45.5017
        assert data["location_lng"] == -73.5673
        assert data["location_address"] == "123 Test St, Montreal"

    @pytest.mark.asyncio
    async def test_get_channel_messages_success(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test getting messages from a channel."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        # Create channel
        channel_response = await client.post(
            "/api/v1/channels",
            json={"name": "Get Messages Test", "channel_type": "team"},
            headers={"Authorization": f"Bearer {token}"},
        )
        channel_id = channel_response.json()["id"]

        # Send a message
        with patch("app.api.messages.sio") as mock_sio:
            mock_sio.emit = AsyncMock()
            await client.post(
                f"/api/v1/messages/channel/{channel_id}",
                json={"content": "Test message"},
                headers={"Authorization": f"Bearer {token}"},
            )

        # Get messages
        response = await client.get(
            f"/api/v1/messages/channel/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["content"] == "Test message"

    @pytest.mark.asyncio
    async def test_edit_message_success(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test editing a message."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        # Create channel and send message
        channel_response = await client.post(
            "/api/v1/channels",
            json={"name": "Edit Test Channel", "channel_type": "team"},
            headers={"Authorization": f"Bearer {token}"},
        )
        channel_id = channel_response.json()["id"]

        with patch("app.api.messages.sio") as mock_sio:
            mock_sio.emit = AsyncMock()
            msg_response = await client.post(
                f"/api/v1/messages/channel/{channel_id}",
                json={"content": "Original content"},
                headers={"Authorization": f"Bearer {token}"},
            )
        message_id = msg_response.json()["id"]

        # Edit the message
        with patch("app.api.messages.sio") as mock_sio:
            mock_sio.emit = AsyncMock()
            response = await client.patch(
                f"/api/v1/messages/{message_id}",
                json={"content": "Edited content"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Edited content"
        assert data["is_edited"] is True

    @pytest.mark.asyncio
    async def test_delete_message_success(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test deleting a message."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        # Create channel and send message
        channel_response = await client.post(
            "/api/v1/channels",
            json={"name": "Delete Test Channel", "channel_type": "team"},
            headers={"Authorization": f"Bearer {token}"},
        )
        channel_id = channel_response.json()["id"]

        with patch("app.api.messages.sio") as mock_sio:
            mock_sio.emit = AsyncMock()
            msg_response = await client.post(
                f"/api/v1/messages/channel/{channel_id}",
                json={"content": "To be deleted"},
                headers={"Authorization": f"Bearer {token}"},
            )
        message_id = msg_response.json()["id"]

        # Delete the message
        with patch("app.api.messages.sio") as mock_sio:
            mock_sio.emit = AsyncMock()
            response = await client.delete(
                f"/api/v1/messages/{message_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_mark_as_read_success(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test marking messages as read."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        # Create channel
        channel_response = await client.post(
            "/api/v1/channels",
            json={"name": "Read Test Channel", "channel_type": "team"},
            headers={"Authorization": f"Bearer {token}"},
        )
        channel_id = channel_response.json()["id"]

        # Mark as read
        response = await client.post(
            f"/api/v1/messages/channel/{channel_id}/read",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Marked as read"

    @pytest.mark.asyncio
    async def test_get_unread_count(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test getting unread message counts."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            "/api/v1/messages/unread/count",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_channel" in data

    @pytest.mark.asyncio
    async def test_search_messages_success(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test searching messages."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        # Create channel and send message
        channel_response = await client.post(
            "/api/v1/channels",
            json={"name": "Search Test Channel", "channel_type": "team"},
            headers={"Authorization": f"Bearer {token}"},
        )
        channel_id = channel_response.json()["id"]

        with patch("app.api.messages.sio") as mock_sio:
            mock_sio.emit = AsyncMock()
            await client.post(
                f"/api/v1/messages/channel/{channel_id}",
                json={"content": "Finding this specific message"},
                headers={"Authorization": f"Bearer {token}"},
            )

        # Search
        response = await client.get(
            "/api/v1/messages/search?query=specific",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        # Search results may vary based on implementation

    @pytest.mark.asyncio
    async def test_add_reaction_success(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test adding a reaction to a message."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        # Create channel and send message
        channel_response = await client.post(
            "/api/v1/channels",
            json={"name": "Reaction Test Channel", "channel_type": "team"},
            headers={"Authorization": f"Bearer {token}"},
        )
        channel_id = channel_response.json()["id"]

        with patch("app.api.messages.sio") as mock_sio:
            mock_sio.emit = AsyncMock()
            msg_response = await client.post(
                f"/api/v1/messages/channel/{channel_id}",
                json={"content": "React to this"},
                headers={"Authorization": f"Bearer {token}"},
            )
        message_id = msg_response.json()["id"]

        # Add reaction
        with patch("app.api.messages.sio") as mock_sio:
            mock_sio.emit = AsyncMock()
            response = await client.post(
                f"/api/v1/messages/{message_id}/reactions",
                json={"emoji": "thumbsup"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_remove_reaction_success(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test removing a reaction from a message."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        # Create channel and send message
        channel_response = await client.post(
            "/api/v1/channels",
            json={"name": "Remove Reaction Test", "channel_type": "team"},
            headers={"Authorization": f"Bearer {token}"},
        )
        channel_id = channel_response.json()["id"]

        with patch("app.api.messages.sio") as mock_sio:
            mock_sio.emit = AsyncMock()
            msg_response = await client.post(
                f"/api/v1/messages/channel/{channel_id}",
                json={"content": "React and remove"},
                headers={"Authorization": f"Bearer {token}"},
            )
        message_id = msg_response.json()["id"]

        # Add then remove reaction
        with patch("app.api.messages.sio") as mock_sio:
            mock_sio.emit = AsyncMock()
            await client.post(
                f"/api/v1/messages/{message_id}/reactions",
                json={"emoji": "heart"},
                headers={"Authorization": f"Bearer {token}"},
            )

        with patch("app.api.messages.sio") as mock_sio:
            mock_sio.emit = AsyncMock()
            response = await client.delete(
                f"/api/v1/messages/{message_id}/reactions/heart",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_send_priority_message(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test sending an urgent message."""
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        channel_response = await client.post(
            "/api/v1/channels",
            json={"name": "Priority Test Channel", "channel_type": "team"},
            headers={"Authorization": f"Bearer {token}"},
        )
        channel_id = channel_response.json()["id"]

        with patch("app.api.messages.sio") as mock_sio:
            mock_sio.emit = AsyncMock()
            response = await client.post(
                f"/api/v1/messages/channel/{channel_id}",
                json={
                    "content": "URGENT: This is urgent!",
                    "priority": "urgent",
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 201
        assert response.json()["priority"] == "urgent"
