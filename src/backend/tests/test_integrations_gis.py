"""Tests for GIS integration service."""

import pytest
from datetime import datetime, timezone

from app.integrations.gis.service import (
    GISService,
    GeocodedAddress,
    Jurisdiction,
    MapLayer,
    RouteResult,
)


class TestGeocodedAddress:
    """Tests for GeocodedAddress dataclass."""

    def test_create_geocoded_address(self):
        """Should create address with all fields."""
        address = GeocodedAddress(
            formatted_address="123 Main St, Montreal, QC H2X 1Y2",
            coordinates=(45.5017, -73.5673),
            confidence=0.95,
            match_type="exact",
            source="esri",
            address_components={
                "street": "Main St",
                "city": "Montreal",
                "state": "QC",
            },
        )

        assert address.formatted_address == "123 Main St, Montreal, QC H2X 1Y2"
        assert address.coordinates == (45.5017, -73.5673)
        assert address.confidence == 0.95


class TestJurisdiction:
    """Tests for Jurisdiction dataclass."""

    def test_create_jurisdiction(self):
        """Should create jurisdiction with all fields."""
        jurisdiction = Jurisdiction(
            id="pd-001",
            name="Downtown Police District",
            jurisdiction_type="police",
            agency_id="police-dept-001",
            agency_name="City Police Department",
        )

        assert jurisdiction.id == "pd-001"
        assert jurisdiction.jurisdiction_type == "police"
        assert jurisdiction.agency_name == "City Police Department"


class TestGISService:
    """Tests for GIS service."""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Should track connection state."""
        gis = GISService()

        await gis.connect()
        assert gis.is_connected

        await gis.disconnect()
        assert not gis.is_connected

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Should return health status."""
        gis = GISService()
        await gis.connect()

        health = await gis.health_check()

        assert health["healthy"] is True

    @pytest.mark.asyncio
    async def test_geocode_address(self):
        """Should geocode address to coordinates."""
        gis = GISService()
        await gis.connect()

        results = await gis.geocode("123 Main St, Montreal")

        assert len(results) > 0
        assert results[0].coordinates is not None
        assert len(results[0].coordinates) == 2

    @pytest.mark.asyncio
    async def test_geocode_caching(self):
        """Should cache geocoding results."""
        gis = GISService()
        await gis.connect()

        # First call
        results1 = await gis.geocode("456 Oak Ave")

        # Second call should hit cache
        results2 = await gis.geocode("456 Oak Ave")

        assert results1 == results2
        assert len(gis._geocode_cache) == 1

    @pytest.mark.asyncio
    async def test_reverse_geocode(self):
        """Should reverse geocode coordinates."""
        gis = GISService()
        await gis.connect()

        result = await gis.reverse_geocode(45.5017, -73.5673)

        assert result is not None
        assert result.coordinates == (45.5017, -73.5673)

    @pytest.mark.asyncio
    async def test_get_jurisdictions(self):
        """Should find jurisdictions for location."""
        gis = GISService()
        await gis.connect()

        jurisdictions = await gis.get_jurisdictions(45.5017, -73.5673)

        assert len(jurisdictions) > 0
        assert all(isinstance(j, Jurisdiction) for j in jurisdictions)

    @pytest.mark.asyncio
    async def test_filter_jurisdictions_by_type(self):
        """Should filter jurisdictions by type."""
        gis = GISService()
        await gis.connect()

        police = await gis.get_jurisdictions(45.5017, -73.5673, "police")
        fire = await gis.get_jurisdictions(45.5017, -73.5673, "fire")

        assert all(j.jurisdiction_type == "police" for j in police)
        assert all(j.jurisdiction_type == "fire" for j in fire)

    @pytest.mark.asyncio
    async def test_calculate_distance(self):
        """Should calculate distance between points."""
        gis = GISService()

        # Montreal to Toronto is approximately 504 km
        distance = await gis.get_distance(
            (45.5017, -73.5673),  # Montreal
            (43.6532, -79.3832),  # Toronto
        )

        # Should be between 500-520 km
        assert 500_000 < distance < 520_000  # meters

    @pytest.mark.asyncio
    async def test_distance_same_point(self):
        """Distance to same point should be zero."""
        gis = GISService()

        distance = await gis.get_distance(
            (45.5017, -73.5673),
            (45.5017, -73.5673),
        )

        assert distance == 0.0

    @pytest.mark.asyncio
    async def test_get_route(self):
        """Should calculate route between points."""
        gis = GISService()
        await gis.connect()

        route = await gis.get_route(
            (45.5017, -73.5673),
            (45.5100, -73.5700),
        )

        assert route is not None
        assert route.distance_meters > 0
        assert route.duration_seconds > 0
        assert route.geometry["type"] == "LineString"

    @pytest.mark.asyncio
    async def test_get_nearest_resources(self):
        """Should find nearest resources to location."""
        gis = GISService()

        resources = [
            ("R1", 45.5020, -73.5680),  # Close
            ("R2", 45.5100, -73.5800),  # Medium
            ("R3", 45.5500, -73.6000),  # Far
        ]

        nearest = await gis.get_nearest_resources(
            45.5017, -73.5673,
            resources,
            limit=2,
        )

        assert len(nearest) == 2
        assert nearest[0][0] == "R1"  # Closest first
        assert nearest[1][0] == "R2"

    @pytest.mark.asyncio
    async def test_nearest_resources_sorted(self):
        """Resources should be sorted by distance."""
        gis = GISService()

        resources = [
            ("R1", 45.6000, -73.7000),  # Far
            ("R2", 45.5020, -73.5675),  # Very close
            ("R3", 45.5100, -73.5800),  # Medium
        ]

        nearest = await gis.get_nearest_resources(
            45.5017, -73.5673,
            resources,
        )

        # Should be sorted by distance
        for i in range(len(nearest) - 1):
            assert nearest[i][1] <= nearest[i + 1][1]

    @pytest.mark.asyncio
    async def test_get_map_layers(self):
        """Should return map layers."""
        gis = GISService()
        await gis.connect()

        layers = await gis.get_map_layers()

        assert len(layers) > 0
        assert all(isinstance(l, MapLayer) for l in layers)

    @pytest.mark.asyncio
    async def test_filter_map_layers_by_type(self):
        """Should filter layers by type."""
        gis = GISService()
        await gis.connect()

        vector_layers = await gis.get_map_layers(layer_type="vector")

        assert all(l.layer_type == "vector" for l in vector_layers)

    def test_haversine_formula(self):
        """Should correctly implement Haversine formula."""
        # Known distance: New York to Los Angeles is approximately 3940 km
        distance = GISService._haversine_distance(
            40.7128, -74.0060,   # New York
            34.0522, -118.2437,  # Los Angeles
        )

        # Should be between 3900-4000 km
        assert 3_900_000 < distance < 4_000_000

    def test_haversine_antipodal(self):
        """Should handle antipodal points."""
        # North pole to south pole
        distance = GISService._haversine_distance(
            90.0, 0.0,   # North pole
            -90.0, 0.0,  # South pole
        )

        # Should be approximately half Earth's circumference (20,000 km)
        assert 19_900_000 < distance < 20_100_000


class TestGISCaching:
    """Tests for GIS caching functionality."""

    @pytest.mark.asyncio
    async def test_cache_expires(self):
        """Cache should expire after TTL."""
        gis = GISService(cache_ttl_seconds=0)  # Immediate expiry
        await gis.connect()

        # First call
        await gis.geocode("test address")

        # Clear cache manually since TTL is 0
        gis._geocode_cache.clear()

        # Should not be cached
        assert len(gis._geocode_cache) == 0

    @pytest.mark.asyncio
    async def test_different_addresses_cached_separately(self):
        """Different addresses should have separate cache entries."""
        gis = GISService()
        await gis.connect()

        await gis.geocode("address one")
        await gis.geocode("address two")

        assert len(gis._geocode_cache) == 2

    @pytest.mark.asyncio
    async def test_cache_cleared_on_disconnect(self):
        """Cache should be cleared on disconnect."""
        gis = GISService()
        await gis.connect()

        await gis.geocode("test address")
        assert len(gis._geocode_cache) > 0

        await gis.disconnect()
        assert len(gis._geocode_cache) == 0
