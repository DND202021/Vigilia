"""Building Service for emergency response building information management."""

from datetime import datetime, timezone
from typing import Any
import uuid
import math

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.building import (
    Building,
    BuildingType,
    OccupancyType,
    ConstructionType,
    HazardLevel,
    FloorPlan,
)
from app.models.agency import Agency


class BuildingError(Exception):
    """Building related errors."""
    pass


class BuildingService:
    """Service for building information management operations."""

    def __init__(self, db: AsyncSession):
        """Initialize building service with database session."""
        self.db = db

    # ==================== Building CRUD ====================

    async def create_building(
        self,
        agency_id: uuid.UUID,
        name: str,
        street_name: str,
        city: str,
        province_state: str,
        latitude: float,
        longitude: float,
        civic_number: str | None = None,
        street_type: str | None = None,
        unit_number: str | None = None,
        postal_code: str | None = None,
        country: str = "Canada",
        building_type: BuildingType = BuildingType.OTHER,
        occupancy_type: OccupancyType | None = None,
        construction_type: ConstructionType = ConstructionType.UNKNOWN,
        year_built: int | None = None,
        total_floors: int = 1,
        basement_levels: int = 0,
        **kwargs,
    ) -> Building:
        """Create a new building record."""
        # Verify agency exists
        agency = await self._get_agency(agency_id)
        if agency is None:
            raise BuildingError(f"Agency {agency_id} not found")

        # Build full address
        full_address = self._build_full_address(
            civic_number=civic_number,
            street_name=street_name,
            street_type=street_type,
            unit_number=unit_number,
            city=city,
            province_state=province_state,
            postal_code=postal_code,
            country=country,
        )

        building = Building(
            id=uuid.uuid4(),
            agency_id=agency_id,
            name=name,
            civic_number=civic_number,
            street_name=street_name,
            street_type=street_type,
            unit_number=unit_number,
            city=city,
            province_state=province_state,
            postal_code=postal_code,
            country=country,
            full_address=full_address,
            latitude=latitude,
            longitude=longitude,
            building_type=building_type,
            occupancy_type=occupancy_type,
            construction_type=construction_type,
            year_built=year_built,
            total_floors=total_floors,
            basement_levels=basement_levels,
            **kwargs,
        )

        self.db.add(building)
        await self.db.commit()
        await self.db.refresh(building)

        return building

    async def get_building(
        self,
        building_id: uuid.UUID,
        include_floor_plans: bool = False,
    ) -> Building | None:
        """Get building by ID."""
        query = select(Building).where(
            Building.id == building_id,
            Building.deleted_at.is_(None),
        )

        if include_floor_plans:
            query = query.options(selectinload(Building.floor_plans))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_buildings(
        self,
        agency_id: uuid.UUID | None = None,
        building_type: BuildingType | None = None,
        city: str | None = None,
        search_query: str | None = None,
        near_latitude: float | None = None,
        near_longitude: float | None = None,
        radius_km: float = 5.0,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Building], int]:
        """List buildings with optional filters. Returns (buildings, total_count)."""
        query = select(Building).where(Building.deleted_at.is_(None))
        count_query = select(func.count(Building.id)).where(Building.deleted_at.is_(None))

        conditions = []
        if agency_id:
            conditions.append(Building.agency_id == agency_id)
        if building_type:
            conditions.append(Building.building_type == building_type)
        if city:
            conditions.append(func.lower(Building.city) == city.lower())
        if search_query:
            search_pattern = f"%{search_query}%"
            conditions.append(
                or_(
                    Building.name.ilike(search_pattern),
                    Building.full_address.ilike(search_pattern),
                    Building.street_name.ilike(search_pattern),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # Get total count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination
        query = query.order_by(Building.name).limit(limit).offset(offset)

        result = await self.db.execute(query)
        buildings = list(result.scalars().all())

        # Filter by proximity if coordinates provided (post-query filtering)
        if near_latitude is not None and near_longitude is not None:
            buildings = [
                b for b in buildings
                if self._calculate_distance(
                    near_latitude, near_longitude,
                    b.latitude, b.longitude
                ) <= radius_km
            ]
            # Sort by distance
            buildings.sort(key=lambda b: self._calculate_distance(
                near_latitude, near_longitude,
                b.latitude, b.longitude
            ))
            total = len(buildings)

        return buildings, total

    async def update_building(
        self,
        building_id: uuid.UUID,
        **updates,
    ) -> Building:
        """Update building information."""
        building = await self.get_building(building_id)
        if building is None:
            raise BuildingError(f"Building {building_id} not found")

        # Update fields
        address_fields = {'civic_number', 'street_name', 'street_type', 'unit_number',
                          'city', 'province_state', 'postal_code', 'country'}
        address_changed = False

        for key, value in updates.items():
            if hasattr(building, key) and key not in ('id', 'created_at', 'agency_id'):
                setattr(building, key, value)
                if key in address_fields:
                    address_changed = True

        # Rebuild full address if address components changed
        if address_changed:
            building.full_address = self._build_full_address(
                civic_number=building.civic_number,
                street_name=building.street_name,
                street_type=building.street_type,
                unit_number=building.unit_number,
                city=building.city,
                province_state=building.province_state,
                postal_code=building.postal_code,
                country=building.country,
            )

        await self.db.commit()
        await self.db.refresh(building)

        return building

    async def delete_building(self, building_id: uuid.UUID) -> None:
        """Soft delete a building."""
        building = await self.get_building(building_id)
        if building is None:
            raise BuildingError(f"Building {building_id} not found")

        building.deleted_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def verify_building(
        self,
        building_id: uuid.UUID,
        verified_by_id: uuid.UUID,
    ) -> Building:
        """Mark a building as verified."""
        building = await self.get_building(building_id)
        if building is None:
            raise BuildingError(f"Building {building_id} not found")

        building.is_verified = True
        building.verified_by_id = verified_by_id
        building.verified_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(building)

        return building

    # ==================== Floor Plan Management ====================

    async def add_floor_plan(
        self,
        building_id: uuid.UUID,
        floor_number: int,
        floor_name: str | None = None,
        plan_file_url: str | None = None,
        plan_thumbnail_url: str | None = None,
        plan_data: bytes | None = None,
        file_type: str | None = None,
        floor_area_sqm: float | None = None,
        ceiling_height_m: float | None = None,
        key_locations: list | None = None,
        emergency_exits: list | None = None,
        fire_equipment: list | None = None,
        hazards: list | None = None,
        notes: str | None = None,
        bim_floor_data: dict | None = None,
    ) -> FloorPlan:
        """Add a floor plan to a building."""
        building = await self.get_building(building_id)
        if building is None:
            raise BuildingError(f"Building {building_id} not found")

        # Check if floor plan already exists for this floor
        existing = await self.db.execute(
            select(FloorPlan).where(
                FloorPlan.building_id == building_id,
                FloorPlan.floor_number == floor_number,
            )
        )
        if existing.scalar_one_or_none():
            raise BuildingError(f"Floor plan for floor {floor_number} already exists")

        floor_plan = FloorPlan(
            id=uuid.uuid4(),
            building_id=building_id,
            floor_number=floor_number,
            floor_name=floor_name or self._default_floor_name(floor_number),
            plan_file_url=plan_file_url,
            plan_thumbnail_url=plan_thumbnail_url,
            plan_data=plan_data,
            file_type=file_type,
            floor_area_sqm=floor_area_sqm,
            ceiling_height_m=ceiling_height_m,
            key_locations=key_locations,
            emergency_exits=emergency_exits,
            fire_equipment=fire_equipment,
            hazards=hazards,
            notes=notes,
            bim_floor_data=bim_floor_data,
        )

        self.db.add(floor_plan)
        await self.db.commit()
        await self.db.refresh(floor_plan)

        return floor_plan

    async def get_floor_plan(
        self,
        floor_plan_id: uuid.UUID,
    ) -> FloorPlan | None:
        """Get a specific floor plan."""
        result = await self.db.execute(
            select(FloorPlan).where(FloorPlan.id == floor_plan_id)
        )
        return result.scalar_one_or_none()

    async def get_building_floor_plans(
        self,
        building_id: uuid.UUID,
    ) -> list[FloorPlan]:
        """Get all floor plans for a building."""
        result = await self.db.execute(
            select(FloorPlan)
            .where(FloorPlan.building_id == building_id)
            .order_by(FloorPlan.floor_number)
        )
        return list(result.scalars().all())

    async def update_floor_plan(
        self,
        floor_plan_id: uuid.UUID,
        **updates,
    ) -> FloorPlan:
        """Update a floor plan."""
        floor_plan = await self.get_floor_plan(floor_plan_id)
        if floor_plan is None:
            raise BuildingError(f"Floor plan {floor_plan_id} not found")

        for key, value in updates.items():
            if hasattr(floor_plan, key) and key not in ('id', 'created_at', 'building_id'):
                setattr(floor_plan, key, value)

        await self.db.commit()
        await self.db.refresh(floor_plan)

        return floor_plan

    async def delete_floor_plan(self, floor_plan_id: uuid.UUID) -> None:
        """Delete a floor plan."""
        floor_plan = await self.get_floor_plan(floor_plan_id)
        if floor_plan is None:
            raise BuildingError(f"Floor plan {floor_plan_id} not found")

        await self.db.delete(floor_plan)
        await self.db.commit()

    # ==================== Search and Lookup ====================

    async def find_building_at_location(
        self,
        latitude: float,
        longitude: float,
        radius_meters: float = 50.0,
    ) -> Building | None:
        """Find the nearest building to a given location within radius."""
        # Convert radius to km
        radius_km = radius_meters / 1000

        result = await self.db.execute(
            select(Building).where(Building.deleted_at.is_(None))
        )
        buildings = list(result.scalars().all())

        nearest = None
        min_distance = float('inf')

        for building in buildings:
            distance = self._calculate_distance(
                latitude, longitude,
                building.latitude, building.longitude
            )
            if distance <= radius_km and distance < min_distance:
                nearest = building
                min_distance = distance

        return nearest

    async def search_buildings(
        self,
        query: str,
        agency_id: uuid.UUID | None = None,
        limit: int = 20,
    ) -> list[Building]:
        """Search buildings by name or address."""
        search_pattern = f"%{query}%"

        sql_query = select(Building).where(
            Building.deleted_at.is_(None),
            or_(
                Building.name.ilike(search_pattern),
                Building.full_address.ilike(search_pattern),
            )
        )

        if agency_id:
            sql_query = sql_query.where(Building.agency_id == agency_id)

        sql_query = sql_query.limit(limit)

        result = await self.db.execute(sql_query)
        return list(result.scalars().all())

    async def get_buildings_near_incident(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 1.0,
    ) -> list[tuple[Building, float]]:
        """Get buildings near an incident location with distances."""
        result = await self.db.execute(
            select(Building).where(Building.deleted_at.is_(None))
        )
        buildings = list(result.scalars().all())

        nearby = []
        for building in buildings:
            distance = self._calculate_distance(
                latitude, longitude,
                building.latitude, building.longitude
            )
            if distance <= radius_km:
                nearby.append((building, distance))

        # Sort by distance
        nearby.sort(key=lambda x: x[1])
        return nearby

    # ==================== BIM Import ====================

    async def import_bim_data(
        self,
        building_id: uuid.UUID,
        bim_data: dict,
        bim_file_url: str | None = None,
    ) -> Building:
        """Import BIM (Building Information Model) data for a building."""
        building = await self.get_building(building_id)
        if building is None:
            raise BuildingError(f"Building {building_id} not found")

        building.bim_data = bim_data
        if bim_file_url:
            building.bim_file_url = bim_file_url

        # Extract relevant information from BIM data if available
        if 'floors' in bim_data:
            building.total_floors = len(bim_data['floors'])

        if 'total_area' in bim_data:
            building.total_area_sqm = bim_data['total_area']

        if 'height' in bim_data:
            building.building_height_m = bim_data['height']

        await self.db.commit()
        await self.db.refresh(building)

        # If BIM data includes floor information, create floor plans
        if 'floors' in bim_data:
            for floor_data in bim_data['floors']:
                floor_number = floor_data.get('number', 0)
                existing = await self.db.execute(
                    select(FloorPlan).where(
                        FloorPlan.building_id == building_id,
                        FloorPlan.floor_number == floor_number,
                    )
                )
                if not existing.scalar_one_or_none():
                    await self.add_floor_plan(
                        building_id=building_id,
                        floor_number=floor_number,
                        floor_name=floor_data.get('name'),
                        floor_area_sqm=floor_data.get('area'),
                        ceiling_height_m=floor_data.get('ceiling_height'),
                        bim_floor_data=floor_data,
                    )

        return building

    # ==================== Statistics ====================

    async def get_building_stats(
        self,
        agency_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Get building statistics."""
        query = select(Building).where(Building.deleted_at.is_(None))
        if agency_id:
            query = query.where(Building.agency_id == agency_id)

        result = await self.db.execute(query)
        buildings = list(result.scalars().all())

        stats = {
            "total": len(buildings),
            "verified": sum(1 for b in buildings if b.is_verified),
            "unverified": sum(1 for b in buildings if not b.is_verified),
            "by_type": {},
            "by_hazard_level": {},
            "with_hazmat": sum(1 for b in buildings if b.has_hazmat),
            "with_sprinkler": sum(1 for b in buildings if b.has_sprinkler_system),
            "high_rise": sum(1 for b in buildings if b.total_floors >= 7),
        }

        for building in buildings:
            # Count by type
            bt = building.building_type.value
            stats["by_type"][bt] = stats["by_type"].get(bt, 0) + 1

            # Count by hazard level
            hl = building.hazard_level.value
            stats["by_hazard_level"][hl] = stats["by_hazard_level"].get(hl, 0) + 1

        return stats

    # ==================== Helper Methods ====================

    async def _get_agency(self, agency_id: uuid.UUID) -> Agency | None:
        """Get agency by ID."""
        result = await self.db.execute(
            select(Agency).where(Agency.id == agency_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _build_full_address(
        civic_number: str | None,
        street_name: str,
        street_type: str | None,
        unit_number: str | None,
        city: str,
        province_state: str,
        postal_code: str | None,
        country: str,
    ) -> str:
        """Build full address string from components."""
        parts = []

        # Street address
        street_parts = []
        if civic_number:
            street_parts.append(civic_number)
        street_parts.append(street_name)
        if street_type:
            street_parts.append(street_type)
        parts.append(" ".join(street_parts))

        if unit_number:
            parts.append(f"#{unit_number}")

        parts.append(city)
        parts.append(province_state)

        if postal_code:
            parts.append(postal_code)

        parts.append(country)

        return ", ".join(parts)

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

    @staticmethod
    def _default_floor_name(floor_number: int) -> str:
        """Generate default floor name from number."""
        if floor_number < 0:
            return f"Sous-sol {abs(floor_number)}"
        elif floor_number == 0:
            return "Rez-de-chaussée"
        else:
            return f"Étage {floor_number}"
