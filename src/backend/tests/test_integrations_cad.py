"""Tests for CAD system integration."""

import pytest
from datetime import datetime, timezone
import uuid

from app.integrations.cad.base import (
    CADIncident,
    CADUnit,
    CADIncidentStatus,
    CADUnitStatus,
)
from app.integrations.cad.mock_adapter import MockCADAdapter
from app.integrations.cad.sync_service import CADSyncService


class TestCADDataClasses:
    """Tests for CAD data structures."""

    def test_create_cad_incident(self):
        """Should create CAD incident with all fields."""
        incident = CADIncident(
            cad_incident_id="INC-001",
            incident_type="FIRE",
            priority=2,
            status=CADIncidentStatus.PENDING,
            location_address="123 Main St",
            location_coordinates=(45.5017, -73.5673),
            caller_name="John Doe",
            caller_phone="555-1234",
        )

        assert incident.cad_incident_id == "INC-001"
        assert incident.incident_type == "FIRE"
        assert incident.priority == 2
        assert incident.status == CADIncidentStatus.PENDING

    def test_create_cad_unit(self):
        """Should create CAD unit with all fields."""
        unit = CADUnit(
            cad_unit_id="E1",
            unit_name="Engine 1",
            unit_type="fire",
            status=CADUnitStatus.AVAILABLE,
            location=(45.5017, -73.5673),
            capabilities=["fire", "rescue"],
        )

        assert unit.cad_unit_id == "E1"
        assert unit.unit_type == "fire"
        assert unit.status == CADUnitStatus.AVAILABLE
        assert "fire" in unit.capabilities


class TestMockCADAdapter:
    """Tests for mock CAD adapter."""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Should track connection state."""
        adapter = MockCADAdapter()

        assert not adapter.is_connected
        await adapter.connect()
        assert adapter.is_connected
        await adapter.disconnect()
        assert not adapter.is_connected

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Should return health status."""
        adapter = MockCADAdapter()
        await adapter.connect()

        health = await adapter.health_check()

        assert health["healthy"] is True
        assert "incidents_count" in health
        assert "units_count" in health

    @pytest.mark.asyncio
    async def test_create_incident(self):
        """Should create incident with generated ID."""
        adapter = MockCADAdapter()
        await adapter.connect()

        incident = CADIncident(
            cad_incident_id="",  # Will be assigned
            incident_type="MEDICAL",
            priority=1,
            status=CADIncidentStatus.PENDING,
            location_address="456 Oak Ave",
        )

        cad_id = await adapter.create_incident(incident)

        assert cad_id.startswith("INC-")
        retrieved = await adapter.get_incident(cad_id)
        assert retrieved is not None
        assert retrieved.incident_type == "MEDICAL"

    @pytest.mark.asyncio
    async def test_get_active_incidents(self):
        """Should return only active incidents."""
        adapter = MockCADAdapter()
        await adapter.connect()

        # Create two incidents
        incident1 = CADIncident(
            cad_incident_id="",
            incident_type="FIRE",
            priority=2,
            status=CADIncidentStatus.PENDING,
            location_address="123 Main St",
        )
        incident2 = CADIncident(
            cad_incident_id="",
            incident_type="POLICE",
            priority=3,
            status=CADIncidentStatus.PENDING,
            location_address="456 Oak Ave",
        )

        id1 = await adapter.create_incident(incident1)
        id2 = await adapter.create_incident(incident2)

        # Close one
        await adapter.close_incident(id1)

        active = await adapter.get_active_incidents()
        active_ids = [i.cad_incident_id for i in active]

        assert id1 not in active_ids
        assert id2 in active_ids

    @pytest.mark.asyncio
    async def test_update_incident(self):
        """Should update incident fields."""
        adapter = MockCADAdapter()
        await adapter.connect()

        incident = CADIncident(
            cad_incident_id="",
            incident_type="FIRE",
            priority=3,
            status=CADIncidentStatus.PENDING,
            location_address="123 Main St",
        )
        cad_id = await adapter.create_incident(incident)

        success = await adapter.update_incident(cad_id, {
            "priority": 1,
            "narrative": "Upgraded to high priority",
        })

        assert success is True
        updated = await adapter.get_incident(cad_id)
        assert updated.priority == 1
        assert updated.narrative == "Upgraded to high priority"

    @pytest.mark.asyncio
    async def test_add_narrative(self):
        """Should append narrative entries."""
        adapter = MockCADAdapter()
        await adapter.connect()

        incident = CADIncident(
            cad_incident_id="",
            incident_type="POLICE",
            priority=2,
            status=CADIncidentStatus.PENDING,
            location_address="789 Elm St",
        )
        cad_id = await adapter.create_incident(incident)

        await adapter.add_incident_narrative(cad_id, "First update")
        await adapter.add_incident_narrative(cad_id, "Second update")

        updated = await adapter.get_incident(cad_id)
        assert "First update" in updated.narrative
        assert "Second update" in updated.narrative

    @pytest.mark.asyncio
    async def test_get_available_units(self):
        """Should return available units."""
        adapter = MockCADAdapter()
        await adapter.connect()

        units = await adapter.get_available_units()
        assert len(units) > 0
        assert all(u.status == CADUnitStatus.AVAILABLE for u in units)

    @pytest.mark.asyncio
    async def test_filter_units_by_type(self):
        """Should filter units by type."""
        adapter = MockCADAdapter()
        await adapter.connect()

        fire_units = await adapter.get_available_units(unit_type="fire")
        ems_units = await adapter.get_available_units(unit_type="ems")

        assert all(u.unit_type == "fire" for u in fire_units)
        assert all(u.unit_type == "ems" for u in ems_units)

    @pytest.mark.asyncio
    async def test_dispatch_unit(self):
        """Should dispatch unit to incident."""
        adapter = MockCADAdapter()
        await adapter.connect()

        # Create incident
        incident = CADIncident(
            cad_incident_id="",
            incident_type="FIRE",
            priority=2,
            status=CADIncidentStatus.PENDING,
            location_address="123 Main St",
        )
        cad_id = await adapter.create_incident(incident)

        # Get available unit
        units = await adapter.get_available_units(unit_type="fire")
        unit_id = units[0].cad_unit_id

        # Dispatch
        success = await adapter.dispatch_unit(unit_id, cad_id)

        assert success is True

        # Check unit status
        unit = await adapter.get_unit(unit_id)
        assert unit.status == CADUnitStatus.DISPATCHED
        assert unit.current_incident_id == cad_id

        # Check incident
        updated_incident = await adapter.get_incident(cad_id)
        assert unit_id in updated_incident.assigned_units
        assert updated_incident.status == CADIncidentStatus.DISPATCHED

    @pytest.mark.asyncio
    async def test_dispatch_unavailable_unit_fails(self):
        """Should fail to dispatch unavailable unit."""
        adapter = MockCADAdapter()
        await adapter.connect()

        # Create incident and dispatch a unit
        incident = CADIncident(
            cad_incident_id="",
            incident_type="FIRE",
            priority=2,
            status=CADIncidentStatus.PENDING,
            location_address="123 Main St",
        )
        cad_id = await adapter.create_incident(incident)

        units = await adapter.get_available_units(unit_type="fire")
        unit_id = units[0].cad_unit_id

        # First dispatch succeeds
        await adapter.dispatch_unit(unit_id, cad_id)

        # Second dispatch should fail
        incident2 = CADIncident(
            cad_incident_id="",
            incident_type="FIRE",
            priority=1,
            status=CADIncidentStatus.PENDING,
            location_address="456 Oak Ave",
        )
        cad_id2 = await adapter.create_incident(incident2)

        with pytest.raises(Exception) as exc_info:
            await adapter.dispatch_unit(unit_id, cad_id2)

        assert "not available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_unit_status(self):
        """Should update unit status."""
        adapter = MockCADAdapter()
        await adapter.connect()

        units = await adapter.get_available_units()
        unit_id = units[0].cad_unit_id

        await adapter.update_unit_status(unit_id, CADUnitStatus.OUT_OF_SERVICE)

        unit = await adapter.get_unit(unit_id)
        assert unit.status == CADUnitStatus.OUT_OF_SERVICE

    @pytest.mark.asyncio
    async def test_close_incident_releases_units(self):
        """Should release units when incident closes."""
        adapter = MockCADAdapter()
        await adapter.connect()

        # Create and dispatch
        incident = CADIncident(
            cad_incident_id="",
            incident_type="FIRE",
            priority=2,
            status=CADIncidentStatus.PENDING,
            location_address="123 Main St",
        )
        cad_id = await adapter.create_incident(incident)

        units = await adapter.get_available_units(unit_type="fire")
        unit_id = units[0].cad_unit_id
        await adapter.dispatch_unit(unit_id, cad_id)

        # Close incident
        await adapter.close_incident(cad_id)

        # Unit should be available again
        unit = await adapter.get_unit(unit_id)
        assert unit.status == CADUnitStatus.AVAILABLE
        assert unit.current_incident_id is None

    @pytest.mark.asyncio
    async def test_status_mapping_to_cad(self):
        """Should map ERIOP status to CAD status."""
        adapter = MockCADAdapter()

        assert adapter.map_status_to_cad("new") == CADIncidentStatus.PENDING
        assert adapter.map_status_to_cad("assigned") == CADIncidentStatus.DISPATCHED
        assert adapter.map_status_to_cad("on_scene") == CADIncidentStatus.ON_SCENE
        assert adapter.map_status_to_cad("closed") == CADIncidentStatus.CLEARED

    @pytest.mark.asyncio
    async def test_status_mapping_from_cad(self):
        """Should map CAD status to ERIOP status."""
        adapter = MockCADAdapter()

        assert adapter.map_status_from_cad(CADIncidentStatus.PENDING) == "new"
        assert adapter.map_status_from_cad(CADIncidentStatus.DISPATCHED) == "assigned"
        assert adapter.map_status_from_cad(CADIncidentStatus.ON_SCENE) == "on_scene"
        assert adapter.map_status_from_cad(CADIncidentStatus.CLEARED) == "resolved"


class TestCADSyncService:
    """Tests for CAD sync service."""

    @pytest.mark.asyncio
    async def test_create_sync_service(self):
        """Should create sync service with adapter."""
        adapter = MockCADAdapter()
        await adapter.connect()

        sync = CADSyncService(cad_adapter=adapter)

        assert sync.cad == adapter

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Should return sync statistics."""
        adapter = MockCADAdapter()
        await adapter.connect()

        sync = CADSyncService(cad_adapter=adapter)

        stats = sync.get_stats()

        assert stats["running"] is False
        assert stats["cad_system"] == "MockCAD"
        assert "incidents_synced_from_cad" in stats
        assert "incidents_synced_to_cad" in stats

    @pytest.mark.asyncio
    async def test_mapping_storage(self):
        """Should store and retrieve mappings."""
        adapter = MockCADAdapter()
        await adapter.connect()

        sync = CADSyncService(cad_adapter=adapter)

        eriop_id = uuid.uuid4()
        cad_id = "INC-12345"

        # Simulate creating a mapping
        from app.integrations.cad.base import CADMapping
        mapping = CADMapping(
            entity_type="incident",
            eriop_id=eriop_id,
            cad_id=cad_id,
            cad_system="MockCAD",
        )
        sync._incident_mappings[cad_id] = mapping

        # Retrieve by CAD ID
        found = sync.get_mapping("incident", cad_id=cad_id)
        assert found is not None
        assert found.eriop_id == eriop_id

        # Retrieve by ERIOP ID
        found2 = sync.get_mapping("incident", eriop_id=eriop_id)
        assert found2 is not None
        assert found2.cad_id == cad_id
