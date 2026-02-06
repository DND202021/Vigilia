"""Tests for AssignmentEngine."""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agency import Agency
from app.models.user import User
from app.models.incident import Incident, IncidentStatus, IncidentPriority, IncidentCategory
from app.models.resource import Resource, ResourceType, ResourceStatus
from app.services.assignment_engine import AssignmentEngine


@pytest.mark.asyncio
class TestAssignmentEngine:
    """Test suite for AssignmentEngine."""

    async def test_find_available_resources(self, db_session: AsyncSession, test_agency: Agency):
        """Test finding available resources."""
        # Create available resource
        resource = Resource(
            id=uuid.uuid4(),
            name="Engine 1",
            resource_type=ResourceType.VEHICLE,
            status=ResourceStatus.AVAILABLE,
            agency_id=test_agency.id,
        )
        db_session.add(resource)
        await db_session.commit()

        engine = AssignmentEngine(db_session)

        resources = await engine.find_available_resources(
            agency_id=test_agency.id,
            resource_type=ResourceType.VEHICLE,
        )

        assert len(resources) >= 1

    async def test_assign_resource_to_incident(self, db_session: AsyncSession, test_agency: Agency, test_user: User):
        """Test assigning a resource to an incident."""
        # Create incident
        incident = Incident(
            id=uuid.uuid4(),
            incident_number="INC-001",
            title="Test Incident",
            status=IncidentStatus.NEW,
            priority=IncidentPriority.HIGH,
            category=IncidentCategory.FIRE,
            latitude=40.7128,
            longitude=-74.0060,
            reported_at=datetime.now(timezone.utc),
            agency_id=test_agency.id,
        )
        db_session.add(incident)

        # Create resource
        resource = Resource(
            id=uuid.uuid4(),
            name="Engine 1",
            resource_type=ResourceType.VEHICLE,
            status=ResourceStatus.AVAILABLE,
            agency_id=test_agency.id,
        )
        db_session.add(resource)
        await db_session.commit()

        engine = AssignmentEngine(db_session)

        result = await engine.assign_resource(
            incident_id=incident.id,
            resource_id=resource.id,
            assigned_by_id=test_user.id,
        )

        assert result is True

    async def test_recommend_resources_for_incident(self, db_session: AsyncSession, test_agency: Agency):
        """Test recommending resources for an incident."""
        # Create incident
        incident = Incident(
            id=uuid.uuid4(),
            incident_number="INC-001",
            title="Fire Incident",
            status=IncidentStatus.NEW,
            priority=IncidentPriority.HIGH,
            category=IncidentCategory.FIRE,
            latitude=40.7128,
            longitude=-74.0060,
            reported_at=datetime.now(timezone.utc),
            agency_id=test_agency.id,
        )
        db_session.add(incident)

        # Create available resource
        resource = Resource(
            id=uuid.uuid4(),
            name="Engine 1",
            resource_type=ResourceType.VEHICLE,
            status=ResourceStatus.AVAILABLE,
            agency_id=test_agency.id,
        )
        db_session.add(resource)
        await db_session.commit()

        engine = AssignmentEngine(db_session)

        recommendations = await engine.recommend_resources(incident.id)

        assert recommendations is not None
        assert isinstance(recommendations, list)

    async def test_get_resource_workload(self, db_session: AsyncSession, test_agency: Agency):
        """Test getting resource workload."""
        # Create resource
        resource = Resource(
            id=uuid.uuid4(),
            name="Engine 1",
            resource_type=ResourceType.VEHICLE,
            status=ResourceStatus.AVAILABLE,
            agency_id=test_agency.id,
        )
        db_session.add(resource)
        await db_session.commit()

        engine = AssignmentEngine(db_session)

        workload = await engine.get_resource_workload(resource.id)

        assert workload is not None
        assert isinstance(workload, (int, dict))
