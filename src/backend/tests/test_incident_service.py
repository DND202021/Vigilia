"""Tests for incident service."""

import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.incident_service import IncidentService, IncidentError
from app.models.incident import IncidentStatus, IncidentPriority, IncidentCategory
from app.models.agency import Agency
from app.models.user import User


class TestIncidentService:
    """Tests for IncidentService."""

    @pytest.mark.asyncio
    async def test_create_incident(self, db_session: AsyncSession, test_agency: Agency):
        """Incident creation should work with valid data."""
        service = IncidentService(db_session)

        incident = await service.create_incident(
            agency_id=test_agency.id,
            category=IncidentCategory.FIRE,
            title="Structure Fire at 123 Main St",
            latitude=45.5017,
            longitude=-73.5673,
            priority=IncidentPriority.HIGH,
            description="Two-story residential fire",
            address="123 Main St",
        )

        assert incident.id is not None
        assert incident.incident_number.startswith(test_agency.code)
        assert incident.category == IncidentCategory.FIRE
        assert incident.priority == IncidentPriority.HIGH
        assert incident.status == IncidentStatus.NEW
        assert incident.title == "Structure Fire at 123 Main St"
        assert len(incident.timeline_events) == 1
        assert incident.timeline_events[0]["type"] == "created"

    @pytest.mark.asyncio
    async def test_create_incident_invalid_agency(self, db_session: AsyncSession):
        """Incident creation should fail for invalid agency."""
        service = IncidentService(db_session)

        with pytest.raises(IncidentError) as exc_info:
            await service.create_incident(
                agency_id=uuid.uuid4(),  # Non-existent agency
                category=IncidentCategory.FIRE,
                title="Test Fire",
                latitude=45.5017,
                longitude=-73.5673,
            )

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_incident(self, db_session: AsyncSession, test_agency: Agency):
        """Getting incident by ID should work."""
        service = IncidentService(db_session)

        incident = await service.create_incident(
            agency_id=test_agency.id,
            category=IncidentCategory.MEDICAL,
            title="Medical Emergency",
            latitude=45.5017,
            longitude=-73.5673,
        )

        retrieved = await service.get_incident(incident.id)
        assert retrieved is not None
        assert retrieved.id == incident.id

    @pytest.mark.asyncio
    async def test_get_incident_not_found(self, db_session: AsyncSession):
        """Getting non-existent incident should return None."""
        service = IncidentService(db_session)

        retrieved = await service.get_incident(uuid.uuid4())
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_incidents(self, db_session: AsyncSession, test_agency: Agency):
        """Listing incidents should work with filters."""
        service = IncidentService(db_session)

        # Create multiple incidents
        await service.create_incident(
            agency_id=test_agency.id,
            category=IncidentCategory.FIRE,
            title="Fire 1",
            latitude=45.5017,
            longitude=-73.5673,
        )
        await service.create_incident(
            agency_id=test_agency.id,
            category=IncidentCategory.MEDICAL,
            title="Medical 1",
            latitude=45.5017,
            longitude=-73.5673,
        )

        # List all
        all_incidents = await service.list_incidents(agency_id=test_agency.id)
        assert len(all_incidents) == 2

        # Filter by category
        fire_incidents = await service.list_incidents(
            agency_id=test_agency.id,
            category=IncidentCategory.FIRE,
        )
        assert len(fire_incidents) == 1
        assert fire_incidents[0].category == IncidentCategory.FIRE

    @pytest.mark.asyncio
    async def test_update_incident_status(
        self, db_session: AsyncSession, test_agency: Agency, test_user: User
    ):
        """Updating incident status should work."""
        service = IncidentService(db_session)

        incident = await service.create_incident(
            agency_id=test_agency.id,
            category=IncidentCategory.POLICE,
            title="Disturbance Call",
            latitude=45.5017,
            longitude=-73.5673,
        )

        updated = await service.update_incident(
            incident_id=incident.id,
            updated_by=test_user,
            status=IncidentStatus.ASSIGNED,
        )

        assert updated.status == IncidentStatus.ASSIGNED
        assert updated.dispatched_at is not None
        assert len(updated.timeline_events) == 2  # created + updated

    @pytest.mark.asyncio
    async def test_assign_unit(
        self, db_session: AsyncSession, test_agency: Agency, test_user: User
    ):
        """Assigning unit to incident should work."""
        service = IncidentService(db_session)

        incident = await service.create_incident(
            agency_id=test_agency.id,
            category=IncidentCategory.FIRE,
            title="Fire Call",
            latitude=45.5017,
            longitude=-73.5673,
        )

        unit_id = uuid.uuid4()
        updated = await service.assign_unit(
            incident_id=incident.id,
            unit_id=unit_id,
            assigned_by=test_user,
        )

        assert str(unit_id) in updated.assigned_units
        assert updated.status == IncidentStatus.ASSIGNED  # Auto-updated from NEW

    @pytest.mark.asyncio
    async def test_assign_unit_duplicate(
        self, db_session: AsyncSession, test_agency: Agency, test_user: User
    ):
        """Assigning same unit twice should fail."""
        service = IncidentService(db_session)

        incident = await service.create_incident(
            agency_id=test_agency.id,
            category=IncidentCategory.FIRE,
            title="Fire Call",
            latitude=45.5017,
            longitude=-73.5673,
        )

        unit_id = uuid.uuid4()
        await service.assign_unit(
            incident_id=incident.id,
            unit_id=unit_id,
            assigned_by=test_user,
        )

        with pytest.raises(IncidentError) as exc_info:
            await service.assign_unit(
                incident_id=incident.id,
                unit_id=unit_id,
                assigned_by=test_user,
            )

        assert "already assigned" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unassign_unit(
        self, db_session: AsyncSession, test_agency: Agency, test_user: User
    ):
        """Unassigning unit from incident should work."""
        service = IncidentService(db_session)

        incident = await service.create_incident(
            agency_id=test_agency.id,
            category=IncidentCategory.FIRE,
            title="Fire Call",
            latitude=45.5017,
            longitude=-73.5673,
        )

        unit_id = uuid.uuid4()
        await service.assign_unit(
            incident_id=incident.id,
            unit_id=unit_id,
            assigned_by=test_user,
        )

        updated = await service.unassign_unit(
            incident_id=incident.id,
            unit_id=unit_id,
            unassigned_by=test_user,
            reason="Reassigned to higher priority",
        )

        assert str(unit_id) not in updated.assigned_units

    @pytest.mark.asyncio
    async def test_escalate_incident(
        self, db_session: AsyncSession, test_agency: Agency, test_user: User
    ):
        """Escalating incident should increase priority."""
        service = IncidentService(db_session)

        incident = await service.create_incident(
            agency_id=test_agency.id,
            category=IncidentCategory.FIRE,
            title="Fire Call",
            latitude=45.5017,
            longitude=-73.5673,
            priority=IncidentPriority.MEDIUM,
        )

        escalated = await service.escalate_incident(
            incident_id=incident.id,
            escalated_by=test_user,
            reason="Spreading to adjacent buildings",
        )

        assert escalated.priority == IncidentPriority.HIGH  # Escalated from MEDIUM

    @pytest.mark.asyncio
    async def test_close_incident(
        self, db_session: AsyncSession, test_agency: Agency, test_user: User
    ):
        """Closing incident should work."""
        service = IncidentService(db_session)

        incident = await service.create_incident(
            agency_id=test_agency.id,
            category=IncidentCategory.FIRE,
            title="Fire Call",
            latitude=45.5017,
            longitude=-73.5673,
        )

        closed = await service.close_incident(
            incident_id=incident.id,
            closed_by=test_user,
            resolution_notes="Fire extinguished, no injuries",
        )

        assert closed.status == IncidentStatus.CLOSED
        assert closed.closed_at is not None

    @pytest.mark.asyncio
    async def test_close_already_closed(
        self, db_session: AsyncSession, test_agency: Agency, test_user: User
    ):
        """Closing already closed incident should fail."""
        service = IncidentService(db_session)

        incident = await service.create_incident(
            agency_id=test_agency.id,
            category=IncidentCategory.FIRE,
            title="Fire Call",
            latitude=45.5017,
            longitude=-73.5673,
        )

        await service.close_incident(
            incident_id=incident.id,
            closed_by=test_user,
        )

        with pytest.raises(IncidentError) as exc_info:
            await service.close_incident(
                incident_id=incident.id,
                closed_by=test_user,
            )

        assert "already closed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_timeline(
        self, db_session: AsyncSession, test_agency: Agency, test_user: User
    ):
        """Getting incident timeline should work."""
        service = IncidentService(db_session)

        incident = await service.create_incident(
            agency_id=test_agency.id,
            category=IncidentCategory.FIRE,
            title="Fire Call",
            latitude=45.5017,
            longitude=-73.5673,
        )

        await service.update_incident(
            incident_id=incident.id,
            updated_by=test_user,
            status=IncidentStatus.ASSIGNED,
        )

        timeline = await service.get_timeline(incident.id)

        assert len(timeline) == 2
        assert timeline[0]["type"] == "created"
        assert timeline[1]["type"] == "updated"

    @pytest.mark.asyncio
    async def test_get_active_incidents_count(
        self, db_session: AsyncSession, test_agency: Agency, test_user: User
    ):
        """Getting active incidents count should work."""
        service = IncidentService(db_session)

        # Create incidents
        await service.create_incident(
            agency_id=test_agency.id,
            category=IncidentCategory.FIRE,
            title="Fire 1",
            latitude=45.5017,
            longitude=-73.5673,
        )
        incident2 = await service.create_incident(
            agency_id=test_agency.id,
            category=IncidentCategory.MEDICAL,
            title="Medical 1",
            latitude=45.5017,
            longitude=-73.5673,
        )

        # Close one
        await service.close_incident(incident2.id, test_user)

        count = await service.get_active_incidents_count(test_agency.id)
        assert count == 1
