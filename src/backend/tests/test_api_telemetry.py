"""Tests for telemetry API endpoints."""

import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from app.models.device import IoTDevice
from app.models.user import User


class TestTelemetryIngestionAPI:
    """Tests for telemetry ingestion endpoint."""

    @pytest.mark.asyncio
    async def test_ingest_telemetry_not_authenticated(self, client: AsyncClient):
        """Test telemetry ingestion without authentication."""
        device_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/devices/{device_id}/telemetry",
            json={
                "metrics": {"temperature": 25.5, "humidity": 60},
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_ingest_telemetry_success(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test successful telemetry ingestion."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        # Create a device
        device = IoTDevice(
            id=uuid.uuid4(),
            name="Test Device",
            device_type="sensor",
            serial_number="SN-TEL-001",
            status="online",
        )
        db_session.add(device)
        await db_session.commit()

        # Mock the TelemetryIngestionService
        with patch("app.api.telemetry.TelemetryIngestionService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.validate_and_buffer = AsyncMock()
            mock_service_class.return_value = mock_service

            response = await client.post(
                f"/api/v1/devices/{device.id}/telemetry",
                json={
                    "metrics": {"temperature": 25.5, "humidity": 60},
                    "timestamp": "2025-01-31T12:00:00Z",
                    "message_id": "msg-001",
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert data["device_id"] == str(device.id)

    @pytest.mark.asyncio
    async def test_ingest_telemetry_minimal_payload(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test telemetry ingestion with minimal payload."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        device = IoTDevice(
            id=uuid.uuid4(),
            name="Minimal Device",
            device_type="sensor",
            serial_number="SN-TEL-002",
            status="online",
        )
        db_session.add(device)
        await db_session.commit()

        with patch("app.api.telemetry.TelemetryIngestionService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.validate_and_buffer = AsyncMock()
            mock_service_class.return_value = mock_service

            response = await client.post(
                f"/api/v1/devices/{device.id}/telemetry",
                json={"metrics": {"value": 100}},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 202

    @pytest.mark.asyncio
    async def test_ingest_telemetry_validation_error(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test telemetry ingestion with validation error."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        device = IoTDevice(
            id=uuid.uuid4(),
            name="Error Device",
            device_type="sensor",
            serial_number="SN-TEL-003",
            status="online",
        )
        db_session.add(device)
        await db_session.commit()

        # Mock service to raise error
        from app.services.telemetry_ingestion_service import TelemetryIngestionError

        with patch("app.api.telemetry.TelemetryIngestionService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.validate_and_buffer = AsyncMock(
                side_effect=TelemetryIngestionError("Invalid metric format")
            )
            mock_service_class.return_value = mock_service

            response = await client.post(
                f"/api/v1/devices/{device.id}/telemetry",
                json={"metrics": {"invalid": "data"}},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 422
        assert "Invalid metric format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_ingest_telemetry_various_metric_types(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test telemetry ingestion with various metric types."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        device = IoTDevice(
            id=uuid.uuid4(),
            name="Multi-Metric Device",
            device_type="sensor",
            serial_number="SN-TEL-004",
            status="online",
        )
        db_session.add(device)
        await db_session.commit()

        with patch("app.api.telemetry.TelemetryIngestionService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.validate_and_buffer = AsyncMock()
            mock_service_class.return_value = mock_service

            response = await client.post(
                f"/api/v1/devices/{device.id}/telemetry",
                json={
                    "metrics": {
                        "temperature": 25.5,  # float
                        "count": 100,  # int
                        "status": "active",  # string
                        "is_online": True,  # bool
                    },
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 202

    @pytest.mark.asyncio
    async def test_ingest_telemetry_missing_metrics(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test telemetry ingestion without metrics field."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        device_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/devices/{device_id}/telemetry",
            json={},  # Missing metrics
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_ingest_telemetry_invalid_device_id(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test telemetry ingestion with invalid device ID format."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        response = await client.post(
            "/api/v1/devices/not-a-valid-uuid/telemetry",
            json={"metrics": {"value": 1}},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422
