"""Tests for building service."""

import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.building_service import BuildingService, BuildingError
from app.models.building import BuildingType, OccupancyType, ConstructionType, HazardLevel
from app.models.agency import Agency


class TestBuildingService:
    """Tests for BuildingService."""

    # ==================== Building CRUD Tests ====================

    @pytest.mark.asyncio
    async def test_create_building(self, db_session: AsyncSession, test_agency: Agency):
        """Building creation should work with valid data."""
        service = BuildingService(db_session)

        building = await service.create_building(
            agency_id=test_agency.id,
            name="City Hall",
            civic_number="100",
            street_name="Main",
            street_type="Street",
            city="Montreal",
            province_state="Quebec",
            postal_code="H2X 1Y1",
            latitude=45.5017,
            longitude=-73.5673,
            building_type=BuildingType.GOVERNMENT,
            total_floors=5,
            has_elevator=True,
            elevator_count=2,
        )

        assert building.id is not None
        assert building.name == "City Hall"
        assert building.city == "Montreal"
        assert building.building_type == BuildingType.GOVERNMENT
        assert building.total_floors == 5
        assert building.has_elevator is True
        assert "100 Main Street" in building.full_address

    @pytest.mark.asyncio
    async def test_create_building_invalid_agency(self, db_session: AsyncSession):
        """Building creation should fail for invalid agency."""
        service = BuildingService(db_session)

        with pytest.raises(BuildingError) as exc_info:
            await service.create_building(
                agency_id=uuid.uuid4(),
                name="Test Building",
                street_name="Test Street",
                city="Montreal",
                province_state="Quebec",
                latitude=45.5017,
                longitude=-73.5673,
            )

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_building(self, db_session: AsyncSession, test_agency: Agency):
        """Getting a building by ID should work."""
        service = BuildingService(db_session)

        created = await service.create_building(
            agency_id=test_agency.id,
            name="Test Building",
            street_name="Test Street",
            city="Montreal",
            province_state="Quebec",
            latitude=45.5017,
            longitude=-73.5673,
        )

        retrieved = await service.get_building(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Test Building"

    @pytest.mark.asyncio
    async def test_get_building_not_found(self, db_session: AsyncSession):
        """Getting a non-existent building should return None."""
        service = BuildingService(db_session)

        result = await service.get_building(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_buildings(self, db_session: AsyncSession, test_agency: Agency):
        """Listing buildings should work with filters."""
        service = BuildingService(db_session)

        await service.create_building(
            agency_id=test_agency.id,
            name="Building 1",
            street_name="First Street",
            city="Montreal",
            province_state="Quebec",
            latitude=45.5017,
            longitude=-73.5673,
            building_type=BuildingType.COMMERCIAL,
        )
        await service.create_building(
            agency_id=test_agency.id,
            name="Building 2",
            street_name="Second Street",
            city="Laval",
            province_state="Quebec",
            latitude=45.5680,
            longitude=-73.7490,
            building_type=BuildingType.RESIDENTIAL_MULTI,
        )

        # All buildings
        buildings, total = await service.list_buildings(agency_id=test_agency.id)
        assert len(buildings) == 2
        assert total == 2

        # Filter by city
        montreal_buildings, _ = await service.list_buildings(
            agency_id=test_agency.id,
            city="Montreal",
        )
        assert len(montreal_buildings) == 1
        assert montreal_buildings[0].name == "Building 1"

        # Filter by type
        commercial_buildings, _ = await service.list_buildings(
            agency_id=test_agency.id,
            building_type=BuildingType.COMMERCIAL,
        )
        assert len(commercial_buildings) == 1

    @pytest.mark.asyncio
    async def test_update_building(self, db_session: AsyncSession, test_agency: Agency):
        """Updating a building should work."""
        service = BuildingService(db_session)

        building = await service.create_building(
            agency_id=test_agency.id,
            name="Original Name",
            street_name="Test Street",
            city="Montreal",
            province_state="Quebec",
            latitude=45.5017,
            longitude=-73.5673,
        )

        updated = await service.update_building(
            building.id,
            name="Updated Name",
            has_sprinkler_system=True,
            hazard_level=HazardLevel.HIGH,
        )

        assert updated.name == "Updated Name"
        assert updated.has_sprinkler_system is True
        assert updated.hazard_level == HazardLevel.HIGH

    @pytest.mark.asyncio
    async def test_delete_building(self, db_session: AsyncSession, test_agency: Agency):
        """Soft deleting a building should work."""
        service = BuildingService(db_session)

        building = await service.create_building(
            agency_id=test_agency.id,
            name="To Delete",
            street_name="Test Street",
            city="Montreal",
            province_state="Quebec",
            latitude=45.5017,
            longitude=-73.5673,
        )

        await service.delete_building(building.id)

        # Should not be found after deletion
        result = await service.get_building(building.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_building(self, db_session: AsyncSession, test_agency: Agency, test_user):
        """Verifying a building should work."""
        service = BuildingService(db_session)

        building = await service.create_building(
            agency_id=test_agency.id,
            name="Test Building",
            street_name="Test Street",
            city="Montreal",
            province_state="Quebec",
            latitude=45.5017,
            longitude=-73.5673,
        )

        assert building.is_verified is False

        verified = await service.verify_building(building.id, test_user.id)

        assert verified.is_verified is True
        assert verified.verified_by_id == test_user.id
        assert verified.verified_at is not None

    # ==================== Floor Plan Tests ====================

    @pytest.mark.asyncio
    async def test_add_floor_plan(self, db_session: AsyncSession, test_agency: Agency):
        """Adding a floor plan should work."""
        service = BuildingService(db_session)

        building = await service.create_building(
            agency_id=test_agency.id,
            name="Test Building",
            street_name="Test Street",
            city="Montreal",
            province_state="Quebec",
            latitude=45.5017,
            longitude=-73.5673,
            total_floors=3,
        )

        floor_plan = await service.add_floor_plan(
            building_id=building.id,
            floor_number=1,
            floor_name="Ground Floor",
            floor_area_sqm=500.0,
            ceiling_height_m=3.5,
            key_locations=[
                {"type": "stairwell", "name": "Main Stairs", "x": 100, "y": 200},
                {"type": "elevator", "name": "Elevator 1", "x": 150, "y": 200},
            ],
        )

        assert floor_plan.id is not None
        assert floor_plan.floor_number == 1
        assert floor_plan.floor_name == "Ground Floor"
        assert len(floor_plan.key_locations) == 2

    @pytest.mark.asyncio
    async def test_add_duplicate_floor_plan(self, db_session: AsyncSession, test_agency: Agency):
        """Adding a duplicate floor plan should fail."""
        service = BuildingService(db_session)

        building = await service.create_building(
            agency_id=test_agency.id,
            name="Test Building",
            street_name="Test Street",
            city="Montreal",
            province_state="Quebec",
            latitude=45.5017,
            longitude=-73.5673,
        )

        await service.add_floor_plan(
            building_id=building.id,
            floor_number=1,
        )

        with pytest.raises(BuildingError) as exc_info:
            await service.add_floor_plan(
                building_id=building.id,
                floor_number=1,
            )

        assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_building_floor_plans(self, db_session: AsyncSession, test_agency: Agency):
        """Getting floor plans should return them in order."""
        service = BuildingService(db_session)

        building = await service.create_building(
            agency_id=test_agency.id,
            name="Test Building",
            street_name="Test Street",
            city="Montreal",
            province_state="Quebec",
            latitude=45.5017,
            longitude=-73.5673,
            total_floors=3,
            basement_levels=1,
        )

        # Add floors in random order
        await service.add_floor_plan(building_id=building.id, floor_number=2)
        await service.add_floor_plan(building_id=building.id, floor_number=-1)  # Basement
        await service.add_floor_plan(building_id=building.id, floor_number=0)  # Ground
        await service.add_floor_plan(building_id=building.id, floor_number=1)

        floor_plans = await service.get_building_floor_plans(building.id)

        assert len(floor_plans) == 4
        # Should be sorted by floor number
        assert floor_plans[0].floor_number == -1
        assert floor_plans[1].floor_number == 0
        assert floor_plans[2].floor_number == 1
        assert floor_plans[3].floor_number == 2

    # ==================== Search Tests ====================

    @pytest.mark.asyncio
    async def test_search_buildings(self, db_session: AsyncSession, test_agency: Agency):
        """Searching buildings should work."""
        service = BuildingService(db_session)

        await service.create_building(
            agency_id=test_agency.id,
            name="Fire Station 1",
            street_name="Main Street",
            city="Montreal",
            province_state="Quebec",
            latitude=45.5017,
            longitude=-73.5673,
        )
        await service.create_building(
            agency_id=test_agency.id,
            name="Police Station",
            street_name="Oak Avenue",
            city="Montreal",
            province_state="Quebec",
            latitude=45.5100,
            longitude=-73.5700,
        )

        # Search by name
        results = await service.search_buildings("Fire", agency_id=test_agency.id)
        assert len(results) == 1
        assert results[0].name == "Fire Station 1"

        # Search by address
        results = await service.search_buildings("Main", agency_id=test_agency.id)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_find_building_at_location(self, db_session: AsyncSession, test_agency: Agency):
        """Finding building at location should work."""
        service = BuildingService(db_session)

        building = await service.create_building(
            agency_id=test_agency.id,
            name="Target Building",
            street_name="Test Street",
            city="Montreal",
            province_state="Quebec",
            latitude=45.5017,
            longitude=-73.5673,
        )

        # Search at exact location
        found = await service.find_building_at_location(45.5017, -73.5673)
        assert found is not None
        assert found.id == building.id

        # Search nearby (within 50m)
        found = await service.find_building_at_location(45.5018, -73.5674, radius_meters=50.0)
        assert found is not None

        # Search too far away
        found = await service.find_building_at_location(45.6000, -73.6000, radius_meters=50.0)
        assert found is None

    @pytest.mark.asyncio
    async def test_get_buildings_near_incident(self, db_session: AsyncSession, test_agency: Agency):
        """Getting buildings near incident location should work."""
        service = BuildingService(db_session)

        await service.create_building(
            agency_id=test_agency.id,
            name="Close Building",
            street_name="Near Street",
            city="Montreal",
            province_state="Quebec",
            latitude=45.5017,
            longitude=-73.5673,
        )
        await service.create_building(
            agency_id=test_agency.id,
            name="Far Building",
            street_name="Far Street",
            city="Montreal",
            province_state="Quebec",
            latitude=45.6000,
            longitude=-73.7000,
        )

        # Get buildings within 1km of incident
        nearby = await service.get_buildings_near_incident(
            latitude=45.5020,
            longitude=-73.5670,
            radius_km=1.0,
        )

        assert len(nearby) == 1
        assert nearby[0][0].name == "Close Building"
        assert nearby[0][1] < 1.0  # Distance should be less than 1km

    # ==================== BIM Import Tests ====================

    @pytest.mark.asyncio
    async def test_import_bim_data(self, db_session: AsyncSession, test_agency: Agency):
        """BIM data import should work."""
        service = BuildingService(db_session)

        building = await service.create_building(
            agency_id=test_agency.id,
            name="BIM Building",
            street_name="Tech Street",
            city="Montreal",
            province_state="Quebec",
            latitude=45.5017,
            longitude=-73.5673,
            total_floors=2,
        )

        bim_data = {
            "total_area": 1500.0,
            "height": 10.5,
            "floors": [
                {"number": 0, "name": "Ground Floor", "area": 750.0, "ceiling_height": 3.5},
                {"number": 1, "name": "First Floor", "area": 750.0, "ceiling_height": 3.0},
            ],
        }

        updated = await service.import_bim_data(
            building.id,
            bim_data=bim_data,
            bim_file_url="https://example.com/building.ifc",
        )

        assert updated.bim_data == bim_data
        assert updated.bim_file_url == "https://example.com/building.ifc"
        assert updated.total_area_sqm == 1500.0
        assert updated.building_height_m == 10.5

        # Should have created floor plans
        floor_plans = await service.get_building_floor_plans(building.id)
        assert len(floor_plans) == 2

    # ==================== Statistics Tests ====================

    @pytest.mark.asyncio
    async def test_get_building_stats(self, db_session: AsyncSession, test_agency: Agency):
        """Getting building statistics should work."""
        service = BuildingService(db_session)

        await service.create_building(
            agency_id=test_agency.id,
            name="Building 1",
            street_name="Street 1",
            city="Montreal",
            province_state="Quebec",
            latitude=45.5017,
            longitude=-73.5673,
            building_type=BuildingType.COMMERCIAL,
            has_hazmat=True,
            has_sprinkler_system=True,
            total_floors=10,  # High-rise
        )
        await service.create_building(
            agency_id=test_agency.id,
            name="Building 2",
            street_name="Street 2",
            city="Montreal",
            province_state="Quebec",
            latitude=45.5020,
            longitude=-73.5680,
            building_type=BuildingType.RESIDENTIAL_MULTI,
            hazard_level=HazardLevel.HIGH,
        )

        stats = await service.get_building_stats(agency_id=test_agency.id)

        assert stats["total"] == 2
        assert stats["with_hazmat"] == 1
        assert stats["with_sprinkler"] == 1
        assert stats["high_rise"] == 1
        assert stats["by_type"]["commercial"] == 1
        assert stats["by_type"]["residential_multi"] == 1
        assert stats["by_hazard_level"]["high"] == 1


class TestBuildingServiceHelpers:
    """Tests for BuildingService helper methods."""

    def test_build_full_address(self):
        """Building full address should work correctly."""
        address = BuildingService._build_full_address(
            civic_number="100",
            street_name="Main",
            street_type="Street",
            unit_number="101",
            city="Montreal",
            province_state="Quebec",
            postal_code="H2X 1Y1",
            country="Canada",
        )

        assert "100 Main Street" in address
        assert "#101" in address
        assert "Montreal" in address
        assert "Quebec" in address
        assert "H2X 1Y1" in address

    def test_calculate_distance(self):
        """Distance calculation should be accurate."""
        # Montreal to Laval (approximately 15km)
        distance = BuildingService._calculate_distance(
            45.5017, -73.5673,  # Montreal
            45.5680, -73.7490,  # Laval
        )

        assert 10 < distance < 20  # Should be around 15km

    def test_default_floor_name(self):
        """Default floor name generation should work."""
        assert BuildingService._default_floor_name(-1) == "Sous-sol 1"
        assert BuildingService._default_floor_name(-2) == "Sous-sol 2"
        assert BuildingService._default_floor_name(0) == "Rez-de-chaussée"
        assert BuildingService._default_floor_name(1) == "Étage 1"
        assert BuildingService._default_floor_name(5) == "Étage 5"
