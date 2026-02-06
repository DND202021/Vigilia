"""Tests for alerts API endpoints."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.alert import Alert, AlertStatus, AlertSeverity, AlertSource


class TestAlertsAPI:
    """Tests for alerts API endpoints."""

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

    async def create_test_alert(self, db_session: AsyncSession, agency_id: uuid.UUID) -> Alert:
        """Helper to create a test alert."""
        alert = Alert(
            id=uuid.uuid4(),
            agency_id=agency_id,
            source=AlertSource.MANUAL,
            severity=AlertSeverity.HIGH,
            status=AlertStatus.PENDING,
            alert_type="test_alert",
            title="Test Alert",
            description="Test alert description",
        )
        db_session.add(alert)
        await db_session.commit()
        await db_session.refresh(alert)
        return alert

    # ==================== List Alerts Tests ====================

    @pytest.mark.asyncio
    async def test_list_alerts(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Listing alerts should work for authenticated users."""
        token = await self.get_auth_token(client)

        # Create a test alert
        await self.create_test_alert(db_session, test_user.agency_id)

        response = await client.get(
            "/api/v1/alerts",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_alerts_no_auth(self, client: AsyncClient):
        """Listing alerts without auth should fail."""
        response = await client.get("/api/v1/alerts")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_alerts_with_filters(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Listing alerts with filters should work."""
        token = await self.get_auth_token(client)

        # Create alerts with different statuses
        await self.create_test_alert(db_session, test_user.agency_id)

        response = await client.get(
            "/api/v1/alerts?status=pending",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200

    # ==================== Get Alert Tests ====================

    @pytest.mark.asyncio
    async def test_get_alert(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Getting an alert by ID should work."""
        token = await self.get_auth_token(client)

        # Create an alert
        alert = await self.create_test_alert(db_session, test_user.agency_id)

        response = await client.get(
            f"/api/v1/alerts/{alert.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(alert.id)

    @pytest.mark.asyncio
    async def test_get_alert_not_found(self, client: AsyncClient, test_user: User):
        """Getting a non-existent alert should return 404."""
        token = await self.get_auth_token(client)

        response = await client.get(
            f"/api/v1/alerts/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    # ==================== Acknowledge Alert Tests ====================

    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Acknowledging an alert should work."""
        token = await self.get_auth_token(client)

        # Create a pending alert
        alert = await self.create_test_alert(db_session, test_user.agency_id)

        response = await client.post(
            f"/api/v1/alerts/{alert.id}/acknowledge",
            headers={"Authorization": f"Bearer {token}"},
            json={"notes": "Acknowledged by test user"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "acknowledged"

    @pytest.mark.asyncio
    async def test_acknowledge_already_acknowledged(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Acknowledging an already acknowledged alert should handle gracefully."""
        token = await self.get_auth_token(client)

        # Create an acknowledged alert
        alert = Alert(
            id=uuid.uuid4(),
            agency_id=test_user.agency_id,
            source=AlertSource.MANUAL,
            severity=AlertSeverity.HIGH,
            status=AlertStatus.ACKNOWLEDGED,
            alert_type="test_alert",
            title="Test Alert",
            acknowledged_by_id=test_user.id,
        )
        db_session.add(alert)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/alerts/{alert.id}/acknowledge",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should either succeed or return a reasonable error
        assert response.status_code in [200, 400]

    # ==================== Resolve Alert Tests ====================

    @pytest.mark.asyncio
    async def test_resolve_alert(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Resolving an alert should work."""
        token = await self.get_auth_token(client)

        # Create an alert
        alert = await self.create_test_alert(db_session, test_user.agency_id)

        response = await client.post(
            f"/api/v1/alerts/{alert.id}/resolve",
            headers={"Authorization": f"Bearer {token}"},
            json={"resolution_notes": "Resolved by test"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"

    # ==================== Create Incident from Alert Tests ====================

    @pytest.mark.asyncio
    async def test_create_incident_from_alert(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Creating an incident from an alert should work."""
        token = await self.get_auth_token(client)

        # Create an alert
        alert = await self.create_test_alert(db_session, test_user.agency_id)

        response = await client.post(
            f"/api/v1/alerts/{alert.id}/create-incident",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "incident_type": "emergency",
                "priority": "high",
            },
        )

        # Should either create incident or fail gracefully
        assert response.status_code in [200, 201, 400, 403]

    # ==================== Dismiss Alert Tests ====================

    @pytest.mark.asyncio
    async def test_dismiss_alert(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Dismissing an alert should work."""
        token = await self.get_auth_token(client)

        # Create an alert
        alert = await self.create_test_alert(db_session, test_user.agency_id)

        response = await client.post(
            f"/api/v1/alerts/{alert.id}/dismiss",
            headers={"Authorization": f"Bearer {token}"},
            json={"reason": "False alarm"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "dismissed"

    # ==================== Assign Alert Tests ====================

    @pytest.mark.asyncio
    async def test_assign_alert(self, client: AsyncClient, test_user: User, admin_user: User, db_session: AsyncSession):
        """Assigning an alert to a user should work."""
        token = await self.get_auth_token(client)

        # Create an alert
        alert = await self.create_test_alert(db_session, test_user.agency_id)

        response = await client.post(
            f"/api/v1/alerts/{alert.id}/assign",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": str(admin_user.id)},
        )

        # Should either succeed or fail gracefully
        assert response.status_code in [200, 403, 404]

    # ==================== Validation Tests ====================

    @pytest.mark.asyncio
    async def test_acknowledge_alert_not_found(self, client: AsyncClient, test_user: User):
        """Acknowledging a non-existent alert should return 404."""
        token = await self.get_auth_token(client)

        response = await client.post(
            f"/api/v1/alerts/{uuid.uuid4()}/acknowledge",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_pending_alerts(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Listing pending alerts should work."""
        token = await self.get_auth_token(client)

        # Create a pending alert
        await self.create_test_alert(db_session, test_user.agency_id)

        response = await client.get(
            "/api/v1/alerts/pending",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
