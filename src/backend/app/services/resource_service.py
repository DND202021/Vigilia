"""Resource Service for personnel, vehicles, and equipment management."""

from datetime import datetime, timezone
from typing import Any
import uuid
import math

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resource import (
    Resource, ResourceType, ResourceStatus,
    Personnel, Vehicle, Equipment,
)
from app.models.agency import Agency


class ResourceError(Exception):
    """Resource related errors."""
    pass


class ResourceService:
    """Service for resource management operations."""

    def __init__(self, db: AsyncSession):
        """Initialize resource service with database session."""
        self.db = db

    # ==================== Personnel Management ====================

    async def create_personnel(
        self,
        agency_id: uuid.UUID,
        name: str,
        badge_number: str,
        rank: str | None = None,
        call_sign: str | None = None,
        specializations: list[str] | None = None,
        certifications: list[str] | None = None,
        user_id: uuid.UUID | None = None,
    ) -> Personnel:
        """Create a new personnel resource."""
        # Verify agency exists
        agency = await self._get_agency(agency_id)
        if agency is None:
            raise ResourceError(f"Agency {agency_id} not found")

        personnel = Personnel(
            id=uuid.uuid4(),
            resource_type=ResourceType.PERSONNEL,
            agency_id=agency_id,
            name=name,
            call_sign=call_sign,
            status=ResourceStatus.AVAILABLE,
            badge_number=badge_number,
            rank=rank,
            specializations=specializations or [],
            certifications=certifications or [],
            user_id=user_id,
        )

        self.db.add(personnel)
        await self.db.commit()
        await self.db.refresh(personnel)

        return personnel

    async def get_personnel(self, personnel_id: uuid.UUID) -> Personnel | None:
        """Get personnel by ID."""
        result = await self.db.execute(
            select(Personnel).where(Personnel.id == personnel_id)
        )
        return result.scalar_one_or_none()

    async def list_personnel(
        self,
        agency_id: uuid.UUID | None = None,
        status: ResourceStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Personnel]:
        """List personnel with optional filters."""
        query = select(Personnel)

        conditions = []
        if agency_id:
            conditions.append(Personnel.agency_id == agency_id)
        if status:
            conditions.append(Personnel.status == status)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Personnel.name).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ==================== Vehicle Management ====================

    async def create_vehicle(
        self,
        agency_id: uuid.UUID,
        name: str,
        vehicle_type: str,
        call_sign: str | None = None,
        make: str | None = None,
        model: str | None = None,
        year: int | None = None,
        license_plate: str | None = None,
        vin: str | None = None,
    ) -> Vehicle:
        """Create a new vehicle resource."""
        # Verify agency exists
        agency = await self._get_agency(agency_id)
        if agency is None:
            raise ResourceError(f"Agency {agency_id} not found")

        vehicle = Vehicle(
            id=uuid.uuid4(),
            resource_type=ResourceType.VEHICLE,
            agency_id=agency_id,
            name=name,
            call_sign=call_sign,
            status=ResourceStatus.AVAILABLE,
            vehicle_type=vehicle_type,
            make=make,
            model=model,
            year=year,
            license_plate=license_plate,
            vin=vin,
            equipment_inventory=[],
        )

        self.db.add(vehicle)
        await self.db.commit()
        await self.db.refresh(vehicle)

        return vehicle

    async def get_vehicle(self, vehicle_id: uuid.UUID) -> Vehicle | None:
        """Get vehicle by ID."""
        result = await self.db.execute(
            select(Vehicle).where(Vehicle.id == vehicle_id)
        )
        return result.scalar_one_or_none()

    async def list_vehicles(
        self,
        agency_id: uuid.UUID | None = None,
        status: ResourceStatus | None = None,
        vehicle_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Vehicle]:
        """List vehicles with optional filters."""
        query = select(Vehicle)

        conditions = []
        if agency_id:
            conditions.append(Vehicle.agency_id == agency_id)
        if status:
            conditions.append(Vehicle.status == status)
        if vehicle_type:
            conditions.append(Vehicle.vehicle_type == vehicle_type)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Vehicle.name).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ==================== Equipment Management ====================

    async def create_equipment(
        self,
        agency_id: uuid.UUID,
        name: str,
        equipment_type: str,
        serial_number: str | None = None,
        manufacturer: str | None = None,
    ) -> Equipment:
        """Create a new equipment resource."""
        # Verify agency exists
        agency = await self._get_agency(agency_id)
        if agency is None:
            raise ResourceError(f"Agency {agency_id} not found")

        equipment = Equipment(
            id=uuid.uuid4(),
            resource_type=ResourceType.EQUIPMENT,
            agency_id=agency_id,
            name=name,
            status=ResourceStatus.AVAILABLE,
            equipment_type=equipment_type,
            serial_number=serial_number,
            manufacturer=manufacturer,
        )

        self.db.add(equipment)
        await self.db.commit()
        await self.db.refresh(equipment)

        return equipment

    async def get_equipment(self, equipment_id: uuid.UUID) -> Equipment | None:
        """Get equipment by ID."""
        result = await self.db.execute(
            select(Equipment).where(Equipment.id == equipment_id)
        )
        return result.scalar_one_or_none()

    async def list_equipment(
        self,
        agency_id: uuid.UUID | None = None,
        status: ResourceStatus | None = None,
        equipment_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Equipment]:
        """List equipment with optional filters."""
        query = select(Equipment)

        conditions = []
        if agency_id:
            conditions.append(Equipment.agency_id == agency_id)
        if status:
            conditions.append(Equipment.status == status)
        if equipment_type:
            conditions.append(Equipment.equipment_type == equipment_type)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Equipment.name).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ==================== Common Operations ====================

    async def get_resource(self, resource_id: uuid.UUID) -> Resource | None:
        """Get any resource by ID."""
        result = await self.db.execute(
            select(Resource).where(Resource.id == resource_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        resource_id: uuid.UUID,
        status: ResourceStatus,
    ) -> Resource:
        """Update resource status."""
        resource = await self.get_resource(resource_id)
        if resource is None:
            raise ResourceError(f"Resource {resource_id} not found")

        resource.status = status
        await self.db.commit()
        await self.db.refresh(resource)

        return resource

    async def update_location(
        self,
        resource_id: uuid.UUID,
        latitude: float,
        longitude: float,
    ) -> Resource:
        """Update resource location."""
        resource = await self.get_resource(resource_id)
        if resource is None:
            raise ResourceError(f"Resource {resource_id} not found")

        resource.current_latitude = latitude
        resource.current_longitude = longitude
        resource.location_updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(resource)

        return resource

    async def get_available_resources(
        self,
        agency_id: uuid.UUID | None = None,
        resource_type: ResourceType | None = None,
        near_latitude: float | None = None,
        near_longitude: float | None = None,
        radius_km: float = 10.0,
    ) -> dict[str, list[Resource]]:
        """Get available resources, optionally filtered by proximity."""
        query = select(Resource).where(
            Resource.status == ResourceStatus.AVAILABLE
        )

        conditions = []
        if agency_id:
            conditions.append(Resource.agency_id == agency_id)
        if resource_type:
            conditions.append(Resource.resource_type == resource_type)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        resources = list(result.scalars().all())

        # Filter by proximity if coordinates provided
        if near_latitude is not None and near_longitude is not None:
            resources = [
                r for r in resources
                if r.current_latitude is not None and r.current_longitude is not None
                and self._calculate_distance(
                    near_latitude, near_longitude,
                    r.current_latitude, r.current_longitude
                ) <= radius_km
            ]

            # Sort by distance
            resources.sort(key=lambda r: self._calculate_distance(
                near_latitude, near_longitude,
                r.current_latitude, r.current_longitude
            ))

        # Group by type
        grouped: dict[str, list[Resource]] = {
            "personnel": [],
            "vehicles": [],
            "equipment": [],
        }

        for resource in resources:
            if resource.resource_type == ResourceType.PERSONNEL:
                grouped["personnel"].append(resource)
            elif resource.resource_type == ResourceType.VEHICLE:
                grouped["vehicles"].append(resource)
            elif resource.resource_type == ResourceType.EQUIPMENT:
                grouped["equipment"].append(resource)

        return grouped

    async def assign_personnel_to_vehicle(
        self,
        personnel_id: uuid.UUID,
        vehicle_id: uuid.UUID,
    ) -> Personnel:
        """Assign personnel to a vehicle."""
        personnel = await self.get_personnel(personnel_id)
        if personnel is None:
            raise ResourceError(f"Personnel {personnel_id} not found")

        vehicle = await self.get_vehicle(vehicle_id)
        if vehicle is None:
            raise ResourceError(f"Vehicle {vehicle_id} not found")

        personnel.assigned_vehicle_id = vehicle_id
        await self.db.commit()
        await self.db.refresh(personnel)

        return personnel

    async def get_resource_stats(
        self,
        agency_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Get resource statistics."""
        query = select(Resource)
        if agency_id:
            query = query.where(Resource.agency_id == agency_id)

        result = await self.db.execute(query)
        resources = list(result.scalars().all())

        stats = {
            "total": len(resources),
            "by_type": {
                "personnel": 0,
                "vehicles": 0,
                "equipment": 0,
            },
            "by_status": {
                "available": 0,
                "assigned": 0,
                "en_route": 0,
                "on_scene": 0,
                "off_duty": 0,
                "out_of_service": 0,
            },
        }

        for resource in resources:
            # Count by type
            if resource.resource_type == ResourceType.PERSONNEL:
                stats["by_type"]["personnel"] += 1
            elif resource.resource_type == ResourceType.VEHICLE:
                stats["by_type"]["vehicles"] += 1
            elif resource.resource_type == ResourceType.EQUIPMENT:
                stats["by_type"]["equipment"] += 1

            # Count by status
            stats["by_status"][resource.status.value] += 1

        return stats

    async def _get_agency(self, agency_id: uuid.UUID) -> Agency | None:
        """Get agency by ID."""
        result = await self.db.execute(
            select(Agency).where(Agency.id == agency_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula (km)."""
        R = 6371  # Earth's radius in kilometers

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_lat / 2) ** 2 +
            math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c
