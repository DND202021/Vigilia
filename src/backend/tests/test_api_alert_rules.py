"""Tests for alert rules API endpoints."""

import uuid
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient

from app.models.device import IoTDevice
from app.models.device_profile import DeviceProfile
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertSource
from app.models.user import User


class TestDeviceAlertRulesAPI:
    """Tests for device alert rules endpoints."""

    @pytest.mark.asyncio
    async def test_get_device_alert_rules_not_authenticated(self, client: AsyncClient):
        """Test getting device alert rules without authentication."""
        device_id = uuid.uuid4()
        response = await client.get(f"/api/v1/devices/{device_id}/alert-rules")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_device_alert_rules_device_not_found(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test getting alert rules for non-existent device."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        device_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/devices/{device_id}/alert-rules",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert "Device not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_device_alert_rules_no_profile(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test getting alert rules for device without profile."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        # Create device without profile
        device = IoTDevice(
            id=uuid.uuid4(),
            name="Test Device",
            device_type="sensor",
            serial_number="SN-001",
            status="online",
        )
        db_session.add(device)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/devices/{device.id}/alert-rules",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == str(device.id)
        assert data["device_name"] == "Test Device"
        assert data["profile_id"] is None
        assert data["profile_name"] is None
        assert data["rules"] == []

    @pytest.mark.asyncio
    async def test_get_device_alert_rules_with_profile(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test getting alert rules for device with profile."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        # Create profile with alert rules
        profile = DeviceProfile(
            id=uuid.uuid4(),
            name="Temperature Sensor Profile",
            device_type="sensor",
            alert_rules=[
                {
                    "name": "High Temperature",
                    "metric": "temperature",
                    "condition": "gt",
                    "threshold": 80,
                    "severity": "high",
                    "cooldown_seconds": 300,
                },
                {
                    "name": "Low Temperature",
                    "metric": "temperature",
                    "condition": "lt",
                    "threshold": 0,
                    "severity": "medium",
                    "cooldown_seconds": 600,
                },
            ],
        )
        db_session.add(profile)

        # Create device with profile
        device = IoTDevice(
            id=uuid.uuid4(),
            name="Temp Sensor 1",
            device_type="sensor",
            serial_number="SN-002",
            status="online",
            profile_id=profile.id,
        )
        db_session.add(device)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/devices/{device.id}/alert-rules",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == str(device.id)
        assert data["device_name"] == "Temp Sensor 1"
        assert data["profile_id"] == str(profile.id)
        assert data["profile_name"] == "Temperature Sensor Profile"
        assert len(data["rules"]) == 2

        # Check first rule
        rule1 = data["rules"][0]
        assert rule1["name"] == "High Temperature"
        assert rule1["metric"] == "temperature"
        assert rule1["condition"] == "gt"
        assert rule1["threshold"] == 80
        assert rule1["severity"] == "high"
        assert rule1["cooldown_seconds"] == 300

    @pytest.mark.asyncio
    async def test_get_device_alert_rules_profile_without_rules(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test getting alert rules for device with profile but no rules."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        # Create profile without alert rules
        profile = DeviceProfile(
            id=uuid.uuid4(),
            name="Empty Profile",
            device_type="sensor",
            alert_rules=None,
        )
        db_session.add(profile)

        # Create device with profile
        device = IoTDevice(
            id=uuid.uuid4(),
            name="Sensor No Rules",
            device_type="sensor",
            serial_number="SN-003",
            status="online",
            profile_id=profile.id,
        )
        db_session.add(device)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/devices/{device.id}/alert-rules",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["profile_id"] == str(profile.id)
        assert data["profile_name"] == "Empty Profile"
        assert data["rules"] == []


class TestRecentAlertEvaluationsAPI:
    """Tests for recent alert evaluations endpoints."""

    @pytest.mark.asyncio
    async def test_get_recent_alerts_not_authenticated(self, client: AsyncClient):
        """Test getting recent alerts without authentication."""
        response = await client.get("/api/v1/alert-rules/recent")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_recent_alerts_empty(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test getting recent alerts when none exist."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            "/api/v1/alert-rules/recent",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_recent_alerts_with_data(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test getting recent alerts with IoT telemetry alerts."""
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
            serial_number="SN-100",
            status="online",
        )
        db_session.add(device)
        await db_session.flush()

        # Create IoT telemetry alerts
        alert1 = Alert(
            id=uuid.uuid4(),
            title="High Temperature",
            description="Temperature exceeded threshold",
            severity=AlertSeverity.HIGH,
            status=AlertStatus.PENDING,
            source=AlertSource.IOT_TELEMETRY,
            device_id=device.id,
            raw_payload={
                "device_name": "Test Device",
                "rule_name": "High Temperature",
                "metric": "temperature",
                "condition": "gt",
                "threshold": 80,
                "actual_value": 85,
            },
            received_at=datetime.now(timezone.utc),
        )
        alert2 = Alert(
            id=uuid.uuid4(),
            title="Low Battery",
            description="Battery below threshold",
            severity=AlertSeverity.MEDIUM,
            status=AlertStatus.PENDING,
            source=AlertSource.IOT_TELEMETRY,
            device_id=device.id,
            raw_payload={
                "device_name": "Test Device",
                "rule_name": "Low Battery",
                "metric": "battery",
                "condition": "lt",
                "threshold": 20,
                "actual_value": 15,
            },
            received_at=datetime.now(timezone.utc),
        )
        # Create non-IoT alert (should not be included)
        alert3 = Alert(
            id=uuid.uuid4(),
            title="Manual Alert",
            description="Manually created",
            severity=AlertSeverity.LOW,
            status=AlertStatus.PENDING,
            source=AlertSource.MANUAL,
            received_at=datetime.now(timezone.utc),
        )
        db_session.add_all([alert1, alert2, alert3])
        await db_session.commit()

        response = await client.get(
            "/api/v1/alert-rules/recent",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # Only IoT telemetry alerts

        # Check first alert (most recent)
        assert data[0]["device_name"] == "Test Device"
        assert data[0]["rule_name"] in ["High Temperature", "Low Battery"]

    @pytest.mark.asyncio
    async def test_get_recent_alerts_with_limit(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test getting recent alerts with limit parameter."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        # Create multiple alerts
        for i in range(5):
            alert = Alert(
                id=uuid.uuid4(),
                title=f"Alert {i}",
                description="Test",
                severity=AlertSeverity.MEDIUM,
                status=AlertStatus.PENDING,
                source=AlertSource.IOT_TELEMETRY,
                received_at=datetime.now(timezone.utc),
            )
            db_session.add(alert)
        await db_session.commit()

        response = await client.get(
            "/api/v1/alert-rules/recent?limit=2",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.asyncio
    async def test_get_recent_alerts_filter_by_severity(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test filtering recent alerts by severity."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        # Create alerts with different severities
        alert_high = Alert(
            id=uuid.uuid4(),
            title="High Alert",
            description="High severity",
            severity=AlertSeverity.HIGH,
            status=AlertStatus.PENDING,
            source=AlertSource.IOT_TELEMETRY,
            received_at=datetime.now(timezone.utc),
        )
        alert_low = Alert(
            id=uuid.uuid4(),
            title="Low Alert",
            description="Low severity",
            severity=AlertSeverity.LOW,
            status=AlertStatus.PENDING,
            source=AlertSource.IOT_TELEMETRY,
            received_at=datetime.now(timezone.utc),
        )
        db_session.add_all([alert_high, alert_low])
        await db_session.commit()

        response = await client.get(
            "/api/v1/alert-rules/recent?severity=high",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["severity"] == "high"

    @pytest.mark.asyncio
    async def test_get_recent_alerts_invalid_severity(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test filtering with invalid severity."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            "/api/v1/alert-rules/recent?severity=invalid",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "Invalid severity" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_recent_alerts_filter_by_device(
        self, client: AsyncClient, test_user: User, db_session
    ):
        """Test filtering recent alerts by device ID."""
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com", "password": "TestPassword123!"},
        )
        token = login_response.json()["access_token"]

        # Create devices
        device1 = IoTDevice(
            id=uuid.uuid4(),
            name="Device 1",
            device_type="sensor",
            serial_number="SN-D1",
            status="online",
        )
        device2 = IoTDevice(
            id=uuid.uuid4(),
            name="Device 2",
            device_type="sensor",
            serial_number="SN-D2",
            status="online",
        )
        db_session.add_all([device1, device2])
        await db_session.flush()

        # Create alerts for different devices
        alert1 = Alert(
            id=uuid.uuid4(),
            title="Alert D1",
            description="From device 1",
            severity=AlertSeverity.MEDIUM,
            status=AlertStatus.PENDING,
            source=AlertSource.IOT_TELEMETRY,
            device_id=device1.id,
            received_at=datetime.now(timezone.utc),
        )
        alert2 = Alert(
            id=uuid.uuid4(),
            title="Alert D2",
            description="From device 2",
            severity=AlertSeverity.MEDIUM,
            status=AlertStatus.PENDING,
            source=AlertSource.IOT_TELEMETRY,
            device_id=device2.id,
            received_at=datetime.now(timezone.utc),
        )
        db_session.add_all([alert1, alert2])
        await db_session.commit()

        response = await client.get(
            f"/api/v1/alert-rules/recent?device_id={device1.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["device_id"] == str(device1.id)
