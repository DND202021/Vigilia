"""Tests for notifications API endpoints."""

import uuid
import pytest
from httpx import AsyncClient

from app.models.user import User


class TestNotificationsAPI:
    """Tests for notifications API endpoints."""

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

    # ==================== Push Subscription Tests ====================

    @pytest.mark.asyncio
    async def test_subscribe_push(self, client: AsyncClient, test_user: User):
        """Subscribing to push notifications should work."""
        token = await self.get_auth_token(client)

        response = await client.post(
            "/api/v1/notifications/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "endpoint": "https://fcm.googleapis.com/fcm/send/test123",
                "keys": {
                    "p256dh": "test_public_key",
                    "auth": "test_auth_secret",
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "subscription_id" in data

    @pytest.mark.asyncio
    async def test_subscribe_push_no_auth(self, client: AsyncClient):
        """Subscribing without auth should fail."""
        response = await client.post(
            "/api/v1/notifications/subscribe",
            json={
                "endpoint": "https://fcm.googleapis.com/fcm/send/test123",
                "keys": {"p256dh": "key", "auth": "auth"},
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_unsubscribe_push(self, client: AsyncClient, test_user: User):
        """Unsubscribing from push notifications should work."""
        token = await self.get_auth_token(client)

        # First subscribe
        endpoint = "https://fcm.googleapis.com/fcm/send/test456"
        await client.post(
            "/api/v1/notifications/subscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "endpoint": endpoint,
                "keys": {"p256dh": "key", "auth": "auth"},
            },
        )

        # Then unsubscribe
        response = await client.post(
            "/api/v1/notifications/unsubscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"endpoint": endpoint},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_unsubscribe_not_found(self, client: AsyncClient, test_user: User):
        """Unsubscribing a non-existent subscription should return 404."""
        token = await self.get_auth_token(client)

        response = await client.post(
            "/api/v1/notifications/unsubscribe",
            headers={"Authorization": f"Bearer {token}"},
            json={"endpoint": "https://fcm.googleapis.com/fcm/send/nonexistent"},
        )

        assert response.status_code == 404

    # ==================== Get Notifications Tests ====================

    @pytest.mark.asyncio
    async def test_get_notifications(self, client: AsyncClient, test_user: User):
        """Getting notifications should work for authenticated users."""
        token = await self.get_auth_token(client)

        response = await client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_notifications_with_limit(self, client: AsyncClient, test_user: User):
        """Getting notifications with limit should work."""
        token = await self.get_auth_token(client)

        response = await client.get(
            "/api/v1/notifications?limit=10",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10

    @pytest.mark.asyncio
    async def test_get_notifications_no_auth(self, client: AsyncClient):
        """Getting notifications without auth should fail."""
        response = await client.get("/api/v1/notifications")
        assert response.status_code == 401

    # ==================== Mark Delivered/Clicked Tests ====================

    @pytest.mark.asyncio
    async def test_mark_notification_delivered(self, client: AsyncClient, test_user: User, admin_user: User):
        """Marking a notification as delivered should work."""
        admin_token = await self.get_admin_token(client)
        token = await self.get_auth_token(client)

        # Admin sends a notification to test user
        send_response = await client.post(
            "/api/v1/notifications/send",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "user_ids": [str(test_user.id)],
                "title": "Test Notification",
                "body": "Test body",
            },
        )

        if send_response.status_code == 200:
            notification_ids = send_response.json()["notification_ids"]
            if notification_ids:
                notification_id = notification_ids[0]

                # Mark as delivered
                response = await client.post(
                    f"/api/v1/notifications/{notification_id}/delivered",
                    headers={"Authorization": f"Bearer {token}"},
                )

                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_mark_notification_clicked(self, client: AsyncClient, test_user: User, admin_user: User):
        """Marking a notification as clicked should work."""
        admin_token = await self.get_admin_token(client)
        token = await self.get_auth_token(client)

        # Admin sends a notification to test user
        send_response = await client.post(
            "/api/v1/notifications/send",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "user_ids": [str(test_user.id)],
                "title": "Test Notification",
                "body": "Test body",
            },
        )

        if send_response.status_code == 200:
            notification_ids = send_response.json()["notification_ids"]
            if notification_ids:
                notification_id = notification_ids[0]

                # Mark as clicked
                response = await client.post(
                    f"/api/v1/notifications/{notification_id}/clicked",
                    headers={"Authorization": f"Bearer {token}"},
                )

                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_mark_notification_invalid_id(self, client: AsyncClient, test_user: User):
        """Marking a notification with invalid ID should fail."""
        token = await self.get_auth_token(client)

        response = await client.post(
            "/api/v1/notifications/invalid-id/delivered",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_mark_notification_not_found(self, client: AsyncClient, test_user: User):
        """Marking a non-existent notification should return 404."""
        token = await self.get_auth_token(client)

        response = await client.post(
            f"/api/v1/notifications/{uuid.uuid4()}/delivered",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    # ==================== Send Notification Tests (Admin) ====================

    @pytest.mark.asyncio
    async def test_send_notification_as_admin(self, client: AsyncClient, admin_user: User, test_user: User):
        """Admins should be able to send notifications."""
        token = await self.get_admin_token(client)

        response = await client.post(
            "/api/v1/notifications/send",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_ids": [str(test_user.id)],
                "title": "Admin Notification",
                "body": "This is a test notification from admin",
                "notification_type": "system",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "notification_ids" in data

    @pytest.mark.asyncio
    async def test_send_notification_as_regular_user(self, client: AsyncClient, test_user: User, admin_user: User):
        """Regular users should not be able to send notifications."""
        token = await self.get_auth_token(client)

        response = await client.post(
            "/api/v1/notifications/send",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_ids": [str(admin_user.id)],
                "title": "Test",
                "body": "Test",
            },
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_send_notification_invalid_user_id(self, client: AsyncClient, admin_user: User):
        """Sending notification with invalid user ID should fail."""
        token = await self.get_admin_token(client)

        response = await client.post(
            "/api/v1/notifications/send",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_ids": ["not-a-uuid"],
                "title": "Test",
                "body": "Test",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_send_notification_multiple_users(self, client: AsyncClient, admin_user: User, test_user: User):
        """Sending notification to multiple users should work."""
        token = await self.get_admin_token(client)

        response = await client.post(
            "/api/v1/notifications/send",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_ids": [str(test_user.id), str(admin_user.id)],
                "title": "Broadcast",
                "body": "Test broadcast notification",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["notification_ids"]) == 2
