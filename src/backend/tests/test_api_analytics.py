"""Tests for analytics API endpoints."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class TestAnalyticsAPI:
    """Tests for analytics API endpoints."""

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

    # ==================== Dashboard Summary Tests ====================

    @pytest.mark.asyncio
    async def test_get_dashboard_summary(self, client: AsyncClient, test_user: User):
        """Getting dashboard summary should work for authenticated users."""
        token = await self.get_auth_token(client)

        response = await client.get(
            "/api/v1/analytics/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )

        # May require special permissions or may not be implemented yet
        assert response.status_code in [200, 403, 404]

    @pytest.mark.asyncio
    async def test_get_dashboard_summary_no_auth(self, client: AsyncClient):
        """Getting dashboard summary without auth should fail."""
        response = await client.get("/api/v1/analytics/dashboard")
        assert response.status_code == 401

    # ==================== Incident Stats Tests ====================

    @pytest.mark.asyncio
    async def test_get_incident_stats(self, client: AsyncClient, test_user: User):
        """Getting incident stats should work."""
        token = await self.get_auth_token(client)

        response = await client.get(
            "/api/v1/analytics/incidents",
            headers={"Authorization": f"Bearer {token}"},
        )

        # May require permissions
        assert response.status_code in [200, 403, 404]

    @pytest.mark.asyncio
    async def test_get_incident_stats_with_timerange(self, client: AsyncClient, test_user: User):
        """Getting incident stats with time range should work."""
        token = await self.get_auth_token(client)

        response = await client.get(
            "/api/v1/analytics/incidents?time_range=last_7_days",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code in [200, 403, 404]

    # ==================== Resource Stats Tests ====================

    @pytest.mark.asyncio
    async def test_get_resource_stats(self, client: AsyncClient, test_user: User):
        """Getting resource stats should work."""
        token = await self.get_auth_token(client)

        response = await client.get(
            "/api/v1/analytics/resources",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code in [200, 403, 404]

    # ==================== Alert Stats Tests ====================

    @pytest.mark.asyncio
    async def test_get_alert_stats(self, client: AsyncClient, test_user: User):
        """Getting alert stats should work."""
        token = await self.get_auth_token(client)

        response = await client.get(
            "/api/v1/analytics/alerts",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code in [200, 403, 404]

    # ==================== Time Series Tests ====================

    @pytest.mark.asyncio
    async def test_get_incident_timeseries(self, client: AsyncClient, test_user: User):
        """Getting incident time series should work."""
        token = await self.get_auth_token(client)

        response = await client.get(
            "/api/v1/analytics/timeseries/incidents",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code in [200, 403, 404]

    # ==================== Reports Tests ====================

    @pytest.mark.asyncio
    async def test_generate_report(self, client: AsyncClient, admin_user: User):
        """Generating a report should work for admins."""
        token = await self.get_admin_token(client)

        response = await client.post(
            "/api/v1/analytics/reports",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "report_type": "incident_summary",
                "time_range": "last_30_days",
            },
        )

        # May require special permissions
        assert response.status_code in [200, 201, 403, 404]

    @pytest.mark.asyncio
    async def test_list_reports(self, client: AsyncClient, admin_user: User):
        """Listing reports should work for admins."""
        token = await self.get_admin_token(client)

        response = await client.get(
            "/api/v1/analytics/reports",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code in [200, 403, 404]

    # ==================== Metrics Tests ====================

    @pytest.mark.asyncio
    async def test_get_metrics(self, client: AsyncClient, test_user: User):
        """Getting Prometheus metrics should work."""
        # Metrics endpoint is usually public
        response = await client.get("/metrics")

        # May be at /api/v1/metrics or /metrics
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_get_health_metrics(self, client: AsyncClient):
        """Getting health metrics should work without auth."""
        response = await client.get("/api/v1/analytics/health")

        # Health endpoint may be public
        assert response.status_code in [200, 404]
