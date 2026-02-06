"""Tests for messages API endpoints."""

import uuid
import pytest
from httpx import AsyncClient

from app.models.user import User


class TestMessagesAPI:
    """Tests for messages API endpoints."""

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

    async def create_test_channel(self, client: AsyncClient, token: str) -> str:
        """Helper to create a test channel and return its ID."""
        response = await client.post(
            "/api/v1/channels",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Test Channel", "channel_type": "team"},
        )
        return response.json()["id"]

    # ==================== Message CRUD Tests ====================

    @pytest.mark.asyncio
    async def test_send_message(self, client: AsyncClient, test_user: User):
        """Sending a message should work for channel members."""
        token = await self.get_auth_token(client)
        channel_id = await self.create_test_channel(client, token)

        response = await client.post(
            f"/api/v1/messages/channel/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "content": "Hello, world!",
                "message_type": "text",
                "priority": "normal",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "Hello, world!"
        assert data["message_type"] == "text"
        assert data["sender_id"] == str(test_user.id)

    @pytest.mark.asyncio
    async def test_send_message_no_auth(self, client: AsyncClient, test_user: User):
        """Sending a message without auth should fail."""
        token = await self.get_auth_token(client)
        channel_id = await self.create_test_channel(client, token)

        response = await client.post(
            f"/api/v1/messages/channel/{channel_id}",
            json={"content": "Test message"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_send_message_not_member(self, client: AsyncClient, test_user: User, admin_user: User):
        """Sending a message to a channel you're not in should fail."""
        admin_token = await self.get_admin_token(client)
        channel_id = await self.create_test_channel(client, admin_token)

        # Test user tries to send
        token = await self.get_auth_token(client)
        response = await client.post(
            f"/api/v1/messages/channel/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "Test message"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_channel_messages(self, client: AsyncClient, test_user: User):
        """Getting channel messages should work for members."""
        token = await self.get_auth_token(client)
        channel_id = await self.create_test_channel(client, token)

        # Send a message first
        await client.post(
            f"/api/v1/messages/channel/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "Test message"},
        )

        # Get messages
        response = await client.get(
            f"/api/v1/messages/channel/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["content"] == "Test message"

    @pytest.mark.asyncio
    async def test_get_channel_messages_with_limit(self, client: AsyncClient, test_user: User):
        """Getting messages with limit should work."""
        token = await self.get_auth_token(client)
        channel_id = await self.create_test_channel(client, token)

        # Send multiple messages
        for i in range(5):
            await client.post(
                f"/api/v1/messages/channel/{channel_id}",
                headers={"Authorization": f"Bearer {token}"},
                json={"content": f"Message {i}"},
            )

        # Get messages with limit
        response = await client.get(
            f"/api/v1/messages/channel/{channel_id}?limit=3",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 3

    @pytest.mark.asyncio
    async def test_get_message(self, client: AsyncClient, test_user: User):
        """Getting a specific message should work."""
        token = await self.get_auth_token(client)
        channel_id = await self.create_test_channel(client, token)

        # Send a message
        send_response = await client.post(
            f"/api/v1/messages/channel/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "Test message"},
        )
        message_id = send_response.json()["id"]

        # Get the message
        response = await client.get(
            f"/api/v1/messages/{message_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == message_id
        assert data["content"] == "Test message"

    @pytest.mark.asyncio
    async def test_edit_message(self, client: AsyncClient, test_user: User):
        """Editing your own message should work."""
        token = await self.get_auth_token(client)
        channel_id = await self.create_test_channel(client, token)

        # Send a message
        send_response = await client.post(
            f"/api/v1/messages/channel/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "Original message"},
        )
        message_id = send_response.json()["id"]

        # Edit the message
        response = await client.patch(
            f"/api/v1/messages/{message_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "Edited message"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Edited message"
        assert data["is_edited"] is True

    @pytest.mark.asyncio
    async def test_edit_message_not_sender(self, client: AsyncClient, test_user: User, admin_user: User):
        """Editing someone else's message should fail."""
        token = await self.get_auth_token(client)
        channel_id = await self.create_test_channel(client, token)

        # Test user sends a message
        send_response = await client.post(
            f"/api/v1/messages/channel/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "Test message"},
        )
        message_id = send_response.json()["id"]

        # Add admin to channel
        await client.post(
            f"/api/v1/channels/{channel_id}/members",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": str(admin_user.id)},
        )

        # Admin tries to edit
        admin_token = await self.get_admin_token(client)
        response = await client.patch(
            f"/api/v1/messages/{message_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"content": "Hacked message"},
        )

        assert response.status_code == 404  # Not authorized

    @pytest.mark.asyncio
    async def test_delete_message(self, client: AsyncClient, test_user: User):
        """Deleting your own message should work."""
        token = await self.get_auth_token(client)
        channel_id = await self.create_test_channel(client, token)

        # Send a message
        send_response = await client.post(
            f"/api/v1/messages/channel/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "To delete"},
        )
        message_id = send_response.json()["id"]

        # Delete the message
        response = await client.delete(
            f"/api/v1/messages/{message_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_message_as_admin(self, client: AsyncClient, test_user: User, admin_user: User):
        """Channel admins should be able to delete any message."""
        token = await self.get_auth_token(client)
        channel_id = await self.create_test_channel(client, token)

        # Test user sends a message
        send_response = await client.post(
            f"/api/v1/messages/channel/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "Test message"},
        )
        message_id = send_response.json()["id"]

        # Add admin to channel as admin
        await client.post(
            f"/api/v1/channels/{channel_id}/members",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": str(admin_user.id), "is_admin": True},
        )

        # Admin deletes the message
        admin_token = await self.get_admin_token(client)
        response = await client.delete(
            f"/api/v1/messages/{message_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 204

    # ==================== Mark as Read Tests ====================

    @pytest.mark.asyncio
    async def test_mark_as_read(self, client: AsyncClient, test_user: User):
        """Marking messages as read should work."""
        token = await self.get_auth_token(client)
        channel_id = await self.create_test_channel(client, token)

        # Send a message
        await client.post(
            f"/api/v1/messages/channel/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "Test message"},
        )

        # Mark as read
        response = await client.post(
            f"/api/v1/messages/channel/{channel_id}/read",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_unread_count(self, client: AsyncClient, test_user: User):
        """Getting unread count should work."""
        token = await self.get_auth_token(client)

        response = await client.get(
            "/api/v1/messages/unread/count",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_channel" in data

    # ==================== Search Tests ====================

    @pytest.mark.asyncio
    async def test_search_messages(self, client: AsyncClient, test_user: User):
        """Searching messages should work."""
        token = await self.get_auth_token(client)
        channel_id = await self.create_test_channel(client, token)

        # Send a message with searchable content
        await client.post(
            f"/api/v1/messages/channel/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "Find this unique string xyz123"},
        )

        # Search for it
        response = await client.get(
            "/api/v1/messages/search?query=xyz123",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    # ==================== Reaction Tests ====================

    @pytest.mark.asyncio
    async def test_add_reaction(self, client: AsyncClient, test_user: User):
        """Adding a reaction should work."""
        token = await self.get_auth_token(client)
        channel_id = await self.create_test_channel(client, token)

        # Send a message
        send_response = await client.post(
            f"/api/v1/messages/channel/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "React to this"},
        )
        message_id = send_response.json()["id"]

        # Add reaction
        response = await client.post(
            f"/api/v1/messages/{message_id}/reactions",
            headers={"Authorization": f"Bearer {token}"},
            json={"emoji": "👍"},
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_remove_reaction(self, client: AsyncClient, test_user: User):
        """Removing a reaction should work."""
        token = await self.get_auth_token(client)
        channel_id = await self.create_test_channel(client, token)

        # Send a message
        send_response = await client.post(
            f"/api/v1/messages/channel/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "React to this"},
        )
        message_id = send_response.json()["id"]

        # Add and remove reaction
        await client.post(
            f"/api/v1/messages/{message_id}/reactions",
            headers={"Authorization": f"Bearer {token}"},
            json={"emoji": "👍"},
        )

        response = await client.delete(
            f"/api/v1/messages/{message_id}/reactions/👍",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 204

    # ==================== Validation Tests ====================

    @pytest.mark.asyncio
    async def test_send_message_empty_content(self, client: AsyncClient, test_user: User):
        """Sending a message with empty content should fail."""
        token = await self.get_auth_token(client)
        channel_id = await self.create_test_channel(client, token)

        response = await client.post(
            f"/api/v1/messages/channel/{channel_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": ""},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_message_not_found(self, client: AsyncClient, test_user: User):
        """Getting a non-existent message should return 404."""
        token = await self.get_auth_token(client)

        response = await client.get(
            f"/api/v1/messages/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
