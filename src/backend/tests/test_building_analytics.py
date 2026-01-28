"""Tests for building analytics service and API endpoints."""

import pytest
import uuid
from datetime import datetime, timezone, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.building_analytics_service import BuildingAnalyticsService
from app.models.device import IoTDevice, DeviceType, DeviceStatus
from app.models.building import Building, BuildingType, FloorPlan
from app.models.incident import Incident, IncidentStatus, IncidentPriority, IncidentCategory
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertSource
from app.models.inspection import Inspection, InspectionType, InspectionStatus
from app.models.agency import Agency


# ==================== Fixtures ====================


@pytest.fixture
async def analytics_building(db_session: AsyncSession, test_agency: Agency) -> Building:
    """Create a test building for analytics tests."""
    building = Building(
        id=uuid.uuid4(),
        agency_id=test_agency.id,
        name="Analytics Test Building",
        street_name="Analytics Street",
        city="Montreal",
        province_state="Quebec",
        latitude=45.5017,
        longitude=-73.5673,
        building_type=BuildingType.COMMERCIAL,
        full_address="100 Analytics Street, Montreal, Quebec",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def analytics_floor_plan(db_session: AsyncSession, analytics_building: Building) -> FloorPlan:
    """Create a test floor plan for analytics tests."""
    floor_plan = FloorPlan(
        id=uuid.uuid4(),
        building_id=analytics_building.id,
        floor_number=1,
        floor_name="Ground Floor",
    )
    db_session.add(floor_plan)
    await db_session.commit()
    await db_session.refresh(floor_plan)
    return floor_plan


@pytest.fixture
async def devices_various_statuses(
    db_session: AsyncSession,
    analytics_building: Building,
    analytics_floor_plan: FloorPlan,
) -> list[IoTDevice]:
    """Create test devices with various statuses and types."""
    devices = []

    # Online devices (various types)
    online_configs = [
        (DeviceType.CAMERA, "Camera 1"),
        (DeviceType.CAMERA, "Camera 2"),
        (DeviceType.MICROPHONE, "Microphone 1"),
        (DeviceType.SENSOR, "Sensor 1"),
    ]
    for device_type, name in online_configs:
        device = IoTDevice(
            id=uuid.uuid4(),
            name=name,
            device_type=device_type.value,
            building_id=analytics_building.id,
            floor_plan_id=analytics_floor_plan.id,
            status=DeviceStatus.ONLINE.value,
        )
        db_session.add(device)
        devices.append(device)

    # Offline devices
    offline_device = IoTDevice(
        id=uuid.uuid4(),
        name="Offline Camera",
        device_type=DeviceType.CAMERA.value,
        building_id=analytics_building.id,
        status=DeviceStatus.OFFLINE.value,
    )
    db_session.add(offline_device)
    devices.append(offline_device)

    # Alert status device
    alert_device = IoTDevice(
        id=uuid.uuid4(),
        name="Alert Sensor",
        device_type=DeviceType.SENSOR.value,
        building_id=analytics_building.id,
        status=DeviceStatus.ALERT.value,
    )
    db_session.add(alert_device)
    devices.append(alert_device)

    # Maintenance device
    maintenance_device = IoTDevice(
        id=uuid.uuid4(),
        name="Maintenance Gateway",
        device_type=DeviceType.GATEWAY.value,
        building_id=analytics_building.id,
        status=DeviceStatus.MAINTENANCE.value,
    )
    db_session.add(maintenance_device)
    devices.append(maintenance_device)

    # Error device
    error_device = IoTDevice(
        id=uuid.uuid4(),
        name="Error Device",
        device_type=DeviceType.OTHER.value,
        building_id=analytics_building.id,
        status=DeviceStatus.ERROR.value,
    )
    db_session.add(error_device)
    devices.append(error_device)

    await db_session.commit()
    return devices


@pytest.fixture
async def incidents_various(
    db_session: AsyncSession,
    analytics_building: Building,
    test_agency: Agency,
) -> list[Incident]:
    """Create test incidents with various categories, priorities, and statuses."""
    incidents = []
    now = datetime.now(timezone.utc)

    # New fire incident - critical
    inc1 = Incident(
        id=uuid.uuid4(),
        incident_number=f"INC-{uuid.uuid4().hex[:8]}",
        category=IncidentCategory.FIRE,
        priority=IncidentPriority.CRITICAL.value,
        status=IncidentStatus.NEW,
        title="Fire alarm triggered",
        latitude=45.5017,
        longitude=-73.5673,
        reported_at=now - timedelta(hours=2),
        agency_id=test_agency.id,
        building_id=analytics_building.id,
        created_at=now - timedelta(hours=2),
    )
    db_session.add(inc1)
    incidents.append(inc1)

    # Assigned medical - high priority
    inc2 = Incident(
        id=uuid.uuid4(),
        incident_number=f"INC-{uuid.uuid4().hex[:8]}",
        category=IncidentCategory.MEDICAL,
        priority=IncidentPriority.HIGH.value,
        status=IncidentStatus.ASSIGNED,
        title="Medical emergency",
        latitude=45.5017,
        longitude=-73.5673,
        reported_at=now - timedelta(hours=5),
        agency_id=test_agency.id,
        building_id=analytics_building.id,
        created_at=now - timedelta(hours=5),
    )
    db_session.add(inc2)
    incidents.append(inc2)

    # Resolved intrusion - medium priority
    inc3 = Incident(
        id=uuid.uuid4(),
        incident_number=f"INC-{uuid.uuid4().hex[:8]}",
        category=IncidentCategory.INTRUSION,
        priority=IncidentPriority.MEDIUM.value,
        status=IncidentStatus.RESOLVED,
        title="Intrusion detected",
        latitude=45.5017,
        longitude=-73.5673,
        reported_at=now - timedelta(days=1),
        agency_id=test_agency.id,
        building_id=analytics_building.id,
        created_at=now - timedelta(days=1),
    )
    db_session.add(inc3)
    incidents.append(inc3)

    # Closed traffic - low priority (from yesterday)
    inc4 = Incident(
        id=uuid.uuid4(),
        incident_number=f"INC-{uuid.uuid4().hex[:8]}",
        category=IncidentCategory.TRAFFIC,
        priority=IncidentPriority.LOW.value,
        status=IncidentStatus.CLOSED,
        title="Traffic issue",
        latitude=45.5017,
        longitude=-73.5673,
        reported_at=now - timedelta(days=2),
        agency_id=test_agency.id,
        building_id=analytics_building.id,
        created_at=now - timedelta(days=2),
    )
    db_session.add(inc4)
    incidents.append(inc4)

    # On-scene fire - high priority (same day as inc1 for trend testing)
    inc5 = Incident(
        id=uuid.uuid4(),
        incident_number=f"INC-{uuid.uuid4().hex[:8]}",
        category=IncidentCategory.FIRE,
        priority=IncidentPriority.HIGH.value,
        status=IncidentStatus.ON_SCENE,
        title="Second fire alert",
        latitude=45.5017,
        longitude=-73.5673,
        reported_at=now - timedelta(hours=1),
        agency_id=test_agency.id,
        building_id=analytics_building.id,
        created_at=now - timedelta(hours=1),
    )
    db_session.add(inc5)
    incidents.append(inc5)

    await db_session.commit()
    return incidents


@pytest.fixture
async def alerts_various(
    db_session: AsyncSession,
    analytics_building: Building,
) -> list[Alert]:
    """Create test alerts with various severities and statuses."""
    alerts = []
    now = datetime.now(timezone.utc)

    # Critical pending
    alert1 = Alert(
        id=uuid.uuid4(),
        source=AlertSource.AXIS_MICROPHONE,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.PENDING,
        alert_type="gunshot",
        title="Gunshot detected",
        building_id=analytics_building.id,
        received_at=now - timedelta(minutes=30),
        created_at=now - timedelta(minutes=30),
    )
    db_session.add(alert1)
    alerts.append(alert1)

    # High acknowledged
    alert2 = Alert(
        id=uuid.uuid4(),
        source=AlertSource.SECURITY_SYSTEM,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.ACKNOWLEDGED,
        alert_type="intrusion",
        title="Motion detected after hours",
        building_id=analytics_building.id,
        received_at=now - timedelta(hours=1),
        created_at=now - timedelta(hours=1),
    )
    db_session.add(alert2)
    alerts.append(alert2)

    # Medium resolved
    alert3 = Alert(
        id=uuid.uuid4(),
        source=AlertSource.ALARM_SYSTEM,
        severity=AlertSeverity.MEDIUM,
        status=AlertStatus.RESOLVED,
        alert_type="door_open",
        title="Door left open",
        building_id=analytics_building.id,
        received_at=now - timedelta(hours=3),
        created_at=now - timedelta(hours=3),
    )
    db_session.add(alert3)
    alerts.append(alert3)

    # Low dismissed
    alert4 = Alert(
        id=uuid.uuid4(),
        source=AlertSource.MANUAL,
        severity=AlertSeverity.LOW,
        status=AlertStatus.DISMISSED,
        alert_type="test",
        title="Test alert",
        building_id=analytics_building.id,
        received_at=now - timedelta(hours=6),
        created_at=now - timedelta(hours=6),
    )
    db_session.add(alert4)
    alerts.append(alert4)

    # Info pending
    alert5 = Alert(
        id=uuid.uuid4(),
        source=AlertSource.FUNDAMENTUM,
        severity=AlertSeverity.INFO,
        status=AlertStatus.PENDING,
        alert_type="status",
        title="Device status update",
        building_id=analytics_building.id,
        received_at=now - timedelta(hours=12),
        created_at=now - timedelta(hours=12),
    )
    db_session.add(alert5)
    alerts.append(alert5)

    await db_session.commit()
    return alerts


@pytest.fixture
async def inspections_various(
    db_session: AsyncSession,
    analytics_building: Building,
    test_user,
) -> list[Inspection]:
    """Create test inspections with various statuses."""
    inspections = []
    today = date.today()

    # Completed inspections
    insp1 = Inspection(
        id=uuid.uuid4(),
        building_id=analytics_building.id,
        inspection_type=InspectionType.FIRE_SAFETY,
        scheduled_date=today - timedelta(days=30),
        completed_date=today - timedelta(days=30),
        status=InspectionStatus.COMPLETED,
        inspector_name="John Inspector",
        created_by_id=test_user.id,
    )
    db_session.add(insp1)
    inspections.append(insp1)

    insp2 = Inspection(
        id=uuid.uuid4(),
        building_id=analytics_building.id,
        inspection_type=InspectionType.STRUCTURAL,
        scheduled_date=today - timedelta(days=60),
        completed_date=today - timedelta(days=58),
        status=InspectionStatus.COMPLETED,
        inspector_name="Jane Inspector",
        created_by_id=test_user.id,
    )
    db_session.add(insp2)
    inspections.append(insp2)

    # Scheduled future inspections
    insp3 = Inspection(
        id=uuid.uuid4(),
        building_id=analytics_building.id,
        inspection_type=InspectionType.HAZMAT,
        scheduled_date=today + timedelta(days=14),
        status=InspectionStatus.SCHEDULED,
        inspector_name="Mike Inspector",
        created_by_id=test_user.id,
    )
    db_session.add(insp3)
    inspections.append(insp3)

    insp4 = Inspection(
        id=uuid.uuid4(),
        building_id=analytics_building.id,
        inspection_type=InspectionType.GENERAL,
        scheduled_date=today + timedelta(days=30),
        status=InspectionStatus.SCHEDULED,
        inspector_name="Sarah Inspector",
        created_by_id=test_user.id,
    )
    db_session.add(insp4)
    inspections.append(insp4)

    # Overdue inspection
    insp5 = Inspection(
        id=uuid.uuid4(),
        building_id=analytics_building.id,
        inspection_type=InspectionType.FIRE_SAFETY,
        scheduled_date=today - timedelta(days=7),
        status=InspectionStatus.SCHEDULED,  # Scheduled but past date = overdue
        inspector_name="Bob Inspector",
        created_by_id=test_user.id,
    )
    db_session.add(insp5)
    inspections.append(insp5)

    # Another overdue with OVERDUE status
    insp6 = Inspection(
        id=uuid.uuid4(),
        building_id=analytics_building.id,
        inspection_type=InspectionType.STRUCTURAL,
        scheduled_date=today - timedelta(days=14),
        status=InspectionStatus.OVERDUE,
        inspector_name="Alice Inspector",
        created_by_id=test_user.id,
    )
    db_session.add(insp6)
    inspections.append(insp6)

    await db_session.commit()
    return inspections


# ==================== Service Tests ====================


class TestBuildingAnalyticsService:
    """Tests for BuildingAnalyticsService."""

    # -------------------- Device Health Tests --------------------

    @pytest.mark.asyncio
    async def test_get_device_health_empty(
        self, db_session: AsyncSession, analytics_building: Building
    ):
        """No devices returns zeros."""
        service = BuildingAnalyticsService(db_session)

        result = await service.get_device_health(analytics_building.id)

        assert result["total"] == 0
        assert result["health_percentage"] == 0.0
        assert result["by_status"]["online"] == 0
        assert result["by_status"]["offline"] == 0
        assert result["by_status"]["alert"] == 0
        assert result["by_status"]["maintenance"] == 0
        assert result["by_status"]["error"] == 0
        assert result["by_type"]["camera"] == 0
        assert result["by_type"]["microphone"] == 0
        assert result["by_type"]["sensor"] == 0
        assert result["by_type"]["gateway"] == 0
        assert result["by_type"]["other"] == 0

    @pytest.mark.asyncio
    async def test_get_device_health_with_devices(
        self,
        db_session: AsyncSession,
        analytics_building: Building,
        devices_various_statuses: list[IoTDevice],
    ):
        """Returns correct counts by status and type."""
        service = BuildingAnalyticsService(db_session)

        result = await service.get_device_health(analytics_building.id)

        # Total devices: 8
        assert result["total"] == 8

        # Status counts: 4 online, 1 offline, 1 alert, 1 maintenance, 1 error
        assert result["by_status"]["online"] == 4
        assert result["by_status"]["offline"] == 1
        assert result["by_status"]["alert"] == 1
        assert result["by_status"]["maintenance"] == 1
        assert result["by_status"]["error"] == 1

        # Type counts: 3 cameras, 1 microphone, 2 sensors, 1 gateway, 1 other
        assert result["by_type"]["camera"] == 3
        assert result["by_type"]["microphone"] == 1
        assert result["by_type"]["sensor"] == 2
        assert result["by_type"]["gateway"] == 1
        assert result["by_type"]["other"] == 1

    @pytest.mark.asyncio
    async def test_get_device_health_percentage(
        self,
        db_session: AsyncSession,
        analytics_building: Building,
        devices_various_statuses: list[IoTDevice],
    ):
        """Health percentage calculated correctly."""
        service = BuildingAnalyticsService(db_session)

        result = await service.get_device_health(analytics_building.id)

        # 4 online out of 8 total = 50%
        assert result["health_percentage"] == 50.0

    # -------------------- Incident Stats Tests --------------------

    @pytest.mark.asyncio
    async def test_get_incident_stats_empty(
        self, db_session: AsyncSession, analytics_building: Building
    ):
        """No incidents returns zeros."""
        service = BuildingAnalyticsService(db_session)

        result = await service.get_incident_stats(analytics_building.id)

        assert result["total"] == 0
        assert result["by_status"]["new"] == 0
        assert result["by_status"]["assigned"] == 0
        assert result["by_status"]["en_route"] == 0
        assert result["by_status"]["on_scene"] == 0
        assert result["by_status"]["resolved"] == 0
        assert result["by_status"]["closed"] == 0
        assert result["by_priority"]["critical"] == 0
        assert result["by_priority"]["high"] == 0
        assert result["by_priority"]["medium"] == 0
        assert result["by_priority"]["low"] == 0
        assert result["by_priority"]["minimal"] == 0
        assert result["trend"] == []

    @pytest.mark.asyncio
    async def test_get_incident_stats_with_incidents(
        self,
        db_session: AsyncSession,
        analytics_building: Building,
        incidents_various: list[Incident],
    ):
        """Returns correct breakdowns by status, category, and priority."""
        service = BuildingAnalyticsService(db_session)

        result = await service.get_incident_stats(analytics_building.id)

        # Total: 5 incidents
        assert result["total"] == 5

        # Status counts
        assert result["by_status"]["new"] == 1
        assert result["by_status"]["assigned"] == 1
        assert result["by_status"]["resolved"] == 1
        assert result["by_status"]["closed"] == 1
        assert result["by_status"]["on_scene"] == 1

        # Category counts
        assert result["by_category"]["fire"] == 2
        assert result["by_category"]["medical"] == 1
        assert result["by_category"]["intrusion"] == 1
        assert result["by_category"]["traffic"] == 1

        # Priority counts
        assert result["by_priority"]["critical"] == 1
        assert result["by_priority"]["high"] == 2
        assert result["by_priority"]["medium"] == 1
        assert result["by_priority"]["low"] == 1

    @pytest.mark.asyncio
    async def test_get_incident_stats_trend(
        self,
        db_session: AsyncSession,
        analytics_building: Building,
        incidents_various: list[Incident],
    ):
        """Trend data has correct daily counts."""
        service = BuildingAnalyticsService(db_session)

        result = await service.get_incident_stats(analytics_building.id)

        # Should have trend data
        assert len(result["trend"]) > 0

        # Each trend item should have date and count
        for item in result["trend"]:
            assert "date" in item
            assert "count" in item
            assert isinstance(item["count"], int)
            assert item["count"] > 0

    # -------------------- Alert Breakdown Tests --------------------

    @pytest.mark.asyncio
    async def test_get_alert_breakdown_empty(
        self, db_session: AsyncSession, analytics_building: Building
    ):
        """No alerts returns zeros."""
        service = BuildingAnalyticsService(db_session)

        result = await service.get_alert_breakdown(analytics_building.id)

        assert result["total"] == 0
        assert result["pending"] == 0
        assert result["by_severity"]["critical"] == 0
        assert result["by_severity"]["high"] == 0
        assert result["by_severity"]["medium"] == 0
        assert result["by_severity"]["low"] == 0
        assert result["by_severity"]["info"] == 0
        assert result["by_status"]["pending"] == 0
        assert result["by_status"]["acknowledged"] == 0
        assert result["by_status"]["resolved"] == 0
        assert result["by_status"]["dismissed"] == 0
        assert result["recent"] == []

    @pytest.mark.asyncio
    async def test_get_alert_breakdown_with_alerts(
        self,
        db_session: AsyncSession,
        analytics_building: Building,
        alerts_various: list[Alert],
    ):
        """Returns severity and status counts."""
        service = BuildingAnalyticsService(db_session)

        result = await service.get_alert_breakdown(analytics_building.id)

        # Total: 5 alerts
        assert result["total"] == 5

        # Pending count: 2 (critical pending + info pending)
        assert result["pending"] == 2

        # Severity counts
        assert result["by_severity"]["critical"] == 1
        assert result["by_severity"]["high"] == 1
        assert result["by_severity"]["medium"] == 1
        assert result["by_severity"]["low"] == 1
        assert result["by_severity"]["info"] == 1

        # Status counts
        assert result["by_status"]["pending"] == 2
        assert result["by_status"]["acknowledged"] == 1
        assert result["by_status"]["resolved"] == 1
        assert result["by_status"]["dismissed"] == 1

        # Recent alerts (should have 5, sorted by created_at desc)
        assert len(result["recent"]) == 5
        # Most recent should be the critical pending alert
        assert result["recent"][0]["severity"] == "critical"
        assert result["recent"][0]["title"] == "Gunshot detected"

    # -------------------- Inspection Compliance Tests --------------------

    @pytest.mark.asyncio
    async def test_get_inspection_compliance_empty(
        self, db_session: AsyncSession, analytics_building: Building
    ):
        """No inspections returns zeros."""
        service = BuildingAnalyticsService(db_session)

        result = await service.get_inspection_compliance(analytics_building.id)

        assert result["total"] == 0
        assert result["completed"] == 0
        assert result["scheduled"] == 0
        assert result["overdue"] == 0
        assert result["compliance_rate"] == 0.0
        assert result["upcoming"] == []
        assert result["overdue_list"] == []

    @pytest.mark.asyncio
    async def test_get_inspection_compliance_with_inspections(
        self,
        db_session: AsyncSession,
        analytics_building: Building,
        inspections_various: list[Inspection],
    ):
        """Returns correct counts for completed, scheduled, and overdue."""
        service = BuildingAnalyticsService(db_session)

        result = await service.get_inspection_compliance(analytics_building.id)

        # Total: 6 inspections
        assert result["total"] == 6

        # Completed: 2
        assert result["completed"] == 2

        # Scheduled (future): 2
        assert result["scheduled"] == 2

        # Overdue: 2 (one scheduled with past date, one with OVERDUE status)
        assert result["overdue"] == 2

        # Upcoming list (should have 2 future scheduled inspections)
        assert len(result["upcoming"]) == 2

        # Overdue list (should have 2)
        assert len(result["overdue_list"]) == 2

    @pytest.mark.asyncio
    async def test_get_inspection_compliance_rate(
        self,
        db_session: AsyncSession,
        analytics_building: Building,
        inspections_various: list[Inspection],
    ):
        """Compliance rate calculated correctly."""
        service = BuildingAnalyticsService(db_session)

        result = await service.get_inspection_compliance(analytics_building.id)

        # Compliance rate = completed / (completed + overdue) * 100
        # = 2 / (2 + 2) * 100 = 50%
        assert result["compliance_rate"] == 50.0

    # -------------------- Building Overview Test --------------------

    @pytest.mark.asyncio
    async def test_get_building_overview(
        self,
        db_session: AsyncSession,
        analytics_building: Building,
        devices_various_statuses: list[IoTDevice],
        incidents_various: list[Incident],
        alerts_various: list[Alert],
        inspections_various: list[Inspection],
    ):
        """Returns all sections combined."""
        service = BuildingAnalyticsService(db_session)

        result = await service.get_building_overview(analytics_building.id)

        # Should have building_id
        assert result["building_id"] == str(analytics_building.id)

        # Should have generated_at timestamp
        assert "generated_at" in result
        assert isinstance(result["generated_at"], str)

        # Should have all four sections
        assert "device_health" in result
        assert "incident_stats" in result
        assert "alert_breakdown" in result
        assert "inspection_compliance" in result

        # Verify device_health section
        assert result["device_health"]["total"] == 8
        assert result["device_health"]["health_percentage"] == 50.0

        # Verify incident_stats section
        assert result["incident_stats"]["total"] == 5

        # Verify alert_breakdown section
        assert result["alert_breakdown"]["total"] == 5

        # Verify inspection_compliance section
        assert result["inspection_compliance"]["total"] == 6


# ==================== API Tests ====================


class TestBuildingAnalyticsAPI:
    """Tests for building analytics API endpoints."""

    async def get_admin_token(self, client) -> str:
        """Helper to get admin auth token for API requests."""
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "AdminPassword123!",
            },
        )
        return login_response.json()["access_token"]

    async def create_test_building(self, client, token: str) -> str:
        """Helper to create a test building and return its ID."""
        response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Analytics API Test Building",
                "street_name": "API Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
            },
        )
        return response.json()["id"]

    @pytest.mark.asyncio
    async def test_get_analytics_endpoint(self, client, admin_user, test_agency):
        """GET /buildings/{id}/analytics returns 200."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.get(
            f"/api/v1/buildings/{building_id}/analytics",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Should have all required fields
        assert "building_id" in data
        assert "generated_at" in data
        assert "device_health" in data
        assert "incident_stats" in data
        assert "alert_breakdown" in data
        assert "inspection_compliance" in data

        # Building ID should match
        assert data["building_id"] == building_id

    @pytest.mark.asyncio
    async def test_get_device_analytics(self, client, admin_user, test_agency):
        """GET /buildings/{id}/analytics/devices returns device health."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.get(
            f"/api/v1/buildings/{building_id}/analytics/devices",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Should have device health fields
        assert "total" in data
        assert "by_status" in data
        assert "by_type" in data
        assert "health_percentage" in data

        # Empty building should have zeros
        assert data["total"] == 0
        assert data["health_percentage"] == 0.0

    @pytest.mark.asyncio
    async def test_get_incident_analytics(self, client, admin_user, test_agency):
        """GET /buildings/{id}/analytics/incidents returns incident stats."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.get(
            f"/api/v1/buildings/{building_id}/analytics/incidents",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Should have incident stats fields
        assert "total" in data
        assert "by_status" in data
        assert "by_category" in data
        assert "by_priority" in data
        assert "trend" in data

        # Empty building should have zeros
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_incident_analytics_with_days_param(self, client, admin_user, test_agency):
        """GET /buildings/{id}/analytics/incidents accepts days parameter."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.get(
            f"/api/v1/buildings/{building_id}/analytics/incidents",
            headers={"Authorization": f"Bearer {token}"},
            params={"days": 7},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_alert_analytics(self, client, admin_user, test_agency):
        """GET /buildings/{id}/analytics/alerts returns alert breakdown."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.get(
            f"/api/v1/buildings/{building_id}/analytics/alerts",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Should have alert breakdown fields
        assert "total" in data
        assert "pending" in data
        assert "by_severity" in data
        assert "by_status" in data
        assert "recent" in data

        # Empty building should have zeros
        assert data["total"] == 0
        assert data["pending"] == 0

    @pytest.mark.asyncio
    async def test_get_alert_analytics_with_days_param(self, client, admin_user, test_agency):
        """GET /buildings/{id}/analytics/alerts accepts days parameter."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.get(
            f"/api/v1/buildings/{building_id}/analytics/alerts",
            headers={"Authorization": f"Bearer {token}"},
            params={"days": 14},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_inspection_analytics(self, client, admin_user, test_agency):
        """GET /buildings/{id}/analytics/inspections returns compliance metrics."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.get(
            f"/api/v1/buildings/{building_id}/analytics/inspections",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Should have inspection compliance fields
        assert "total" in data
        assert "completed" in data
        assert "scheduled" in data
        assert "overdue" in data
        assert "compliance_rate" in data
        assert "upcoming" in data
        assert "overdue_list" in data

        # Empty building should have zeros
        assert data["total"] == 0
        assert data["compliance_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_analytics_invalid_building(self, client, admin_user, test_agency):
        """Returns 404 for invalid building ID."""
        token = await self.get_admin_token(client)
        fake_id = str(uuid.uuid4())

        response = await client.get(
            f"/api/v1/buildings/{fake_id}/analytics",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_analytics_invalid_building_format(self, client, admin_user, test_agency):
        """Returns 400 for invalid building ID format."""
        token = await self.get_admin_token(client)

        response = await client.get(
            "/api/v1/buildings/not-a-uuid/analytics",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_analytics_unauthorized(self, client, admin_user, test_agency):
        """Returns 401 without auth."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.get(
            f"/api/v1/buildings/{building_id}/analytics",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_device_analytics_unauthorized(self, client, admin_user, test_agency):
        """Returns 401 for device analytics without auth."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.get(
            f"/api/v1/buildings/{building_id}/analytics/devices",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_incident_analytics_unauthorized(self, client, admin_user, test_agency):
        """Returns 401 for incident analytics without auth."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.get(
            f"/api/v1/buildings/{building_id}/analytics/incidents",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_alert_analytics_unauthorized(self, client, admin_user, test_agency):
        """Returns 401 for alert analytics without auth."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.get(
            f"/api/v1/buildings/{building_id}/analytics/alerts",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_inspection_analytics_unauthorized(self, client, admin_user, test_agency):
        """Returns 401 for inspection analytics without auth."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.get(
            f"/api/v1/buildings/{building_id}/analytics/inspections",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_device_analytics_building_not_found(self, client, admin_user, test_agency):
        """Returns 404 for device analytics with non-existent building."""
        token = await self.get_admin_token(client)
        fake_id = str(uuid.uuid4())

        response = await client.get(
            f"/api/v1/buildings/{fake_id}/analytics/devices",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_incident_analytics_building_not_found(self, client, admin_user, test_agency):
        """Returns 404 for incident analytics with non-existent building."""
        token = await self.get_admin_token(client)
        fake_id = str(uuid.uuid4())

        response = await client.get(
            f"/api/v1/buildings/{fake_id}/analytics/incidents",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_alert_analytics_building_not_found(self, client, admin_user, test_agency):
        """Returns 404 for alert analytics with non-existent building."""
        token = await self.get_admin_token(client)
        fake_id = str(uuid.uuid4())

        response = await client.get(
            f"/api/v1/buildings/{fake_id}/analytics/alerts",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_inspection_analytics_building_not_found(self, client, admin_user, test_agency):
        """Returns 404 for inspection analytics with non-existent building."""
        token = await self.get_admin_token(client)
        fake_id = str(uuid.uuid4())

        response = await client.get(
            f"/api/v1/buildings/{fake_id}/analytics/inspections",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
