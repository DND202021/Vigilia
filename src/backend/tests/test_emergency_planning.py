"""Tests for Sprint 10 Emergency Response Planning.

Comprehensive tests for EmergencyProcedure, EvacuationRoute, and EmergencyCheckpoint
models and API endpoints.
"""

import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from app.models.building import Building, BuildingType, FloorPlan
from app.models.agency import Agency
from app.models.user import User
from app.models.emergency_procedure import EmergencyProcedure, ProcedureType
from app.models.evacuation_route import EvacuationRoute, RouteType
from app.models.emergency_checkpoint import EmergencyCheckpoint, CheckpointType


# ==================== Fixtures ====================


@pytest.fixture
async def emergency_building(db_session: AsyncSession, test_agency: Agency) -> Building:
    """Create a test building for emergency planning tests."""
    building = Building(
        id=uuid.uuid4(),
        agency_id=test_agency.id,
        name="Emergency Planning Test Building",
        street_name="Emergency Street",
        city="Montreal",
        province_state="Quebec",
        latitude=45.5017,
        longitude=-73.5673,
        building_type=BuildingType.COMMERCIAL,
        full_address="100 Emergency Street, Montreal, Quebec",
        total_floors=5,
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def emergency_floor_plan(
    db_session: AsyncSession, emergency_building: Building
) -> FloorPlan:
    """Create a test floor plan for emergency planning tests."""
    floor_plan = FloorPlan(
        id=uuid.uuid4(),
        building_id=emergency_building.id,
        floor_number=1,
        floor_name="Ground Floor",
    )
    db_session.add(floor_plan)
    await db_session.commit()
    await db_session.refresh(floor_plan)
    return floor_plan


@pytest.fixture
async def second_floor_plan(
    db_session: AsyncSession, emergency_building: Building
) -> FloorPlan:
    """Create a second test floor plan for emergency planning tests."""
    floor_plan = FloorPlan(
        id=uuid.uuid4(),
        building_id=emergency_building.id,
        floor_number=2,
        floor_name="Second Floor",
    )
    db_session.add(floor_plan)
    await db_session.commit()
    await db_session.refresh(floor_plan)
    return floor_plan


@pytest.fixture
async def sample_procedure(
    db_session: AsyncSession, emergency_building: Building
) -> EmergencyProcedure:
    """Create a sample emergency procedure."""
    procedure = EmergencyProcedure(
        id=uuid.uuid4(),
        building_id=emergency_building.id,
        name="Fire Evacuation Procedure",
        description="Standard fire evacuation protocol for the building",
        procedure_type=ProcedureType.FIRE,
        priority=1,
        steps=[
            {"order": 1, "title": "Activate alarm", "description": "Pull nearest fire alarm"},
            {"order": 2, "title": "Evacuate", "description": "Use nearest exit"},
            {"order": 3, "title": "Assembly", "description": "Gather at assembly point"},
        ],
        contacts=[
            {"name": "Fire Chief", "role": "Emergency Coordinator", "phone": "555-0100"},
            {"name": "Building Manager", "role": "Support", "phone": "555-0101"},
        ],
        equipment_needed=["fire extinguisher", "first aid kit", "flashlight"],
        estimated_duration_minutes=15,
        is_active=True,
    )
    db_session.add(procedure)
    await db_session.commit()
    await db_session.refresh(procedure)
    return procedure


@pytest.fixture
async def sample_route(
    db_session: AsyncSession, emergency_building: Building, emergency_floor_plan: FloorPlan
) -> EvacuationRoute:
    """Create a sample evacuation route."""
    route = EvacuationRoute(
        id=uuid.uuid4(),
        building_id=emergency_building.id,
        floor_plan_id=emergency_floor_plan.id,
        name="Primary Exit Route A",
        description="Main evacuation route through lobby",
        route_type=RouteType.PRIMARY.value,
        waypoints=[
            {"order": 1, "x": 10.0, "y": 20.0, "label": "Start"},
            {"order": 2, "x": 50.0, "y": 50.0, "label": "Hallway"},
            {"order": 3, "x": 90.0, "y": 80.0, "label": "Exit"},
        ],
        color="#ff0000",
        line_width=3,
        is_active=True,
        capacity=100,
        estimated_time_seconds=60,
        accessibility_features=["wheelchair", "wide_corridors"],
    )
    db_session.add(route)
    await db_session.commit()
    await db_session.refresh(route)
    return route


@pytest.fixture
async def sample_checkpoint(
    db_session: AsyncSession, emergency_building: Building, emergency_floor_plan: FloorPlan
) -> EmergencyCheckpoint:
    """Create a sample emergency checkpoint."""
    checkpoint = EmergencyCheckpoint(
        id=uuid.uuid4(),
        building_id=emergency_building.id,
        floor_plan_id=emergency_floor_plan.id,
        name="Main Assembly Point",
        checkpoint_type=CheckpointType.ASSEMBLY_POINT,
        position_x=75.0,
        position_y=25.0,
        capacity=200,
        equipment=[
            {"name": "First Aid Kit", "quantity": 2, "location": "Cabinet A"},
            {"name": "Emergency Blankets", "quantity": 10, "location": "Storage Box"},
        ],
        responsible_person="John Smith",
        contact_info={"phone": "555-1234", "email": "john@example.com", "radio_channel": "Channel 5"},
        instructions="Wait here until all-clear signal is given.",
        is_active=True,
    )
    db_session.add(checkpoint)
    await db_session.commit()
    await db_session.refresh(checkpoint)
    return checkpoint


# ==================== Model Tests ====================


class TestEmergencyProcedureModel:
    """Tests for EmergencyProcedure model."""

    @pytest.mark.asyncio
    async def test_create_procedure_with_all_fields(
        self, db_session: AsyncSession, emergency_building: Building
    ):
        """Test creating an EmergencyProcedure with all fields."""
        procedure = EmergencyProcedure(
            id=uuid.uuid4(),
            building_id=emergency_building.id,
            name="Complete Procedure",
            description="A comprehensive emergency procedure",
            procedure_type=ProcedureType.HAZMAT,
            priority=2,
            steps=[
                {"order": 1, "title": "Alert", "description": "Notify hazmat team", "duration_minutes": 2},
                {"order": 2, "title": "Contain", "description": "Isolate the area", "duration_minutes": 5},
            ],
            contacts=[
                {"name": "Hazmat Lead", "role": "Coordinator", "phone": "555-0200", "email": "hazmat@example.com"},
            ],
            equipment_needed=["hazmat suit", "respirator", "containment kit"],
            estimated_duration_minutes=45,
            is_active=True,
        )
        db_session.add(procedure)
        await db_session.commit()
        await db_session.refresh(procedure)

        assert procedure.id is not None
        assert procedure.building_id == emergency_building.id
        assert procedure.name == "Complete Procedure"
        assert procedure.description == "A comprehensive emergency procedure"
        assert procedure.procedure_type == ProcedureType.HAZMAT
        assert procedure.priority == 2
        assert len(procedure.steps) == 2
        assert procedure.steps[0]["title"] == "Alert"
        assert len(procedure.contacts) == 1
        assert procedure.contacts[0]["email"] == "hazmat@example.com"
        assert len(procedure.equipment_needed) == 3
        assert procedure.estimated_duration_minutes == 45
        assert procedure.is_active is True

    @pytest.mark.asyncio
    async def test_procedure_steps_json_field(
        self, db_session: AsyncSession, emergency_building: Building
    ):
        """Test that steps JSON field serializes correctly."""
        steps = [
            {"order": 1, "title": "Step 1", "description": "First step", "responsible_role": "Lead", "duration_minutes": 5},
            {"order": 2, "title": "Step 2", "description": "Second step", "responsible_role": "Support", "duration_minutes": 10},
        ]
        procedure = EmergencyProcedure(
            building_id=emergency_building.id,
            name="Steps Test",
            procedure_type=ProcedureType.EVACUATION,
            steps=steps,
        )
        db_session.add(procedure)
        await db_session.commit()
        await db_session.refresh(procedure)

        assert procedure.steps == steps
        assert procedure.steps[0]["responsible_role"] == "Lead"
        assert procedure.steps[1]["duration_minutes"] == 10

    @pytest.mark.asyncio
    async def test_procedure_contacts_json_field(
        self, db_session: AsyncSession, emergency_building: Building
    ):
        """Test that contacts JSON field serializes correctly."""
        contacts = [
            {"name": "Contact A", "role": "Primary", "phone": "111-1111", "email": "a@example.com"},
            {"name": "Contact B", "role": "Backup", "phone": "222-2222", "email": "b@example.com"},
        ]
        procedure = EmergencyProcedure(
            building_id=emergency_building.id,
            name="Contacts Test",
            procedure_type=ProcedureType.MEDICAL,
            contacts=contacts,
        )
        db_session.add(procedure)
        await db_session.commit()
        await db_session.refresh(procedure)

        assert procedure.contacts == contacts
        assert len(procedure.contacts) == 2

    @pytest.mark.asyncio
    async def test_procedure_equipment_json_field(
        self, db_session: AsyncSession, emergency_building: Building
    ):
        """Test that equipment_needed JSON field serializes correctly."""
        equipment = ["item1", "item2", "item3", "item4"]
        procedure = EmergencyProcedure(
            building_id=emergency_building.id,
            name="Equipment Test",
            procedure_type=ProcedureType.FIRE,
            equipment_needed=equipment,
        )
        db_session.add(procedure)
        await db_session.commit()
        await db_session.refresh(procedure)

        assert procedure.equipment_needed == equipment
        assert len(procedure.equipment_needed) == 4

    @pytest.mark.asyncio
    async def test_procedure_soft_delete(
        self, db_session: AsyncSession, sample_procedure: EmergencyProcedure
    ):
        """Test soft delete functionality for EmergencyProcedure."""
        # Initially not deleted
        assert sample_procedure.deleted_at is None
        assert sample_procedure.is_deleted is False

        # Soft delete
        sample_procedure.deleted_at = datetime.now(timezone.utc)
        await db_session.commit()
        await db_session.refresh(sample_procedure)

        assert sample_procedure.deleted_at is not None
        assert sample_procedure.is_deleted is True

    @pytest.mark.asyncio
    async def test_procedure_is_active_default(
        self, db_session: AsyncSession, emergency_building: Building
    ):
        """Test that is_active defaults to True."""
        procedure = EmergencyProcedure(
            building_id=emergency_building.id,
            name="Default Active Test",
            procedure_type=ProcedureType.LOCKDOWN,
        )
        db_session.add(procedure)
        await db_session.commit()
        await db_session.refresh(procedure)

        assert procedure.is_active is True

    @pytest.mark.asyncio
    async def test_procedure_timestamp_auto_generation(
        self, db_session: AsyncSession, emergency_building: Building
    ):
        """Test that created_at and updated_at are auto-generated."""
        procedure = EmergencyProcedure(
            building_id=emergency_building.id,
            name="Timestamp Test",
            procedure_type=ProcedureType.WEATHER,
        )
        db_session.add(procedure)
        await db_session.commit()
        await db_session.refresh(procedure)

        assert procedure.created_at is not None
        assert procedure.updated_at is not None

    @pytest.mark.asyncio
    async def test_procedure_building_relationship(
        self, db_session: AsyncSession, sample_procedure: EmergencyProcedure, emergency_building: Building
    ):
        """Test the building relationship."""
        assert sample_procedure.building_id == emergency_building.id


class TestEvacuationRouteModel:
    """Tests for EvacuationRoute model."""

    @pytest.mark.asyncio
    async def test_create_route_with_all_fields(
        self, db_session: AsyncSession, emergency_building: Building, emergency_floor_plan: FloorPlan
    ):
        """Test creating an EvacuationRoute with all fields."""
        route = EvacuationRoute(
            id=uuid.uuid4(),
            building_id=emergency_building.id,
            floor_plan_id=emergency_floor_plan.id,
            name="Complete Route",
            description="A comprehensive evacuation route",
            route_type=RouteType.ACCESSIBLE.value,
            waypoints=[
                {"order": 1, "x": 5.0, "y": 10.0, "label": "Start Point"},
                {"order": 2, "x": 25.0, "y": 30.0, "label": "Turn Left"},
                {"order": 3, "x": 45.0, "y": 50.0, "label": "Ramp"},
                {"order": 4, "x": 95.0, "y": 90.0, "label": "Exit Door"},
            ],
            color="#00ff00",
            line_width=5,
            is_active=True,
            capacity=50,
            estimated_time_seconds=120,
            accessibility_features=["wheelchair", "no_stairs", "wide_corridors", "automatic_doors"],
        )
        db_session.add(route)
        await db_session.commit()
        await db_session.refresh(route)

        assert route.id is not None
        assert route.building_id == emergency_building.id
        assert route.floor_plan_id == emergency_floor_plan.id
        assert route.name == "Complete Route"
        assert route.route_type == RouteType.ACCESSIBLE.value
        assert len(route.waypoints) == 4
        assert route.color == "#00ff00"
        assert route.line_width == 5
        assert route.capacity == 50
        assert route.estimated_time_seconds == 120
        assert len(route.accessibility_features) == 4

    @pytest.mark.asyncio
    async def test_route_waypoints_json_serialization(
        self, db_session: AsyncSession, emergency_building: Building
    ):
        """Test that waypoints JSON field serializes correctly."""
        waypoints = [
            {"order": 1, "x": 10.5, "y": 20.5, "floor_plan_id": str(uuid.uuid4()), "label": "Point A"},
            {"order": 2, "x": 30.5, "y": 40.5, "floor_plan_id": str(uuid.uuid4()), "label": "Point B"},
        ]
        route = EvacuationRoute(
            building_id=emergency_building.id,
            name="Waypoints Test",
            route_type=RouteType.PRIMARY.value,
            waypoints=waypoints,
        )
        db_session.add(route)
        await db_session.commit()
        await db_session.refresh(route)

        assert route.waypoints == waypoints
        assert route.waypoints[0]["x"] == 10.5
        assert route.waypoints[1]["label"] == "Point B"

    @pytest.mark.asyncio
    async def test_route_floor_plan_relationship(
        self, db_session: AsyncSession, sample_route: EvacuationRoute, emergency_floor_plan: FloorPlan
    ):
        """Test the floor_plan relationship."""
        assert sample_route.floor_plan_id == emergency_floor_plan.id

    @pytest.mark.asyncio
    async def test_route_is_active_default(
        self, db_session: AsyncSession, emergency_building: Building
    ):
        """Test that is_active defaults to True."""
        route = EvacuationRoute(
            building_id=emergency_building.id,
            name="Default Active Route",
            route_type=RouteType.SECONDARY.value,
        )
        db_session.add(route)
        await db_session.commit()
        await db_session.refresh(route)

        assert route.is_active is True

    @pytest.mark.asyncio
    async def test_route_timestamp_auto_generation(
        self, db_session: AsyncSession, emergency_building: Building
    ):
        """Test that created_at and updated_at are auto-generated."""
        route = EvacuationRoute(
            building_id=emergency_building.id,
            name="Timestamp Route",
            route_type=RouteType.EMERGENCY_VEHICLE.value,
        )
        db_session.add(route)
        await db_session.commit()
        await db_session.refresh(route)

        assert route.created_at is not None
        assert route.updated_at is not None


class TestEmergencyCheckpointModel:
    """Tests for EmergencyCheckpoint model."""

    @pytest.mark.asyncio
    async def test_create_checkpoint_with_all_fields(
        self, db_session: AsyncSession, emergency_building: Building, emergency_floor_plan: FloorPlan
    ):
        """Test creating an EmergencyCheckpoint with all fields."""
        checkpoint = EmergencyCheckpoint(
            id=uuid.uuid4(),
            building_id=emergency_building.id,
            floor_plan_id=emergency_floor_plan.id,
            name="Complete Checkpoint",
            checkpoint_type=CheckpointType.COMMAND_POST,
            position_x=50.0,
            position_y=50.0,
            capacity=25,
            equipment=[
                {"name": "Radio", "quantity": 5, "location": "Desk"},
                {"name": "Maps", "quantity": 10, "location": "Wall"},
            ],
            responsible_person="Captain Jane Doe",
            contact_info={"phone": "555-9999", "email": "captain@example.com", "radio_channel": "Command"},
            instructions="Coordinate all emergency response activities from this location.",
            is_active=True,
        )
        db_session.add(checkpoint)
        await db_session.commit()
        await db_session.refresh(checkpoint)

        assert checkpoint.id is not None
        assert checkpoint.building_id == emergency_building.id
        assert checkpoint.floor_plan_id == emergency_floor_plan.id
        assert checkpoint.name == "Complete Checkpoint"
        assert checkpoint.checkpoint_type == CheckpointType.COMMAND_POST
        assert checkpoint.position_x == 50.0
        assert checkpoint.position_y == 50.0
        assert checkpoint.capacity == 25
        assert len(checkpoint.equipment) == 2
        assert checkpoint.responsible_person == "Captain Jane Doe"
        assert checkpoint.contact_info["radio_channel"] == "Command"
        assert checkpoint.instructions is not None

    @pytest.mark.asyncio
    async def test_checkpoint_equipment_json_field(
        self, db_session: AsyncSession, emergency_building: Building
    ):
        """Test that equipment JSON field serializes correctly."""
        equipment = [
            {"name": "Defibrillator", "quantity": 1, "location": "Medical Cabinet"},
            {"name": "Oxygen Tank", "quantity": 2, "location": "Emergency Kit"},
        ]
        checkpoint = EmergencyCheckpoint(
            building_id=emergency_building.id,
            name="Equipment Test",
            checkpoint_type=CheckpointType.FIRST_AID,
            position_x=30.0,
            position_y=40.0,
            equipment=equipment,
        )
        db_session.add(checkpoint)
        await db_session.commit()
        await db_session.refresh(checkpoint)

        assert checkpoint.equipment == equipment
        assert checkpoint.equipment[0]["name"] == "Defibrillator"

    @pytest.mark.asyncio
    async def test_checkpoint_contact_info_json_field(
        self, db_session: AsyncSession, emergency_building: Building
    ):
        """Test that contact_info JSON field serializes correctly."""
        contact_info = {"phone": "555-0000", "email": "test@example.com", "radio_channel": "Channel 1"}
        checkpoint = EmergencyCheckpoint(
            building_id=emergency_building.id,
            name="Contact Info Test",
            checkpoint_type=CheckpointType.TRIAGE_AREA,
            position_x=60.0,
            position_y=70.0,
            contact_info=contact_info,
        )
        db_session.add(checkpoint)
        await db_session.commit()
        await db_session.refresh(checkpoint)

        assert checkpoint.contact_info == contact_info
        assert checkpoint.contact_info["radio_channel"] == "Channel 1"

    @pytest.mark.asyncio
    async def test_checkpoint_is_active_default(
        self, db_session: AsyncSession, emergency_building: Building
    ):
        """Test that is_active defaults to True."""
        checkpoint = EmergencyCheckpoint(
            building_id=emergency_building.id,
            name="Default Active Checkpoint",
            checkpoint_type=CheckpointType.STAGING_AREA,
            position_x=10.0,
            position_y=10.0,
        )
        db_session.add(checkpoint)
        await db_session.commit()
        await db_session.refresh(checkpoint)

        assert checkpoint.is_active is True

    @pytest.mark.asyncio
    async def test_checkpoint_timestamp_auto_generation(
        self, db_session: AsyncSession, emergency_building: Building
    ):
        """Test that created_at and updated_at are auto-generated."""
        checkpoint = EmergencyCheckpoint(
            building_id=emergency_building.id,
            name="Timestamp Checkpoint",
            checkpoint_type=CheckpointType.MEDIA_POINT,
            position_x=80.0,
            position_y=20.0,
        )
        db_session.add(checkpoint)
        await db_session.commit()
        await db_session.refresh(checkpoint)

        assert checkpoint.created_at is not None
        assert checkpoint.updated_at is not None


# ==================== API Tests ====================


class TestEmergencyPlanningAPI:
    """Tests for emergency planning API endpoints."""

    async def get_admin_token(self, client: AsyncClient) -> str:
        """Helper to get admin auth token for API requests."""
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "AdminPassword123!",
            },
        )
        return login_response.json()["access_token"]

    async def create_test_building(self, client: AsyncClient, token: str) -> str:
        """Helper to create a test building and return its ID."""
        response = await client.post(
            "/api/v1/buildings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Emergency API Test Building",
                "street_name": "API Test Street",
                "city": "Montreal",
                "province_state": "Quebec",
                "latitude": 45.5017,
                "longitude": -73.5673,
                "total_floors": 3,
            },
        )
        return response.json()["id"]

    async def create_test_floor_plan(self, client: AsyncClient, token: str, building_id: str) -> str:
        """Helper to create a test floor plan and return its ID."""
        response = await client.post(
            f"/api/v1/buildings/{building_id}/floors",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "floor_number": 1,
                "floor_name": "Ground Floor",
            },
        )
        return response.json()["id"]

    # ==================== Procedure API Tests ====================

    @pytest.mark.asyncio
    async def test_list_procedures_for_building(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test listing procedures for a building."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create some procedures
        for i in range(3):
            await client.post(
                f"/api/v1/emergency-planning/buildings/{building_id}/procedures",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "name": f"Procedure {i}",
                    "procedure_type": "fire",
                    "priority": i + 1,
                },
            )

        response = await client.get(
            f"/api/v1/emergency-planning/buildings/{building_id}/procedures",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 3

    @pytest.mark.asyncio
    async def test_list_procedures_filtered_by_type(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test listing procedures filtered by type."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create procedures of different types
        await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/procedures",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Fire Proc", "procedure_type": "fire"},
        )
        await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/procedures",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Medical Proc", "procedure_type": "medical"},
        )

        response = await client.get(
            f"/api/v1/emergency-planning/buildings/{building_id}/procedures?procedure_type=fire",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["procedure_type"] == "fire"

    @pytest.mark.asyncio
    async def test_list_procedures_filtered_by_is_active(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test listing procedures filtered by is_active."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create active and inactive procedures
        await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/procedures",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Active Proc", "procedure_type": "fire", "is_active": True},
        )
        await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/procedures",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Inactive Proc", "procedure_type": "fire", "is_active": False},
        )

        response = await client.get(
            f"/api/v1/emergency-planning/buildings/{building_id}/procedures?is_active=true",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_single_procedure(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test getting a single procedure."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create a procedure
        create_response = await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/procedures",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Get Test Procedure",
                "procedure_type": "evacuation",
                "description": "Test description",
            },
        )
        procedure_id = create_response.json()["id"]

        response = await client.get(
            f"/api/v1/emergency-planning/procedures/{procedure_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == procedure_id
        assert data["name"] == "Get Test Procedure"
        assert data["description"] == "Test description"

    @pytest.mark.asyncio
    async def test_get_procedure_not_found(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test getting a non-existent procedure returns 404."""
        token = await self.get_admin_token(client)
        fake_id = str(uuid.uuid4())

        response = await client.get(
            f"/api/v1/emergency-planning/procedures/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_procedure_with_valid_data(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test creating a procedure with valid data."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/procedures",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Complete Procedure",
                "description": "Full procedure with all fields",
                "procedure_type": "hazmat",
                "priority": 1,
                "steps": [
                    {"order": 1, "title": "Step 1", "description": "First step"},
                    {"order": 2, "title": "Step 2", "description": "Second step"},
                ],
                "contacts": [
                    {"name": "Contact 1", "role": "Lead", "phone": "555-0001"},
                ],
                "equipment_needed": ["item1", "item2"],
                "estimated_duration_minutes": 30,
                "is_active": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Complete Procedure"
        assert data["procedure_type"] == "hazmat"
        assert data["priority"] == 1
        assert len(data["steps"]) == 2
        assert len(data["contacts"]) == 1
        assert len(data["equipment_needed"]) == 2

    @pytest.mark.asyncio
    async def test_create_procedure_with_invalid_type(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test creating a procedure with invalid type returns 400."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/procedures",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Invalid Type Procedure",
                "procedure_type": "invalid_type",
            },
        )

        assert response.status_code == 400
        assert "Invalid procedure_type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_procedure(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test updating a procedure."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create a procedure
        create_response = await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/procedures",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Original Name", "procedure_type": "fire"},
        )
        procedure_id = create_response.json()["id"]

        # Update it
        response = await client.patch(
            f"/api/v1/emergency-planning/procedures/{procedure_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Updated Name",
                "description": "Updated description",
                "priority": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
        assert data["priority"] == 2

    @pytest.mark.asyncio
    async def test_delete_procedure(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test deleting (soft delete) a procedure."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create a procedure
        create_response = await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/procedures",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "To Delete", "procedure_type": "fire"},
        )
        procedure_id = create_response.json()["id"]

        # Delete it
        response = await client.delete(
            f"/api/v1/emergency-planning/procedures/{procedure_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 204

        # Verify it's soft deleted (not found)
        get_response = await client.get(
            f"/api/v1/emergency-planning/procedures/{procedure_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.status_code == 404

    # ==================== Route API Tests ====================

    @pytest.mark.asyncio
    async def test_list_routes_for_building(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test listing routes for a building."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create some routes
        for i in range(3):
            await client.post(
                f"/api/v1/emergency-planning/buildings/{building_id}/routes",
                headers={"Authorization": f"Bearer {token}"},
                json={"name": f"Route {i}", "route_type": "primary"},
            )

        response = await client.get(
            f"/api/v1/emergency-planning/buildings/{building_id}/routes",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 3

    @pytest.mark.asyncio
    async def test_list_routes_filtered_by_floor_plan(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test listing routes filtered by floor_plan_id."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)
        floor_plan_id = await self.create_test_floor_plan(client, token, building_id)

        # Create routes with and without floor plan
        await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/routes",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Floor Route", "route_type": "primary", "floor_plan_id": floor_plan_id},
        )
        await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/routes",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "No Floor Route", "route_type": "primary"},
        )

        response = await client.get(
            f"/api/v1/emergency-planning/buildings/{building_id}/routes?floor_plan_id={floor_plan_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["floor_plan_id"] == floor_plan_id

    @pytest.mark.asyncio
    async def test_list_routes_filtered_by_route_type(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test listing routes filtered by route_type."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create routes of different types
        await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/routes",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Primary Route", "route_type": "primary"},
        )
        await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/routes",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Secondary Route", "route_type": "secondary"},
        )

        response = await client.get(
            f"/api/v1/emergency-planning/buildings/{building_id}/routes?route_type=primary",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["route_type"] == "primary"

    @pytest.mark.asyncio
    async def test_create_route_with_waypoints(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test creating a route with waypoints."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        waypoints = [
            {"order": 1, "x": 10.0, "y": 20.0, "label": "Start"},
            {"order": 2, "x": 50.0, "y": 50.0, "label": "Middle"},
            {"order": 3, "x": 90.0, "y": 80.0, "label": "End"},
        ]

        response = await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/routes",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Waypoint Route",
                "route_type": "primary",
                "waypoints": waypoints,
                "color": "#00ff00",
                "line_width": 4,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Waypoint Route"
        assert len(data["waypoints"]) == 3
        assert data["waypoints"][0]["label"] == "Start"
        assert data["color"] == "#00ff00"
        assert data["line_width"] == 4

    @pytest.mark.asyncio
    async def test_update_route_waypoints(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test updating route waypoints."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create a route
        create_response = await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/routes",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Update Waypoints Route",
                "route_type": "primary",
                "waypoints": [{"order": 1, "x": 10.0, "y": 10.0}],
            },
        )
        route_id = create_response.json()["id"]

        # Update waypoints
        new_waypoints = [
            {"order": 1, "x": 5.0, "y": 5.0, "label": "New Start"},
            {"order": 2, "x": 95.0, "y": 95.0, "label": "New End"},
        ]

        response = await client.patch(
            f"/api/v1/emergency-planning/routes/{route_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"waypoints": new_waypoints},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["waypoints"]) == 2
        assert data["waypoints"][0]["label"] == "New Start"

    @pytest.mark.asyncio
    async def test_delete_route(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test deleting (soft delete via is_active=False) a route."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create a route
        create_response = await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/routes",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "To Delete Route", "route_type": "primary"},
        )
        route_id = create_response.json()["id"]

        # Delete it
        response = await client.delete(
            f"/api/v1/emergency-planning/routes/{route_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 204

        # Verify it's deactivated
        get_response = await client.get(
            f"/api/v1/emergency-planning/routes/{route_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.json()["is_active"] is False

    # ==================== Checkpoint API Tests ====================

    @pytest.mark.asyncio
    async def test_list_checkpoints_for_building(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test listing checkpoints for a building."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create some checkpoints
        for i in range(3):
            await client.post(
                f"/api/v1/emergency-planning/buildings/{building_id}/checkpoints",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "name": f"Checkpoint {i}",
                    "checkpoint_type": "assembly_point",
                    "position_x": float(i * 10),
                    "position_y": float(i * 10),
                },
            )

        response = await client.get(
            f"/api/v1/emergency-planning/buildings/{building_id}/checkpoints",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 3

    @pytest.mark.asyncio
    async def test_list_checkpoints_filtered_by_type(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test listing checkpoints filtered by type."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create checkpoints of different types
        await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/checkpoints",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Assembly", "checkpoint_type": "assembly_point", "position_x": 10.0, "position_y": 10.0},
        )
        await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/checkpoints",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "First Aid", "checkpoint_type": "first_aid", "position_x": 20.0, "position_y": 20.0},
        )

        response = await client.get(
            f"/api/v1/emergency-planning/buildings/{building_id}/checkpoints?checkpoint_type=assembly_point",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["checkpoint_type"] == "assembly_point"

    @pytest.mark.asyncio
    async def test_create_checkpoint_with_equipment(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test creating a checkpoint with equipment."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        equipment = [
            {"name": "First Aid Kit", "quantity": 2, "location": "Cabinet"},
            {"name": "AED", "quantity": 1, "location": "Wall Mount"},
        ]

        response = await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/checkpoints",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "First Aid Station",
                "checkpoint_type": "first_aid",
                "position_x": 45.0,
                "position_y": 55.0,
                "equipment": equipment,
                "contact_info": {"phone": "555-0911", "radio_channel": "Medical"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "First Aid Station"
        assert len(data["equipment"]) == 2
        assert data["equipment"][0]["name"] == "First Aid Kit"
        assert data["contact_info"]["radio_channel"] == "Medical"

    @pytest.mark.asyncio
    async def test_update_checkpoint_position(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test updating checkpoint position."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create a checkpoint
        create_response = await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/checkpoints",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Movable Checkpoint",
                "checkpoint_type": "staging_area",
                "position_x": 10.0,
                "position_y": 10.0,
            },
        )
        checkpoint_id = create_response.json()["id"]

        # Update position
        response = await client.patch(
            f"/api/v1/emergency-planning/checkpoints/{checkpoint_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"position_x": 80.0, "position_y": 90.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["position_x"] == 80.0
        assert data["position_y"] == 90.0

    @pytest.mark.asyncio
    async def test_delete_checkpoint(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test deleting (soft delete via is_active=False) a checkpoint."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create a checkpoint
        create_response = await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/checkpoints",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "To Delete Checkpoint",
                "checkpoint_type": "media_point",
                "position_x": 50.0,
                "position_y": 50.0,
            },
        )
        checkpoint_id = create_response.json()["id"]

        # Delete it
        response = await client.delete(
            f"/api/v1/emergency-planning/checkpoints/{checkpoint_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 204

        # Verify it's deactivated
        get_response = await client.get(
            f"/api/v1/emergency-planning/checkpoints/{checkpoint_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.json()["is_active"] is False

    # ==================== Combined Emergency Plan API Tests ====================

    @pytest.mark.asyncio
    async def test_get_full_emergency_plan(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test getting the full emergency plan for a building."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create procedures, routes, and checkpoints
        await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/procedures",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Plan Procedure", "procedure_type": "fire"},
        )
        await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/routes",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Plan Route", "route_type": "primary"},
        )
        await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/checkpoints",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Plan Checkpoint", "checkpoint_type": "assembly_point", "position_x": 50.0, "position_y": 50.0},
        )

        response = await client.get(
            f"/api/v1/emergency-planning/buildings/{building_id}/emergency-plan",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "building_id" in data
        assert "building_name" in data
        assert "procedures" in data
        assert "routes" in data
        assert "checkpoints" in data
        assert "total_procedures" in data
        assert "total_routes" in data
        assert "total_checkpoints" in data
        assert data["total_procedures"] >= 1
        assert data["total_routes"] >= 1
        assert data["total_checkpoints"] >= 1

    @pytest.mark.asyncio
    async def test_export_emergency_plan(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test exporting the emergency plan."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create some emergency data
        await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/procedures",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Export Procedure", "procedure_type": "evacuation"},
        )

        response = await client.get(
            f"/api/v1/emergency-planning/buildings/{building_id}/emergency-plan/export",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "building_id" in data
        assert "building_name" in data
        assert "building_address" in data
        assert "exported_at" in data
        assert "exported_by" in data
        assert "procedures" in data
        assert "routes" in data
        assert "checkpoints" in data
        assert "metadata" in data
        assert data["metadata"]["version"] == "1.0"

    @pytest.mark.asyncio
    async def test_export_emergency_plan_include_inactive(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test exporting the emergency plan with inactive items."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        # Create active and inactive procedures
        await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/procedures",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Active Procedure", "procedure_type": "fire", "is_active": True},
        )
        await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/procedures",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Inactive Procedure", "procedure_type": "fire", "is_active": False},
        )

        # Export without inactive
        response_active_only = await client.get(
            f"/api/v1/emergency-planning/buildings/{building_id}/emergency-plan/export",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response_active_only.status_code == 200
        active_count = len(response_active_only.json()["procedures"])

        # Export with inactive
        response_all = await client.get(
            f"/api/v1/emergency-planning/buildings/{building_id}/emergency-plan/export?include_inactive=true",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response_all.status_code == 200
        all_count = len(response_all.json()["procedures"])

        assert all_count >= active_count

    # ==================== Error Cases ====================

    @pytest.mark.asyncio
    async def test_procedure_unauthorized(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test procedure endpoints require authentication."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.get(
            f"/api/v1/emergency-planning/buildings/{building_id}/procedures",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_route_building_not_found(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test route endpoints return 404 for non-existent building."""
        token = await self.get_admin_token(client)
        fake_id = str(uuid.uuid4())

        response = await client.get(
            f"/api/v1/emergency-planning/buildings/{fake_id}/routes",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_checkpoint_invalid_building_id_format(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test checkpoint endpoints return 400 for invalid building ID format."""
        token = await self.get_admin_token(client)

        response = await client.get(
            "/api/v1/emergency-planning/buildings/not-a-uuid/checkpoints",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_route_not_found(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test getting a non-existent route returns 404."""
        token = await self.get_admin_token(client)
        fake_id = str(uuid.uuid4())

        response = await client.get(
            f"/api/v1/emergency-planning/routes/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_checkpoint_not_found(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test getting a non-existent checkpoint returns 404."""
        token = await self.get_admin_token(client)
        fake_id = str(uuid.uuid4())

        response = await client.get(
            f"/api/v1/emergency-planning/checkpoints/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_checkpoint_invalid_type(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test creating a checkpoint with invalid type returns 400."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/checkpoints",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Invalid Type Checkpoint",
                "checkpoint_type": "invalid_type",
                "position_x": 50.0,
                "position_y": 50.0,
            },
        )

        assert response.status_code == 400
        assert "Invalid checkpoint_type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_route_invalid_route_type(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test creating a route with invalid route type returns 400."""
        token = await self.get_admin_token(client)
        building_id = await self.create_test_building(client, token)

        response = await client.post(
            f"/api/v1/emergency-planning/buildings/{building_id}/routes",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Invalid Type Route",
                "route_type": "not_a_valid_type",
            },
        )

        assert response.status_code == 400
        assert "Invalid route_type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_emergency_plan_not_found(self, client: AsyncClient, admin_user: User, test_agency: Agency):
        """Test getting emergency plan for non-existent building returns 404."""
        token = await self.get_admin_token(client)
        fake_id = str(uuid.uuid4())

        response = await client.get(
            f"/api/v1/emergency-planning/buildings/{fake_id}/emergency-plan",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
