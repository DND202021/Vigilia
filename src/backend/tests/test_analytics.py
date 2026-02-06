"""Tests for Analytics service."""

import uuid
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agency import Agency
from app.models.user import User
from app.models.incident import Incident, IncidentStatus, IncidentPriority, IncidentCategory
from app.models.alert import Alert, AlertSeverity, AlertSource
from app.services.analytics import AnalyticsService


@pytest.mark.asyncio
class TestAnalyticsService:
    """Test suite for AnalyticsService."""

    async def test_get_incident_stats(self, db_session: AsyncSession, test_agency: Agency):
        """Test getting incident statistics."""
        # Create test incidents
        incident1 = Incident(
            id=uuid.uuid4(),
            incident_number="INC-001",
            title="Incident 1",
            status=IncidentStatus.NEW,
            priority=IncidentPriority.HIGH,
            category=IncidentCategory.FIRE,
            latitude=40.7128,
            longitude=-74.0060,
            reported_at=datetime.now(timezone.utc),
            agency_id=test_agency.id,
        )
        incident2 = Incident(
            id=uuid.uuid4(),
            incident_number="INC-002",
            title="Incident 2",
            status=IncidentStatus.RESOLVED,
            priority=IncidentPriority.MEDIUM,
            category=IncidentCategory.MEDICAL,
            latitude=40.7128,
            longitude=-74.0060,
            reported_at=datetime.now(timezone.utc),
            agency_id=test_agency.id,
        )
        db_session.add_all([incident1, incident2])
        await db_session.commit()

        service = AnalyticsService(db_session)

        stats = await service.get_incident_stats(
            agency_id=test_agency.id,
            start_date=datetime.now(timezone.utc) - timedelta(days=7),
            end_date=datetime.now(timezone.utc),
        )

        assert stats is not None
        assert isinstance(stats, dict)

    async def test_get_alert_stats(self, db_session: AsyncSession, test_agency: Agency):
        """Test getting alert statistics."""
        # Create test alerts
        alert1 = Alert(
            id=uuid.uuid4(),
            title="Alert 1",
            description="Test alert 1",
            severity=AlertSeverity.CRITICAL,
            source=AlertSource.MANUAL,
            agency_id=test_agency.id,
        )
        alert2 = Alert(
            id=uuid.uuid4(),
            title="Alert 2",
            description="Test alert 2",
            severity=AlertSeverity.WARNING,
            source=AlertSource.SENSOR,
            agency_id=test_agency.id,
        )
        db_session.add_all([alert1, alert2])
        await db_session.commit()

        service = AnalyticsService(db_session)

        stats = await service.get_alert_stats(
            agency_id=test_agency.id,
            start_date=datetime.now(timezone.utc) - timedelta(days=7),
            end_date=datetime.now(timezone.utc),
        )

        assert stats is not None
        assert isinstance(stats, dict)

    async def test_get_response_times(self, db_session: AsyncSession, test_agency: Agency):
        """Test calculating response times."""
        # Create incident with timestamps
        reported = datetime.now(timezone.utc) - timedelta(minutes=30)
        dispatched = reported + timedelta(minutes=2)
        arrived = dispatched + timedelta(minutes=5)

        incident = Incident(
            id=uuid.uuid4(),
            incident_number="INC-001",
            title="Incident 1",
            status=IncidentStatus.ON_SCENE,
            priority=IncidentPriority.HIGH,
            category=IncidentCategory.FIRE,
            latitude=40.7128,
            longitude=-74.0060,
            reported_at=reported,
            dispatched_at=dispatched,
            arrived_at=arrived,
            agency_id=test_agency.id,
        )
        db_session.add(incident)
        await db_session.commit()

        service = AnalyticsService(db_session)

        response_times = await service.get_response_times(
            agency_id=test_agency.id,
            start_date=datetime.now(timezone.utc) - timedelta(days=7),
            end_date=datetime.now(timezone.utc),
        )

        assert response_times is not None
        assert isinstance(response_times, (dict, list))

    async def test_get_resource_utilization(self, db_session: AsyncSession, test_agency: Agency):
        """Test getting resource utilization."""
        service = AnalyticsService(db_session)

        utilization = await service.get_resource_utilization(
            agency_id=test_agency.id,
            start_date=datetime.now(timezone.utc) - timedelta(days=7),
            end_date=datetime.now(timezone.utc),
        )

        assert utilization is not None
        assert isinstance(utilization, dict)
