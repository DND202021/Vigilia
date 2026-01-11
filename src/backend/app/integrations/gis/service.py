"""GIS Integration Service.

Provides geographic information services including:
- Address geocoding/reverse geocoding
- Jurisdiction boundary lookup
- Map layer management
- Distance and routing calculations
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import asyncio
import math
import logging

from app.integrations.base import IntegrationAdapter, IntegrationError, CircuitBreakerConfig


logger = logging.getLogger(__name__)


class GISError(IntegrationError):
    """GIS service specific errors."""
    pass


@dataclass
class GeocodedAddress:
    """Result of geocoding operation."""
    formatted_address: str
    coordinates: tuple[float, float]  # (lat, lon)
    confidence: float  # 0.0 to 1.0
    match_type: str  # exact, interpolated, centroid
    source: str  # local, esri, nominatim
    address_components: dict[str, str] = field(default_factory=dict)


@dataclass
class Jurisdiction:
    """Jurisdiction/district information."""
    id: str
    name: str
    jurisdiction_type: str  # police, fire, ems, city, county
    agency_id: str | None = None
    agency_name: str | None = None
    boundaries: dict | None = None  # GeoJSON geometry
    contact_info: dict[str, str] = field(default_factory=dict)


@dataclass
class MapLayer:
    """Map layer definition."""
    id: str
    name: str
    layer_type: str  # vector, raster, feature
    source_url: str
    visible_by_default: bool = True
    min_zoom: int = 0
    max_zoom: int = 22
    opacity: float = 1.0
    style: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


@dataclass
class RouteResult:
    """Result of routing calculation."""
    distance_meters: float
    duration_seconds: float
    geometry: dict  # GeoJSON LineString
    instructions: list[dict] = field(default_factory=list)


class GISService(IntegrationAdapter):
    """
    Central GIS service for ERIOP.

    Provides geocoding, jurisdiction lookup, and routing
    with fallback between multiple providers.
    """

    def __init__(
        self,
        esri_api_key: str | None = None,
        arcgis_url: str | None = None,
        arcgis_token: str | None = None,
        cache_ttl_seconds: int = 3600,
        circuit_breaker_config: CircuitBreakerConfig | None = None,
    ):
        super().__init__(
            name="gis_service",
            circuit_breaker_config=circuit_breaker_config,
        )

        self.esri_api_key = esri_api_key
        self.arcgis_url = arcgis_url
        self.arcgis_token = arcgis_token
        self.cache_ttl = cache_ttl_seconds

        # Caches
        self._geocode_cache: dict[str, tuple[list[GeocodedAddress], datetime]] = {}
        self._jurisdiction_cache: dict[str, tuple[list[Jurisdiction], datetime]] = {}

        # Mock jurisdiction data (would come from ArcGIS in production)
        self._jurisdictions = self._init_mock_jurisdictions()

    def _init_mock_jurisdictions(self) -> list[Jurisdiction]:
        """Initialize mock jurisdiction data for development."""
        return [
            Jurisdiction(
                id="pd-001",
                name="Downtown Police District",
                jurisdiction_type="police",
                agency_id="police-dept-001",
                agency_name="City Police Department",
            ),
            Jurisdiction(
                id="fd-001",
                name="Fire District 1",
                jurisdiction_type="fire",
                agency_id="fire-dept-001",
                agency_name="City Fire Department",
            ),
            Jurisdiction(
                id="ems-001",
                name="EMS Zone 1",
                jurisdiction_type="ems",
                agency_id="ems-001",
                agency_name="Emergency Medical Services",
            ),
        ]

    async def connect(self) -> bool:
        """Initialize GIS service connections."""
        # In production, would verify API keys and ArcGIS connectivity
        self._connected = True
        logger.info("GIS service initialized")
        return True

    async def disconnect(self) -> None:
        """Shutdown GIS service."""
        self._connected = False
        self._geocode_cache.clear()
        self._jurisdiction_cache.clear()
        logger.info("GIS service shutdown")

    async def health_check(self) -> dict[str, Any]:
        """Check GIS service health."""
        return {
            "healthy": True,
            "esri_configured": bool(self.esri_api_key),
            "arcgis_configured": bool(self.arcgis_url),
            "cache_size": len(self._geocode_cache),
        }

    async def geocode(
        self,
        address: str,
        restrict_to_jurisdiction: str | None = None,
    ) -> list[GeocodedAddress]:
        """
        Geocode address to coordinates.

        Tries local/municipal geocoder first, falls back to ESRI.

        Args:
            address: Address string to geocode
            restrict_to_jurisdiction: Limit results to jurisdiction

        Returns:
            List of geocoding candidates, ordered by confidence
        """
        # Check cache
        cache_key = f"{address}:{restrict_to_jurisdiction or ''}"
        cached = self._get_cached(cache_key, self._geocode_cache)
        if cached:
            return cached

        results = []

        # Try ArcGIS Enterprise first (municipal)
        if self.arcgis_url:
            try:
                results = await self._geocode_arcgis(address)
            except Exception as e:
                logger.warning(f"ArcGIS geocoding failed: {e}")

        # Fall back to ESRI World Geocoder
        if not results and self.esri_api_key:
            try:
                results = await self._geocode_esri(address)
            except Exception as e:
                logger.warning(f"ESRI geocoding failed: {e}")

        # Fall back to simple mock geocoding for development
        if not results:
            results = self._mock_geocode(address)

        # Filter by jurisdiction if specified
        if restrict_to_jurisdiction and results:
            filtered = []
            for result in results:
                jurisdictions = await self.get_jurisdictions(
                    result.coordinates[0],
                    result.coordinates[1],
                )
                if any(j.id == restrict_to_jurisdiction for j in jurisdictions):
                    filtered.append(result)
            results = filtered or results  # Keep results if all filtered out

        # Cache results
        self._geocode_cache[cache_key] = (results, datetime.now(timezone.utc))

        return results

    async def reverse_geocode(
        self,
        lat: float,
        lon: float,
    ) -> GeocodedAddress | None:
        """
        Reverse geocode coordinates to address.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Geocoded address or None if not found
        """
        # Mock implementation for development
        return GeocodedAddress(
            formatted_address=f"{abs(lat):.4f}°{'N' if lat >= 0 else 'S'}, {abs(lon):.4f}°{'W' if lon < 0 else 'E'}",
            coordinates=(lat, lon),
            confidence=0.8,
            match_type="approximate",
            source="mock",
            address_components={
                "lat": str(lat),
                "lon": str(lon),
            },
        )

    async def get_jurisdictions(
        self,
        lat: float,
        lon: float,
        jurisdiction_type: str | None = None,
    ) -> list[Jurisdiction]:
        """
        Find jurisdictions containing a point.

        Args:
            lat: Latitude
            lon: Longitude
            jurisdiction_type: Filter by type (police, fire, ems)

        Returns:
            List of matching jurisdictions
        """
        cache_key = f"{lat:.6f},{lon:.6f}:{jurisdiction_type or ''}"
        cached = self._get_cached(cache_key, self._jurisdiction_cache)
        if cached:
            return cached

        # In production, query ArcGIS boundary layers
        # For now, return all mock jurisdictions (assuming point is in all)
        results = self._jurisdictions

        if jurisdiction_type:
            results = [j for j in results if j.jurisdiction_type == jurisdiction_type]

        self._jurisdiction_cache[cache_key] = (results, datetime.now(timezone.utc))

        return results

    async def get_distance(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> float:
        """
        Calculate distance between two points.

        Uses Haversine formula for straight-line distance.

        Args:
            origin: (lat, lon) tuple
            destination: (lat, lon) tuple

        Returns:
            Distance in meters
        """
        return self._haversine_distance(
            origin[0], origin[1],
            destination[0], destination[1],
        )

    async def get_route(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        avoid_traffic: bool = True,
    ) -> RouteResult | None:
        """
        Calculate route between two points.

        Args:
            origin: (lat, lon) starting point
            destination: (lat, lon) ending point
            avoid_traffic: Whether to consider traffic

        Returns:
            Route geometry, distance, and duration
        """
        # Mock implementation - straight line
        distance = await self.get_distance(origin, destination)

        # Assume average speed of 40 km/h in urban areas
        duration = distance / (40 * 1000 / 3600)  # meters / (km/h * m/km / s/h)

        return RouteResult(
            distance_meters=distance,
            duration_seconds=duration,
            geometry={
                "type": "LineString",
                "coordinates": [
                    [origin[1], origin[0]],  # GeoJSON is [lon, lat]
                    [destination[1], destination[0]],
                ],
            },
        )

    async def get_nearest_resources(
        self,
        lat: float,
        lon: float,
        resource_locations: list[tuple[str, float, float]],
        limit: int = 5,
    ) -> list[tuple[str, float]]:
        """
        Find nearest resources to a location.

        Args:
            lat: Latitude of target location
            lon: Longitude of target location
            resource_locations: List of (resource_id, lat, lon) tuples
            limit: Maximum number of results

        Returns:
            List of (resource_id, distance_meters) sorted by distance
        """
        distances = []

        for resource_id, res_lat, res_lon in resource_locations:
            distance = await self.get_distance((lat, lon), (res_lat, res_lon))
            distances.append((resource_id, distance))

        # Sort by distance
        distances.sort(key=lambda x: x[1])

        return distances[:limit]

    async def get_map_layers(
        self,
        layer_type: str | None = None,
    ) -> list[MapLayer]:
        """
        Get available map layers.

        Args:
            layer_type: Filter by layer type

        Returns:
            List of map layer definitions
        """
        # Mock layers for development
        layers = [
            MapLayer(
                id="base-osm",
                name="OpenStreetMap",
                layer_type="raster",
                source_url="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                visible_by_default=True,
            ),
            MapLayer(
                id="incidents",
                name="Active Incidents",
                layer_type="vector",
                source_url="/api/v1/gis/layers/incidents",
                visible_by_default=True,
                style={"color": "red", "radius": 8},
            ),
            MapLayer(
                id="resources",
                name="Resources",
                layer_type="vector",
                source_url="/api/v1/gis/layers/resources",
                visible_by_default=True,
                style={"color": "blue", "radius": 6},
            ),
            MapLayer(
                id="jurisdictions",
                name="Jurisdiction Boundaries",
                layer_type="vector",
                source_url="/api/v1/gis/layers/jurisdictions",
                visible_by_default=False,
                opacity=0.3,
            ),
        ]

        if layer_type:
            layers = [l for l in layers if l.layer_type == layer_type]

        return layers

    def _get_cached(
        self,
        key: str,
        cache: dict,
    ) -> Any | None:
        """Get value from cache if not expired."""
        if key in cache:
            value, timestamp = cache[key]
            age = (datetime.now(timezone.utc) - timestamp).total_seconds()
            if age < self.cache_ttl:
                return value
            else:
                del cache[key]
        return None

    async def _geocode_arcgis(self, address: str) -> list[GeocodedAddress]:
        """Geocode using ArcGIS Enterprise."""
        # Would use aiohttp to query ArcGIS geocoding service
        return []

    async def _geocode_esri(self, address: str) -> list[GeocodedAddress]:
        """Geocode using ESRI World Geocoder."""
        # Would use aiohttp to query ESRI service
        return []

    def _mock_geocode(self, address: str) -> list[GeocodedAddress]:
        """Mock geocoding for development."""
        # Return a mock result based on address keywords
        address_lower = address.lower()

        # Montreal area
        lat, lon = 45.5017, -73.5673

        if "main st" in address_lower:
            lat, lon = 45.5050, -73.5700
        elif "downtown" in address_lower:
            lat, lon = 45.5017, -73.5673
        elif "airport" in address_lower:
            lat, lon = 45.4657, -73.7455

        return [
            GeocodedAddress(
                formatted_address=address,
                coordinates=(lat, lon),
                confidence=0.75,
                match_type="approximate",
                source="mock",
                address_components={"input": address},
            )
        ]

    @staticmethod
    def _haversine_distance(
        lat1: float, lon1: float,
        lat2: float, lon2: float,
    ) -> float:
        """
        Calculate distance between two points using Haversine formula.

        Returns distance in meters.
        """
        R = 6371000  # Earth's radius in meters

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2 +
            math.cos(phi1) * math.cos(phi2) *
            math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c
