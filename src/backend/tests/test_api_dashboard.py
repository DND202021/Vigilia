"""Tests for dashboard API endpoints."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.incident import Incident, IncidentStatus, IncidentPriority, IncidentCategory
from app.models.alert import Alert, AlertStatus, AlertSeverity, AlertSource
from app.models.resource import Resource, ResourceType, ResourceStatus


class TestDashboardAPI:
    """Tests for dashboard API endpoints."""

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

    # ==================== Dashboard Stats Tests ====================

    @pytest.mark.asyncio
    async def test_get_dashboard_stats(self, client: AsyncClient, test_user: User):
        """Getting dashboard stats should work for authenticated users."""
        token = await self.get_auth_token(client)

        response = await client.get(
            "/api/v1/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "active_incidents" in data
        assert "pending_alerts" in data
        assert "available_resources" in data
        assert "total_resources" in data

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_no_auth(self, client: AsyncClient):
        """Getting dashboard stats without auth should fail."""
        response = await client.get("/api/v1/dashboard/stats")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_dashboard_stats_with_data(
        self,
        client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Dashboard stats should reflect actual data."""
        token = await self.get_auth_token(client)

        # Create test data
        # Active incident
        incident = Incident(
            id=uuid.uuid4(),
            agency_id=test_user.agency_id,
            status=IncidentStatus.NEW,
            priority=IncidentPriority.HIGH,
            category=IncidentCategory.FIRE,
            title="Test Incident",
            description="Test",
        )
        db_session.add(incident)

        # Pending alert
        alert = Alert(
            id=uuid.uuid4(),
            agency_id=test_user.agency_id,
            source=AlertSource.MANUAL,
            severity=AlertSeverity.HIGH,
            status=AlertStatus.PENDING,
            alert_type="test",
            title="Test Alert",
        )
        db_session.add(alert)

        # Available resource
        resource = Resource(
            id=uuid.uuid4(),
            agency_id=test_user.agency_id,
            resource_type=ResourceType.PERSONNEL,
            name="Test Resource",
            status=ResourceStatus.AVAILABLE,
        )
        db_session.add(resource)

        await db_session.commit()

        # Get stats
        response = await client.get(
            "/api/v1/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["active_incidents"] >= 1
        assert data["pending_alerts"] >= 1
        assert data["available_resources"] >= 1
        assert data["total_resources"] >= 1

    @pytest.mark.asyncio
    async def test_dashboard_stats_empty(self, client: AsyncClient, test_user: User):
        """Dashboard stats should return zeros when no data."""
        token = await self.get_auth_token(client)

        response = await client.get(
            "/api/v1/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["active_incidents"], int)
        assert isinstance(data["pending_alerts"], int)
        assert isinstance(data["available_resources"], int)
        assert isinstance(data["total_resources"], int)
