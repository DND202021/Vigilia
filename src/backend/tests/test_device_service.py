"""Tests for device service."""

import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.device_service import DeviceService, DeviceError
from app.models.device import IoTDevice, DeviceType, DeviceStatus
from app.models.building import Building, BuildingType, FloorPlan
from app.models.agency import Agency


@pytest.fixture
async def test_building(db_session: AsyncSession, test_agency: Agency) -> Building:
    """Create a test building for device tests."""
    building = Building(
        id=uuid.uuid4(),
        agency_id=test_agency.id,
        name="Test Building",
        street_name="Test Street",
        city="Montreal",
        province_state="Quebec",
        latitude=45.5017,
        longitude=-73.5673,
        building_type=BuildingType.COMMERCIAL,
        full_address="100 Test Street, Montreal, Quebec",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def test_floor_plan(db_session: AsyncSession, test_building: Building) -> FloorPlan:
    """Create a test floor plan for device tests."""
    floor_plan = FloorPlan(
        id=uuid.uuid4(),
        building_id=test_building.id,
        floor_number=1,
        floor_name="Ground Floor",
    )
    db_session.add(floor_plan)
    await db_session.commit()
    await db_session.refresh(floor_plan)
    return floor_plan


@pytest.fixture
async def second_building(db_session: AsyncSession, test_agency: Agency) -> Building:
    """Create a second test building for filtering tests."""
    building = Building(
        id=uuid.uuid4(),
        agency_id=test_agency.id,
        name="Second Building",
        street_name="Other Street",
        city="Laval",
        province_state="Quebec",
        latitude=45.5680,
        longitude=-73.7490,
        building_type=BuildingType.RESIDENTIAL_MULTI,
        full_address="200 Other Street, Laval, Quebec",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def second_floor_plan(db_session: AsyncSession, test_building: Building) -> FloorPlan:
    """Create a second test floor plan for filtering tests."""
    floor_plan = FloorPlan(
        id=uuid.uuid4(),
        building_id=test_building.id,
        floor_number=2,
        floor_name="Second Floor",
    )
    db_session.add(floor_plan)
    await db_session.commit()
    await db_session.refresh(floor_plan)
    return floor_plan


class TestDeviceService:
    """Tests for DeviceService."""

    # ==================== Device CRUD Tests ====================

    @pytest.mark.asyncio
    async def test_create_device(
        self, db_session: AsyncSession, test_building: Building, test_floor_plan: FloorPlan
    ):
        """Device creation should work with all fields."""
        service = DeviceService(db_session)

        device = await service.create_device(
            name="Camera 1",
            device_type=DeviceType.CAMERA,
            building_id=test_building.id,
            serial_number="CAM-001",
            ip_address="192.168.1.100",
            mac_address="00:11:22:33:44:55",
            model="AXIS P3245-V",
            firmware_version="10.12.114",
            manufacturer="Axis",
            floor_plan_id=test_floor_plan.id,
            position_x=50.0,
            position_y=75.0,
            latitude=45.5017,
            longitude=-73.5673,
            location_name="Main Entrance",
            config={"sensitivity": 0.8, "detection_mode": "motion"},
            capabilities=["motion_detection", "audio_analytics"],
        )

        assert device.id is not None
        assert device.name == "Camera 1"
        assert device.device_type == DeviceType.CAMERA.value
        assert device.building_id == test_building.id
        assert device.serial_number == "CAM-001"
        assert device.ip_address == "192.168.1.100"
        assert device.mac_address == "00:11:22:33:44:55"
        assert device.model == "AXIS P3245-V"
        assert device.firmware_version == "10.12.114"
        assert device.manufacturer == "Axis"
        assert device.floor_plan_id == test_floor_plan.id
        assert device.position_x == 50.0
        assert device.position_y == 75.0
        assert device.latitude == 45.5017
        assert device.longitude == -73.5673
        assert device.location_name == "Main Entrance"
        assert device.config == {"sensitivity": 0.8, "detection_mode": "motion"}
        assert device.capabilities == ["motion_detection", "audio_analytics"]
        assert device.status == DeviceStatus.OFFLINE.value

    @pytest.mark.asyncio
    async def test_create_device_minimal(self, db_session: AsyncSession, test_building: Building):
        """Device creation should work with only required fields."""
        service = DeviceService(db_session)

        device = await service.create_device(
            name="Basic Sensor",
            device_type=DeviceType.SENSOR,
            building_id=test_building.id,
        )

        assert device.id is not None
        assert device.name == "Basic Sensor"
        assert device.device_type == DeviceType.SENSOR.value
        assert device.building_id == test_building.id
        assert device.serial_number is None
        assert device.ip_address is None
        assert device.mac_address is None
        assert device.model is None
        assert device.firmware_version is None
        assert device.manufacturer == "Axis"
        assert device.floor_plan_id is None
        assert device.position_x is None
        assert device.position_y is None
        assert device.config == {}
        assert device.capabilities == []
        assert device.status == DeviceStatus.OFFLINE.value

    @pytest.mark.asyncio
    async def test_create_device_requires_both_coordinates(
        self,
        db_session: AsyncSession,
        test_building: Building,
        test_floor_plan: FloorPlan,
    ):
        """Device creation with floor_plan_id requires both position coordinates."""
        service = DeviceService(db_session)

        # Should fail with only position_x
        with pytest.raises(DeviceError) as exc_info:
            await service.create_device(
                name="Incomplete Device",
                device_type=DeviceType.SENSOR,
                building_id=test_building.id,
                floor_plan_id=test_floor_plan.id,
                position_x=50.0,
            )
        assert "Both position_x and position_y are required" in str(exc_info.value)

        # Should fail with only position_y
        with pytest.raises(DeviceError) as exc_info:
            await service.create_device(
                name="Incomplete Device",
                device_type=DeviceType.SENSOR,
                building_id=test_building.id,
                floor_plan_id=test_floor_plan.id,
                position_y=50.0,
            )
        assert "Both position_x and position_y are required" in str(exc_info.value)

        # Should fail with neither coordinate
        with pytest.raises(DeviceError) as exc_info:
            await service.create_device(
                name="Incomplete Device",
                device_type=DeviceType.SENSOR,
                building_id=test_building.id,
                floor_plan_id=test_floor_plan.id,
            )
        assert "Both position_x and position_y are required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_device(self, db_session: AsyncSession, test_building: Building):
        """Getting a device by ID should work."""
        service = DeviceService(db_session)

        created = await service.create_device(
            name="Test Device",
            device_type=DeviceType.MICROPHONE,
            building_id=test_building.id,
        )

        retrieved = await service.get_device(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Test Device"

    @pytest.mark.asyncio
    async def test_get_device_not_found(self, db_session: AsyncSession):
        """Getting a non-existent device should return None."""
        service = DeviceService(db_session)

        result = await service.get_device(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_devices(self, db_session: AsyncSession, test_building: Building):
        """Listing devices should return all devices."""
        service = DeviceService(db_session)

        await service.create_device(
            name="Device 1",
            device_type=DeviceType.CAMERA,
            building_id=test_building.id,
        )
        await service.create_device(
            name="Device 2",
            device_type=DeviceType.MICROPHONE,
            building_id=test_building.id,
        )

        devices, total = await service.list_devices()
        assert len(devices) == 2
        assert total == 2

    @pytest.mark.asyncio
    async def test_list_devices_by_building(
        self, db_session: AsyncSession, test_building: Building, second_building: Building
    ):
        """Listing devices filtered by building_id should work."""
        service = DeviceService(db_session)

        await service.create_device(
            name="Building 1 Device",
            device_type=DeviceType.CAMERA,
            building_id=test_building.id,
        )
        await service.create_device(
            name="Building 2 Device",
            device_type=DeviceType.CAMERA,
            building_id=second_building.id,
        )

        devices, total = await service.list_devices(building_id=test_building.id)
        assert len(devices) == 1
        assert total == 1
        assert devices[0].name == "Building 1 Device"

    @pytest.mark.asyncio
    async def test_list_devices_by_floor_plan(
        self,
        db_session: AsyncSession,
        test_building: Building,
        test_floor_plan: FloorPlan,
        second_floor_plan: FloorPlan,
    ):
        """Listing devices filtered by floor_plan_id should work."""
        service = DeviceService(db_session)

        await service.create_device(
            name="Floor 1 Device",
            device_type=DeviceType.SENSOR,
            building_id=test_building.id,
            floor_plan_id=test_floor_plan.id,
            position_x=10.0,
            position_y=20.0,
        )
        await service.create_device(
            name="Floor 2 Device",
            device_type=DeviceType.SENSOR,
            building_id=test_building.id,
            floor_plan_id=second_floor_plan.id,
            position_x=30.0,
            position_y=40.0,
        )

        devices, total = await service.list_devices(floor_plan_id=test_floor_plan.id)
        assert len(devices) == 1
        assert total == 1
        assert devices[0].name == "Floor 1 Device"

    @pytest.mark.asyncio
    async def test_list_devices_by_type(self, db_session: AsyncSession, test_building: Building):
        """Listing devices filtered by device_type should work."""
        service = DeviceService(db_session)

        await service.create_device(
            name="Camera Device",
            device_type=DeviceType.CAMERA,
            building_id=test_building.id,
        )
        await service.create_device(
            name="Microphone Device",
            device_type=DeviceType.MICROPHONE,
            building_id=test_building.id,
        )
        await service.create_device(
            name="Sensor Device",
            device_type=DeviceType.SENSOR,
            building_id=test_building.id,
        )

        devices, total = await service.list_devices(device_type=DeviceType.CAMERA)
        assert len(devices) == 1
        assert total == 1
        assert devices[0].name == "Camera Device"

    @pytest.mark.asyncio
    async def test_list_devices_by_status(self, db_session: AsyncSession, test_building: Building):
        """Listing devices filtered by status should work."""
        service = DeviceService(db_session)

        device1 = await service.create_device(
            name="Online Device",
            device_type=DeviceType.CAMERA,
            building_id=test_building.id,
        )
        await service.create_device(
            name="Offline Device",
            device_type=DeviceType.CAMERA,
            building_id=test_building.id,
        )

        # Update first device to online
        await service.update_status(device1.id, DeviceStatus.ONLINE)

        devices, total = await service.list_devices(status=DeviceStatus.ONLINE)
        assert len(devices) == 1
        assert total == 1
        assert devices[0].name == "Online Device"

    @pytest.mark.asyncio
    async def test_list_devices_pagination(self, db_session: AsyncSession, test_building: Building):
        """Listing devices with pagination should work."""
        service = DeviceService(db_session)

        # Create 5 devices
        for i in range(5):
            await service.create_device(
                name=f"Device {i:02d}",
                device_type=DeviceType.SENSOR,
                building_id=test_building.id,
            )

        # Get first page
        devices, total = await service.list_devices(limit=2, offset=0)
        assert len(devices) == 2
        assert total == 5

        # Get second page
        devices, total = await service.list_devices(limit=2, offset=2)
        assert len(devices) == 2
        assert total == 5

        # Get last page
        devices, total = await service.list_devices(limit=2, offset=4)
        assert len(devices) == 1
        assert total == 5

    @pytest.mark.asyncio
    async def test_update_device(self, db_session: AsyncSession, test_building: Building):
        """Updating a device should work."""
        service = DeviceService(db_session)

        device = await service.create_device(
            name="Original Name",
            device_type=DeviceType.CAMERA,
            building_id=test_building.id,
            model="Old Model",
        )

        updated = await service.update_device(
            device.id,
            name="Updated Name",
            model="New Model",
            ip_address="192.168.1.200",
        )

        assert updated.name == "Updated Name"
        assert updated.model == "New Model"
        assert updated.ip_address == "192.168.1.200"

    @pytest.mark.asyncio
    async def test_update_device_not_found(self, db_session: AsyncSession):
        """Updating a non-existent device should raise DeviceError."""
        service = DeviceService(db_session)

        with pytest.raises(DeviceError) as exc_info:
            await service.update_device(uuid.uuid4(), name="New Name")

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_position(
        self, db_session: AsyncSession, test_building: Building, test_floor_plan: FloorPlan
    ):
        """Updating device position should work."""
        service = DeviceService(db_session)

        device = await service.create_device(
            name="Position Test Device",
            device_type=DeviceType.CAMERA,
            building_id=test_building.id,
        )

        assert device.floor_plan_id is None
        assert device.position_x is None
        assert device.position_y is None

        updated = await service.update_position(
            device.id,
            floor_plan_id=test_floor_plan.id,
            position_x=25.5,
            position_y=75.5,
        )

        assert updated.floor_plan_id == test_floor_plan.id
        assert updated.position_x == 25.5
        assert updated.position_y == 75.5

    @pytest.mark.asyncio
    async def test_update_status(self, db_session: AsyncSession, test_building: Building):
        """Updating device status should update status and last_seen."""
        service = DeviceService(db_session)

        device = await service.create_device(
            name="Status Test Device",
            device_type=DeviceType.SENSOR,
            building_id=test_building.id,
        )

        assert device.status == DeviceStatus.OFFLINE.value
        assert device.last_seen is None

        updated = await service.update_status(
            device.id,
            status=DeviceStatus.ONLINE,
            connection_quality=95,
        )

        assert updated.status == DeviceStatus.ONLINE.value
        assert updated.last_seen is not None
        assert updated.connection_quality == 95

    @pytest.mark.asyncio
    async def test_update_config(self, db_session: AsyncSession, test_building: Building):
        """Updating device config should work."""
        service = DeviceService(db_session)

        device = await service.create_device(
            name="Config Test Device",
            device_type=DeviceType.MICROPHONE,
            building_id=test_building.id,
            config={"old_setting": True},
        )

        new_config = {
            "sensitivity": 0.9,
            "detection_types": ["gunshot", "glass_break", "scream"],
            "threshold": 75,
        }

        updated = await service.update_config(device.id, config=new_config)

        assert updated.config == new_config

    @pytest.mark.asyncio
    async def test_delete_device(self, db_session: AsyncSession, test_building: Building):
        """Soft deleting a device should work."""
        service = DeviceService(db_session)

        device = await service.create_device(
            name="To Delete",
            device_type=DeviceType.GATEWAY,
            building_id=test_building.id,
        )

        await service.delete_device(device.id)

        # Should not be found after deletion
        result = await service.get_device(device.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_device_not_found(self, db_session: AsyncSession):
        """Deleting a non-existent device should raise DeviceError."""
        service = DeviceService(db_session)

        with pytest.raises(DeviceError) as exc_info:
            await service.delete_device(uuid.uuid4())

        assert "not found" in str(exc_info.value)

    # ==================== Device Lookup Tests ====================

    @pytest.mark.asyncio
    async def test_get_device_by_serial(self, db_session: AsyncSession, test_building: Building):
        """Finding device by serial number should work."""
        service = DeviceService(db_session)

        await service.create_device(
            name="Serialized Device",
            device_type=DeviceType.CAMERA,
            building_id=test_building.id,
            serial_number="UNIQUE-SERIAL-123",
        )

        found = await service.get_device_by_serial("UNIQUE-SERIAL-123")
        assert found is not None
        assert found.name == "Serialized Device"
        assert found.serial_number == "UNIQUE-SERIAL-123"

        # Non-existent serial should return None
        not_found = await service.get_device_by_serial("NONEXISTENT")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_get_devices_by_building(
        self, db_session: AsyncSession, test_building: Building, second_building: Building
    ):
        """Getting all devices in a building should work."""
        service = DeviceService(db_session)

        await service.create_device(
            name="Building A - Camera",
            device_type=DeviceType.CAMERA,
            building_id=test_building.id,
        )
        await service.create_device(
            name="Building A - Mic",
            device_type=DeviceType.MICROPHONE,
            building_id=test_building.id,
        )
        await service.create_device(
            name="Building B - Sensor",
            device_type=DeviceType.SENSOR,
            building_id=second_building.id,
        )

        building_a_devices = await service.get_devices_by_building(test_building.id)
        assert len(building_a_devices) == 2
        # Should be ordered by name
        assert building_a_devices[0].name == "Building A - Camera"
        assert building_a_devices[1].name == "Building A - Mic"

        building_b_devices = await service.get_devices_by_building(second_building.id)
        assert len(building_b_devices) == 1
        assert building_b_devices[0].name == "Building B - Sensor"

    @pytest.mark.asyncio
    async def test_get_devices_by_floor(
        self,
        db_session: AsyncSession,
        test_building: Building,
        test_floor_plan: FloorPlan,
        second_floor_plan: FloorPlan,
    ):
        """Getting all devices on a floor should work."""
        service = DeviceService(db_session)

        await service.create_device(
            name="Floor 1 - Camera",
            device_type=DeviceType.CAMERA,
            building_id=test_building.id,
            floor_plan_id=test_floor_plan.id,
            position_x=10.0,
            position_y=20.0,
        )
        await service.create_device(
            name="Floor 1 - Sensor",
            device_type=DeviceType.SENSOR,
            building_id=test_building.id,
            floor_plan_id=test_floor_plan.id,
            position_x=30.0,
            position_y=40.0,
        )
        await service.create_device(
            name="Floor 2 - Mic",
            device_type=DeviceType.MICROPHONE,
            building_id=test_building.id,
            floor_plan_id=second_floor_plan.id,
            position_x=50.0,
            position_y=60.0,
        )
        await service.create_device(
            name="Unplaced Device",
            device_type=DeviceType.GATEWAY,
            building_id=test_building.id,
        )

        floor_1_devices = await service.get_devices_by_floor(test_floor_plan.id)
        assert len(floor_1_devices) == 2
        # Should be ordered by name
        assert floor_1_devices[0].name == "Floor 1 - Camera"
        assert floor_1_devices[1].name == "Floor 1 - Sensor"

        floor_2_devices = await service.get_devices_by_floor(second_floor_plan.id)
        assert len(floor_2_devices) == 1
        assert floor_2_devices[0].name == "Floor 2 - Mic"
