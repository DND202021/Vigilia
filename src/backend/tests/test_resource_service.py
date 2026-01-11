"""Tests for resource service."""

import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.resource_service import ResourceService, ResourceError
from app.models.resource import ResourceType, ResourceStatus
from app.models.agency import Agency


class TestResourceService:
    """Tests for ResourceService."""

    # ==================== Personnel Tests ====================

    @pytest.mark.asyncio
    async def test_create_personnel(self, db_session: AsyncSession, test_agency: Agency):
        """Personnel creation should work with valid data."""
        service = ResourceService(db_session)

        personnel = await service.create_personnel(
            agency_id=test_agency.id,
            name="John Smith",
            badge_number="12345",
            rank="Lieutenant",
            call_sign="L-12",
            specializations=["hazmat", "rescue"],
            certifications=["EMT-B", "Firefighter I"],
        )

        assert personnel.id is not None
        assert personnel.name == "John Smith"
        assert personnel.badge_number == "12345"
        assert personnel.rank == "Lieutenant"
        assert personnel.status == ResourceStatus.AVAILABLE
        assert "hazmat" in personnel.specializations

    @pytest.mark.asyncio
    async def test_create_personnel_invalid_agency(self, db_session: AsyncSession):
        """Personnel creation should fail for invalid agency."""
        service = ResourceService(db_session)

        with pytest.raises(ResourceError) as exc_info:
            await service.create_personnel(
                agency_id=uuid.uuid4(),
                name="John Smith",
                badge_number="12345",
            )

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_personnel(self, db_session: AsyncSession, test_agency: Agency):
        """Listing personnel should work."""
        service = ResourceService(db_session)

        await service.create_personnel(
            agency_id=test_agency.id,
            name="John Smith",
            badge_number="12345",
        )
        await service.create_personnel(
            agency_id=test_agency.id,
            name="Jane Doe",
            badge_number="12346",
        )

        personnel = await service.list_personnel(agency_id=test_agency.id)
        assert len(personnel) == 2

    # ==================== Vehicle Tests ====================

    @pytest.mark.asyncio
    async def test_create_vehicle(self, db_session: AsyncSession, test_agency: Agency):
        """Vehicle creation should work with valid data."""
        service = ResourceService(db_session)

        vehicle = await service.create_vehicle(
            agency_id=test_agency.id,
            name="Engine 1",
            vehicle_type="fire_engine",
            call_sign="E-1",
            make="Pierce",
            model="Arrow XT",
            year=2020,
            license_plate="FD1234",
        )

        assert vehicle.id is not None
        assert vehicle.name == "Engine 1"
        assert vehicle.vehicle_type == "fire_engine"
        assert vehicle.status == ResourceStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_list_vehicles(self, db_session: AsyncSession, test_agency: Agency):
        """Listing vehicles should work with filters."""
        service = ResourceService(db_session)

        await service.create_vehicle(
            agency_id=test_agency.id,
            name="Engine 1",
            vehicle_type="fire_engine",
        )
        await service.create_vehicle(
            agency_id=test_agency.id,
            name="Ambulance 1",
            vehicle_type="ambulance",
        )

        # All vehicles
        all_vehicles = await service.list_vehicles(agency_id=test_agency.id)
        assert len(all_vehicles) == 2

        # Filter by type
        engines = await service.list_vehicles(
            agency_id=test_agency.id,
            vehicle_type="fire_engine",
        )
        assert len(engines) == 1

    # ==================== Equipment Tests ====================

    @pytest.mark.asyncio
    async def test_create_equipment(self, db_session: AsyncSession, test_agency: Agency):
        """Equipment creation should work with valid data."""
        service = ResourceService(db_session)

        equipment = await service.create_equipment(
            agency_id=test_agency.id,
            name="Thermal Camera",
            equipment_type="imaging",
            serial_number="TC-12345",
            manufacturer="FLIR",
        )

        assert equipment.id is not None
        assert equipment.name == "Thermal Camera"
        assert equipment.equipment_type == "imaging"
        assert equipment.status == ResourceStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_list_equipment(self, db_session: AsyncSession, test_agency: Agency):
        """Listing equipment should work."""
        service = ResourceService(db_session)

        await service.create_equipment(
            agency_id=test_agency.id,
            name="Thermal Camera",
            equipment_type="imaging",
        )
        await service.create_equipment(
            agency_id=test_agency.id,
            name="Jaws of Life",
            equipment_type="extrication",
        )

        equipment = await service.list_equipment(agency_id=test_agency.id)
        assert len(equipment) == 2

    # ==================== Common Operations Tests ====================

    @pytest.mark.asyncio
    async def test_update_status(self, db_session: AsyncSession, test_agency: Agency):
        """Updating resource status should work."""
        service = ResourceService(db_session)

        personnel = await service.create_personnel(
            agency_id=test_agency.id,
            name="John Smith",
            badge_number="12345",
        )

        updated = await service.update_status(
            resource_id=personnel.id,
            status=ResourceStatus.ASSIGNED,
        )

        assert updated.status == ResourceStatus.ASSIGNED

    @pytest.mark.asyncio
    async def test_update_location(self, db_session: AsyncSession, test_agency: Agency):
        """Updating resource location should work."""
        service = ResourceService(db_session)

        vehicle = await service.create_vehicle(
            agency_id=test_agency.id,
            name="Engine 1",
            vehicle_type="fire_engine",
        )

        updated = await service.update_location(
            resource_id=vehicle.id,
            latitude=45.5017,
            longitude=-73.5673,
        )

        assert updated.current_latitude == 45.5017
        assert updated.current_longitude == -73.5673
        assert updated.location_updated_at is not None

    @pytest.mark.asyncio
    async def test_get_available_resources(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Getting available resources should work."""
        service = ResourceService(db_session)

        # Create resources
        await service.create_personnel(
            agency_id=test_agency.id,
            name="John Smith",
            badge_number="12345",
        )
        vehicle = await service.create_vehicle(
            agency_id=test_agency.id,
            name="Engine 1",
            vehicle_type="fire_engine",
        )

        # Mark vehicle as assigned
        await service.update_status(vehicle.id, ResourceStatus.ASSIGNED)

        available = await service.get_available_resources(agency_id=test_agency.id)

        assert len(available["personnel"]) == 1
        assert len(available["vehicles"]) == 0  # Marked as assigned

    @pytest.mark.asyncio
    async def test_get_available_resources_by_proximity(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Getting available resources by proximity should work."""
        service = ResourceService(db_session)

        # Create vehicles with locations
        v1 = await service.create_vehicle(
            agency_id=test_agency.id,
            name="Engine 1",
            vehicle_type="fire_engine",
        )
        await service.update_location(v1.id, 45.5017, -73.5673)  # Montreal

        v2 = await service.create_vehicle(
            agency_id=test_agency.id,
            name="Engine 2",
            vehicle_type="fire_engine",
        )
        await service.update_location(v2.id, 48.8566, 2.3522)  # Paris - far away

        # Search near Montreal with 50km radius
        available = await service.get_available_resources(
            agency_id=test_agency.id,
            near_latitude=45.5017,
            near_longitude=-73.5673,
            radius_km=50.0,
        )

        assert len(available["vehicles"]) == 1
        assert available["vehicles"][0].name == "Engine 1"

    @pytest.mark.asyncio
    async def test_assign_personnel_to_vehicle(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Assigning personnel to vehicle should work."""
        service = ResourceService(db_session)

        personnel = await service.create_personnel(
            agency_id=test_agency.id,
            name="John Smith",
            badge_number="12345",
        )
        vehicle = await service.create_vehicle(
            agency_id=test_agency.id,
            name="Engine 1",
            vehicle_type="fire_engine",
        )

        assigned = await service.assign_personnel_to_vehicle(
            personnel_id=personnel.id,
            vehicle_id=vehicle.id,
        )

        assert assigned.assigned_vehicle_id == vehicle.id

    @pytest.mark.asyncio
    async def test_get_resource_stats(
        self, db_session: AsyncSession, test_agency: Agency
    ):
        """Getting resource statistics should work."""
        service = ResourceService(db_session)

        # Create resources
        p1 = await service.create_personnel(
            agency_id=test_agency.id,
            name="John Smith",
            badge_number="12345",
        )
        await service.create_vehicle(
            agency_id=test_agency.id,
            name="Engine 1",
            vehicle_type="fire_engine",
        )
        await service.create_equipment(
            agency_id=test_agency.id,
            name="Thermal Camera",
            equipment_type="imaging",
        )

        # Mark one as assigned
        await service.update_status(p1.id, ResourceStatus.ASSIGNED)

        stats = await service.get_resource_stats(agency_id=test_agency.id)

        assert stats["total"] == 3
        assert stats["by_type"]["personnel"] == 1
        assert stats["by_type"]["vehicles"] == 1
        assert stats["by_type"]["equipment"] == 1
        assert stats["by_status"]["available"] == 2
        assert stats["by_status"]["assigned"] == 1

    @pytest.mark.asyncio
    async def test_update_status_not_found(self, db_session: AsyncSession):
        """Updating non-existent resource should fail."""
        service = ResourceService(db_session)

        with pytest.raises(ResourceError) as exc_info:
            await service.update_status(
                resource_id=uuid.uuid4(),
                status=ResourceStatus.ASSIGNED,
            )

        assert "not found" in str(exc_info.value)


class TestHaversineDistance:
    """Tests for distance calculation."""

    def test_same_location(self):
        """Same location should have zero distance."""
        distance = ResourceService._calculate_distance(
            45.5017, -73.5673,
            45.5017, -73.5673,
        )
        assert distance == 0.0

    def test_known_distance(self):
        """Known distance should be approximately correct."""
        # Montreal to Toronto is approximately 504 km
        distance = ResourceService._calculate_distance(
            45.5017, -73.5673,  # Montreal
            43.6532, -79.3832,  # Toronto
        )
        assert 500 < distance < 520  # Allow some tolerance
