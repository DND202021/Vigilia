"""Geospatial Query Service.

This service provides location-based queries using PostGIS
for finding nearby incidents, resources, and zones.
"""

import uuid
from dataclasses import dataclass
from math import radians, cos, sin, asin, sqrt
from typing import Any, TypeVar, Generic

from sqlalchemy import select, func, text, Float, cast
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident
from app.models.resource import Resource
from app.models.alert import Alert

T = TypeVar("T")


@dataclass
class GeoPoint:
    """Geographic point with latitude and longitude."""

    latitude: float
    longitude: float

    def to_tuple(self) -> tuple[float, float]:
        return (self.latitude, self.longitude)


@dataclass
class BoundingBox:
    """Geographic bounding box."""

    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float

    @classmethod
    def from_center(cls, center: GeoPoint, radius_km: float) -> "BoundingBox":
        """Create bounding box from center point and radius.

        This is an approximation that works well for small distances.
        """
        # Approximate degrees per km
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * cos(radians(center.latitude)))

        return cls(
            min_lat=center.latitude - lat_delta,
            min_lon=center.longitude - lon_delta,
            max_lat=center.latitude + lat_delta,
            max_lon=center.longitude + lon_delta,
        )


@dataclass
class NearbyResult(Generic[T]):
    """Result of a nearby query with distance."""

    item: T
    distance_km: float


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great circle distance between two points in kilometers."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))

    return 6371 * c  # Earth's radius in km


class GeospatialService:
    """Service for geospatial queries."""

    def __init__(self, db: AsyncSession):
        """Initialize geospatial service."""
        self.db = db

    async def find_nearby_incidents(
        self,
        center: GeoPoint,
        radius_km: float = 10.0,
        limit: int = 50,
        active_only: bool = True,
    ) -> list[NearbyResult[Incident]]:
        """Find incidents within a radius of a point.

        Args:
            center: Center point to search from
            radius_km: Search radius in kilometers
            limit: Maximum number of results
            active_only: Only return active (not closed) incidents

        Returns:
            List of incidents with distances, sorted by distance
        """
        # Use bounding box for initial filtering (fast)
        bbox = BoundingBox.from_center(center, radius_km)

        query = select(Incident).where(
            Incident.latitude >= bbox.min_lat,
            Incident.latitude <= bbox.max_lat,
            Incident.longitude >= bbox.min_lon,
            Incident.longitude <= bbox.max_lon,
        )

        if active_only:
            from app.models.incident import IncidentStatus
            query = query.where(
                Incident.status.not_in([
                    IncidentStatus.RESOLVED,
                    IncidentStatus.CLOSED,
                ])
            )

        result = await self.db.execute(query)
        incidents = result.scalars().all()

        # Calculate exact distances and filter
        nearby = []
        for incident in incidents:
            distance = haversine_distance(
                center.latitude, center.longitude,
                incident.latitude, incident.longitude
            )
            if distance <= radius_km:
                nearby.append(NearbyResult(item=incident, distance_km=distance))

        # Sort by distance and limit
        nearby.sort(key=lambda x: x.distance_km)
        return nearby[:limit]

    async def find_nearby_resources(
        self,
        center: GeoPoint,
        radius_km: float = 10.0,
        limit: int = 50,
        available_only: bool = True,
        resource_types: list[str] | None = None,
    ) -> list[NearbyResult[Resource]]:
        """Find resources within a radius of a point.

        Args:
            center: Center point to search from
            radius_km: Search radius in kilometers
            limit: Maximum number of results
            available_only: Only return available resources
            resource_types: Filter by resource types

        Returns:
            List of resources with distances, sorted by distance
        """
        bbox = BoundingBox.from_center(center, radius_km)

        query = select(Resource).where(
            Resource.current_latitude.is_not(None),
            Resource.current_longitude.is_not(None),
            Resource.current_latitude >= bbox.min_lat,
            Resource.current_latitude <= bbox.max_lat,
            Resource.current_longitude >= bbox.min_lon,
            Resource.current_longitude <= bbox.max_lon,
            Resource.deleted_at.is_(None),
        )

        if available_only:
            from app.models.resource import ResourceStatus
            query = query.where(Resource.status == ResourceStatus.AVAILABLE)

        if resource_types:
            from app.models.resource import ResourceType
            types = [ResourceType(t) for t in resource_types]
            query = query.where(Resource.resource_type.in_(types))

        result = await self.db.execute(query)
        resources = result.scalars().all()

        # Calculate exact distances and filter
        nearby = []
        for resource in resources:
            if resource.current_latitude and resource.current_longitude:
                distance = haversine_distance(
                    center.latitude, center.longitude,
                    resource.current_latitude, resource.current_longitude
                )
                if distance <= radius_km:
                    nearby.append(NearbyResult(item=resource, distance_km=distance))

        nearby.sort(key=lambda x: x.distance_km)
        return nearby[:limit]

    async def find_nearby_alerts(
        self,
        center: GeoPoint,
        radius_km: float = 10.0,
        limit: int = 50,
        pending_only: bool = True,
    ) -> list[NearbyResult[Alert]]:
        """Find alerts within a radius of a point.

        Args:
            center: Center point to search from
            radius_km: Search radius in kilometers
            limit: Maximum number of results
            pending_only: Only return pending alerts

        Returns:
            List of alerts with distances, sorted by distance
        """
        bbox = BoundingBox.from_center(center, radius_km)

        query = select(Alert).where(
            Alert.latitude.is_not(None),
            Alert.longitude.is_not(None),
            Alert.latitude >= bbox.min_lat,
            Alert.latitude <= bbox.max_lat,
            Alert.longitude >= bbox.min_lon,
            Alert.longitude <= bbox.max_lon,
        )

        if pending_only:
            from app.models.alert import AlertStatus
            query = query.where(Alert.status == AlertStatus.PENDING)

        result = await self.db.execute(query)
        alerts = result.scalars().all()

        # Calculate exact distances and filter
        nearby = []
        for alert in alerts:
            if alert.latitude and alert.longitude:
                distance = haversine_distance(
                    center.latitude, center.longitude,
                    alert.latitude, alert.longitude
                )
                if distance <= radius_km:
                    nearby.append(NearbyResult(item=alert, distance_km=distance))

        nearby.sort(key=lambda x: x.distance_km)
        return nearby[:limit]

    async def find_in_polygon(
        self,
        polygon: list[GeoPoint],
        entity_type: str = "incident",
    ) -> list[Any]:
        """Find entities within a polygon.

        Uses ray casting algorithm for point-in-polygon test.

        Args:
            polygon: List of points defining the polygon
            entity_type: Type of entity to search (incident, resource, alert)

        Returns:
            List of entities within the polygon
        """
        if len(polygon) < 3:
            raise ValueError("Polygon must have at least 3 points")

        # Get model class
        model_map = {
            "incident": Incident,
            "resource": Resource,
            "alert": Alert,
        }
        model = model_map.get(entity_type)
        if not model:
            raise ValueError(f"Unknown entity type: {entity_type}")

        # Calculate bounding box for initial filtering
        min_lat = min(p.latitude for p in polygon)
        max_lat = max(p.latitude for p in polygon)
        min_lon = min(p.longitude for p in polygon)
        max_lon = max(p.longitude for p in polygon)

        # Build query based on entity type
        if entity_type == "incident":
            query = select(model).where(
                model.latitude >= min_lat,
                model.latitude <= max_lat,
                model.longitude >= min_lon,
                model.longitude <= max_lon,
            )
        elif entity_type == "resource":
            query = select(model).where(
                model.current_latitude.is_not(None),
                model.current_latitude >= min_lat,
                model.current_latitude <= max_lat,
                model.current_longitude >= min_lon,
                model.current_longitude <= max_lon,
                model.deleted_at.is_(None),
            )
        else:  # alert
            query = select(model).where(
                model.latitude.is_not(None),
                model.latitude >= min_lat,
                model.latitude <= max_lat,
                model.longitude >= min_lon,
                model.longitude <= max_lon,
            )

        result = await self.db.execute(query)
        entities = result.scalars().all()

        # Filter by point-in-polygon
        polygon_coords = [(p.latitude, p.longitude) for p in polygon]
        filtered = []

        for entity in entities:
            if entity_type == "resource":
                lat, lon = entity.current_latitude, entity.current_longitude
            else:
                lat, lon = entity.latitude, entity.longitude

            if lat and lon and self._point_in_polygon(lat, lon, polygon_coords):
                filtered.append(entity)

        return filtered

    def _point_in_polygon(
        self,
        lat: float,
        lon: float,
        polygon: list[tuple[float, float]],
    ) -> bool:
        """Check if a point is inside a polygon using ray casting."""
        n = len(polygon)
        inside = False

        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]

            if ((yi > lon) != (yj > lon)) and \
               (lat < (xj - xi) * (lon - yi) / (yj - yi) + xi):
                inside = not inside

            j = i

        return inside

    async def get_cluster_centers(
        self,
        entity_type: str = "incident",
        grid_size_km: float = 5.0,
        min_cluster_size: int = 2,
    ) -> list[dict]:
        """Get cluster centers for entities on a map.

        Groups entities into grid cells and returns centers of cells
        with multiple entities.

        Args:
            entity_type: Type of entity to cluster
            grid_size_km: Size of grid cells in kilometers
            min_cluster_size: Minimum entities to form a cluster

        Returns:
            List of cluster info with center and count
        """
        model_map = {
            "incident": Incident,
            "resource": Resource,
            "alert": Alert,
        }
        model = model_map.get(entity_type)
        if not model:
            raise ValueError(f"Unknown entity type: {entity_type}")

        # Get all entities with locations
        if entity_type == "resource":
            query = select(model).where(
                model.current_latitude.is_not(None),
                model.current_longitude.is_not(None),
                model.deleted_at.is_(None),
            )
        else:
            query = select(model).where(
                model.latitude.is_not(None),
                model.longitude.is_not(None),
            )

        result = await self.db.execute(query)
        entities = result.scalars().all()

        # Group by grid cell
        grid_size_deg = grid_size_km / 111.0  # Approximate degrees
        clusters: dict[tuple[int, int], list] = {}

        for entity in entities:
            if entity_type == "resource":
                lat, lon = entity.current_latitude, entity.current_longitude
            else:
                lat, lon = entity.latitude, entity.longitude

            if lat and lon:
                cell_x = int(lat / grid_size_deg)
                cell_y = int(lon / grid_size_deg)
                key = (cell_x, cell_y)

                if key not in clusters:
                    clusters[key] = []
                clusters[key].append((lat, lon, entity.id))

        # Calculate cluster centers
        result_clusters = []
        for (cell_x, cell_y), points in clusters.items():
            if len(points) >= min_cluster_size:
                avg_lat = sum(p[0] for p in points) / len(points)
                avg_lon = sum(p[1] for p in points) / len(points)
                result_clusters.append({
                    "center": {"latitude": avg_lat, "longitude": avg_lon},
                    "count": len(points),
                    "entity_ids": [str(p[2]) for p in points],
                })

        return result_clusters
