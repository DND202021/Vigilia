"""GIS Layer Management Service.

This service manages geographic information system (GIS) layers
for map visualization including:
- Vector layers (points, lines, polygons)
- Raster layers (satellite imagery, terrain)
- External services (WMS, WFS, WMTS, ArcGIS)
- Custom data layers (zones, districts, hazards)
"""

import asyncio
import uuid
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import httpx

from sqlalchemy.ext.asyncio import AsyncSession


class LayerType(str, Enum):
    """GIS layer types."""

    # Vector layer types
    GEOJSON = "geojson"
    SHAPEFILE = "shapefile"
    KML = "kml"
    GPX = "gpx"

    # Tile layer types
    XYZ = "xyz"
    TMS = "tms"

    # OGC service types
    WMS = "wms"
    WFS = "wfs"
    WMTS = "wmts"

    # Vendor-specific
    ARCGIS_REST = "arcgis_rest"
    MAPBOX = "mapbox"

    # Internal data layers
    INTERNAL = "internal"


class LayerCategory(str, Enum):
    """Layer categories for organization."""

    BASE_MAP = "base_map"
    ADMINISTRATIVE = "administrative"
    EMERGENCY = "emergency"
    INFRASTRUCTURE = "infrastructure"
    ENVIRONMENTAL = "environmental"
    TRANSPORTATION = "transportation"
    UTILITY = "utility"
    CUSTOM = "custom"


class GeometryType(str, Enum):
    """Geometry types for vector layers."""

    POINT = "Point"
    LINE = "LineString"
    POLYGON = "Polygon"
    MULTI_POINT = "MultiPoint"
    MULTI_LINE = "MultiLineString"
    MULTI_POLYGON = "MultiPolygon"
    GEOMETRY_COLLECTION = "GeometryCollection"


@dataclass
class LayerStyle:
    """Layer styling configuration."""

    # Fill styling
    fill_color: str = "#3388ff"
    fill_opacity: float = 0.2

    # Stroke styling
    stroke_color: str = "#3388ff"
    stroke_width: float = 2
    stroke_opacity: float = 1.0
    stroke_dash_array: str | None = None

    # Point styling
    point_radius: float = 6
    point_icon: str | None = None

    # Label styling
    label_field: str | None = None
    label_font_size: int = 12
    label_color: str = "#000000"
    label_offset: tuple[int, int] = (0, 0)

    # Clustering
    cluster_enabled: bool = False
    cluster_radius: int = 50
    cluster_color: str = "#ff6b6b"

    def to_dict(self) -> dict:
        """Convert style to dictionary."""
        return {
            "fillColor": self.fill_color,
            "fillOpacity": self.fill_opacity,
            "strokeColor": self.stroke_color,
            "strokeWidth": self.stroke_width,
            "strokeOpacity": self.stroke_opacity,
            "strokeDashArray": self.stroke_dash_array,
            "pointRadius": self.point_radius,
            "pointIcon": self.point_icon,
            "labelField": self.label_field,
            "labelFontSize": self.label_font_size,
            "labelColor": self.label_color,
            "labelOffset": list(self.label_offset),
            "clusterEnabled": self.cluster_enabled,
            "clusterRadius": self.cluster_radius,
            "clusterColor": self.cluster_color,
        }


@dataclass
class BoundingBox:
    """Geographic bounding box."""

    min_lng: float
    min_lat: float
    max_lng: float
    max_lat: float

    def contains(self, lat: float, lng: float) -> bool:
        """Check if point is within bounding box."""
        return (
            self.min_lng <= lng <= self.max_lng and
            self.min_lat <= lat <= self.max_lat
        )

    def to_list(self) -> list[float]:
        """Convert to [minLng, minLat, maxLng, maxLat] format."""
        return [self.min_lng, self.min_lat, self.max_lng, self.max_lat]

    def to_wkt(self) -> str:
        """Convert to WKT polygon format."""
        return (
            f"POLYGON(({self.min_lng} {self.min_lat}, "
            f"{self.max_lng} {self.min_lat}, "
            f"{self.max_lng} {self.max_lat}, "
            f"{self.min_lng} {self.max_lat}, "
            f"{self.min_lng} {self.min_lat}))"
        )


@dataclass
class GISLayer:
    """GIS layer configuration."""

    id: uuid.UUID
    name: str
    layer_type: LayerType
    category: LayerCategory
    description: str | None = None
    source_url: str | None = None
    source_data: dict | None = None
    style: LayerStyle = field(default_factory=LayerStyle)
    bounds: BoundingBox | None = None
    min_zoom: int = 0
    max_zoom: int = 22
    visible: bool = True
    opacity: float = 1.0
    z_index: int = 0
    attribution: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Service-specific settings
    wms_layers: str | None = None
    wms_format: str = "image/png"
    wfs_typename: str | None = None
    arcgis_layer_id: int | None = None

    # Caching
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600


@dataclass
class Feature:
    """GeoJSON feature."""

    id: str
    geometry_type: GeometryType
    coordinates: Any
    properties: dict[str, Any] = field(default_factory=dict)

    def to_geojson(self) -> dict:
        """Convert to GeoJSON format."""
        return {
            "type": "Feature",
            "id": self.id,
            "geometry": {
                "type": self.geometry_type.value,
                "coordinates": self.coordinates,
            },
            "properties": self.properties,
        }


class GISLayerService:
    """Service for managing GIS layers."""

    def __init__(self, db: AsyncSession):
        """Initialize GIS layer service."""
        self.db = db
        self._layers: dict[uuid.UUID, GISLayer] = {}
        self._cache: dict[str, tuple[datetime, Any]] = {}

    def register_layer(self, layer: GISLayer) -> None:
        """Register a GIS layer."""
        self._layers[layer.id] = layer

    def unregister_layer(self, layer_id: uuid.UUID) -> bool:
        """Unregister a GIS layer."""
        if layer_id in self._layers:
            del self._layers[layer_id]
            return True
        return False

    def get_layer(self, layer_id: uuid.UUID) -> GISLayer | None:
        """Get layer by ID."""
        return self._layers.get(layer_id)

    def list_layers(
        self,
        category: LayerCategory | None = None,
        visible_only: bool = False,
    ) -> list[GISLayer]:
        """List all layers."""
        layers = list(self._layers.values())

        if category:
            layers = [l for l in layers if l.category == category]

        if visible_only:
            layers = [l for l in layers if l.visible]

        # Sort by z_index
        layers.sort(key=lambda l: l.z_index)

        return layers

    async def fetch_layer_data(
        self,
        layer_id: uuid.UUID,
        bounds: BoundingBox | None = None,
    ) -> dict | None:
        """Fetch data for a layer.

        Args:
            layer_id: Layer ID
            bounds: Optional bounding box to filter data

        Returns:
            GeoJSON FeatureCollection or tile URL
        """
        layer = self._layers.get(layer_id)
        if not layer:
            return None

        # Check cache
        cache_key = f"{layer_id}:{bounds.to_list() if bounds else 'all'}"
        if layer.cache_enabled and cache_key in self._cache:
            cached_at, data = self._cache[cache_key]
            if (datetime.utcnow() - cached_at).total_seconds() < layer.cache_ttl_seconds:
                return data

        # Fetch based on layer type
        data = None

        if layer.layer_type == LayerType.GEOJSON:
            data = await self._fetch_geojson(layer, bounds)
        elif layer.layer_type == LayerType.WMS:
            data = self._get_wms_url(layer)
        elif layer.layer_type == LayerType.WFS:
            data = await self._fetch_wfs(layer, bounds)
        elif layer.layer_type == LayerType.ARCGIS_REST:
            data = await self._fetch_arcgis(layer, bounds)
        elif layer.layer_type == LayerType.XYZ:
            data = {"url": layer.source_url}
        elif layer.layer_type == LayerType.INTERNAL:
            data = layer.source_data

        # Cache result
        if data and layer.cache_enabled:
            self._cache[cache_key] = (datetime.utcnow(), data)

        return data

    async def _fetch_geojson(
        self,
        layer: GISLayer,
        bounds: BoundingBox | None = None,
    ) -> dict | None:
        """Fetch GeoJSON data."""
        if layer.source_data:
            data = layer.source_data
        elif layer.source_url:
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(layer.source_url)
                    response.raise_for_status()
                    data = response.json()
                except Exception:
                    return None
        else:
            return None

        # Filter by bounds if specified
        if bounds and "features" in data:
            filtered_features = []
            for feature in data["features"]:
                if self._feature_in_bounds(feature, bounds):
                    filtered_features.append(feature)
            data = {
                "type": "FeatureCollection",
                "features": filtered_features,
            }

        return data

    def _get_wms_url(self, layer: GISLayer) -> dict:
        """Get WMS layer configuration."""
        return {
            "type": "wms",
            "url": layer.source_url,
            "layers": layer.wms_layers,
            "format": layer.wms_format,
            "transparent": True,
            "attribution": layer.attribution,
        }

    async def _fetch_wfs(
        self,
        layer: GISLayer,
        bounds: BoundingBox | None = None,
    ) -> dict | None:
        """Fetch data from WFS service."""
        if not layer.source_url or not layer.wfs_typename:
            return None

        params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeName": layer.wfs_typename,
            "outputFormat": "application/json",
        }

        if bounds:
            params["bbox"] = f"{bounds.min_lat},{bounds.min_lng},{bounds.max_lat},{bounds.max_lng}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(layer.source_url, params=params)
                response.raise_for_status()
                return response.json()
            except Exception:
                return None

    async def _fetch_arcgis(
        self,
        layer: GISLayer,
        bounds: BoundingBox | None = None,
    ) -> dict | None:
        """Fetch data from ArcGIS REST service."""
        if not layer.source_url:
            return None

        url = f"{layer.source_url}/{layer.arcgis_layer_id or 0}/query"

        params = {
            "where": "1=1",
            "outFields": "*",
            "f": "geojson",
            "returnGeometry": "true",
        }

        if bounds:
            params["geometry"] = json.dumps({
                "xmin": bounds.min_lng,
                "ymin": bounds.min_lat,
                "xmax": bounds.max_lng,
                "ymax": bounds.max_lat,
                "spatialReference": {"wkid": 4326},
            })
            params["geometryType"] = "esriGeometryEnvelope"
            params["inSR"] = "4326"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except Exception:
                return None

    def _feature_in_bounds(self, feature: dict, bounds: BoundingBox) -> bool:
        """Check if a feature intersects with bounds."""
        geometry = feature.get("geometry", {})
        coords = geometry.get("coordinates")

        if not coords:
            return False

        geo_type = geometry.get("type", "")

        # Get representative point(s) based on geometry type
        if geo_type == "Point":
            return bounds.contains(coords[1], coords[0])

        elif geo_type in ("LineString", "MultiPoint"):
            for coord in coords:
                if bounds.contains(coord[1], coord[0]):
                    return True
            return False

        elif geo_type == "Polygon":
            # Check if any point of the polygon is in bounds
            for ring in coords:
                for coord in ring:
                    if bounds.contains(coord[1], coord[0]):
                        return True
            return False

        elif geo_type in ("MultiLineString", "MultiPolygon"):
            for part in coords:
                if geo_type == "MultiPolygon":
                    for ring in part:
                        for coord in ring:
                            if bounds.contains(coord[1], coord[0]):
                                return True
                else:
                    for coord in part:
                        if bounds.contains(coord[1], coord[0]):
                            return True
            return False

        return True

    def create_internal_layer(
        self,
        name: str,
        features: list[Feature],
        category: LayerCategory = LayerCategory.CUSTOM,
        style: LayerStyle | None = None,
        **kwargs,
    ) -> GISLayer:
        """Create an internal data layer from features.

        Args:
            name: Layer name
            features: List of features
            category: Layer category
            style: Optional styling
            **kwargs: Additional layer properties

        Returns:
            Created layer
        """
        # Build GeoJSON
        geojson = {
            "type": "FeatureCollection",
            "features": [f.to_geojson() for f in features],
        }

        # Calculate bounds
        bounds = self._calculate_bounds(geojson)

        layer = GISLayer(
            id=uuid.uuid4(),
            name=name,
            layer_type=LayerType.INTERNAL,
            category=category,
            source_data=geojson,
            style=style or LayerStyle(),
            bounds=bounds,
            **kwargs,
        )

        self.register_layer(layer)
        return layer

    def _calculate_bounds(self, geojson: dict) -> BoundingBox | None:
        """Calculate bounding box for GeoJSON."""
        min_lng = float("inf")
        min_lat = float("inf")
        max_lng = float("-inf")
        max_lat = float("-inf")

        def update_bounds(coords: list) -> None:
            nonlocal min_lng, min_lat, max_lng, max_lat
            if isinstance(coords[0], (int, float)):
                # This is a coordinate pair
                lng, lat = coords[0], coords[1]
                min_lng = min(min_lng, lng)
                min_lat = min(min_lat, lat)
                max_lng = max(max_lng, lng)
                max_lat = max(max_lat, lat)
            else:
                # Nested array
                for c in coords:
                    update_bounds(c)

        for feature in geojson.get("features", []):
            coords = feature.get("geometry", {}).get("coordinates")
            if coords:
                update_bounds(coords)

        if min_lng == float("inf"):
            return None

        return BoundingBox(
            min_lng=min_lng,
            min_lat=min_lat,
            max_lng=max_lng,
            max_lat=max_lat,
        )

    def clear_cache(self, layer_id: uuid.UUID | None = None) -> None:
        """Clear layer cache.

        Args:
            layer_id: Specific layer to clear, or None for all
        """
        if layer_id:
            keys_to_remove = [
                k for k in self._cache.keys()
                if k.startswith(str(layer_id))
            ]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            self._cache.clear()


# Predefined emergency-related layers
def create_predefined_layers(service: GISLayerService) -> list[GISLayer]:
    """Create predefined layers for emergency services."""
    layers = []

    # Fire stations layer
    fire_stations = GISLayer(
        id=uuid.uuid4(),
        name="Fire Stations",
        layer_type=LayerType.INTERNAL,
        category=LayerCategory.EMERGENCY,
        description="Fire station locations",
        style=LayerStyle(
            fill_color="#ff4444",
            stroke_color="#cc0000",
            point_radius=8,
            point_icon="fire-station",
            cluster_enabled=True,
        ),
    )
    service.register_layer(fire_stations)
    layers.append(fire_stations)

    # Hospitals layer
    hospitals = GISLayer(
        id=uuid.uuid4(),
        name="Hospitals",
        layer_type=LayerType.INTERNAL,
        category=LayerCategory.EMERGENCY,
        description="Hospital and medical facility locations",
        style=LayerStyle(
            fill_color="#44aaff",
            stroke_color="#0066cc",
            point_radius=8,
            point_icon="hospital",
            cluster_enabled=True,
        ),
    )
    service.register_layer(hospitals)
    layers.append(hospitals)

    # Hydrants layer
    hydrants = GISLayer(
        id=uuid.uuid4(),
        name="Fire Hydrants",
        layer_type=LayerType.INTERNAL,
        category=LayerCategory.INFRASTRUCTURE,
        description="Fire hydrant locations",
        style=LayerStyle(
            fill_color="#ffaa00",
            stroke_color="#cc8800",
            point_radius=5,
            cluster_enabled=True,
            cluster_radius=30,
        ),
        min_zoom=14,  # Only show at higher zoom levels
    )
    service.register_layer(hydrants)
    layers.append(hydrants)

    # Response zones layer
    response_zones = GISLayer(
        id=uuid.uuid4(),
        name="Response Zones",
        layer_type=LayerType.INTERNAL,
        category=LayerCategory.ADMINISTRATIVE,
        description="Emergency response zone boundaries",
        style=LayerStyle(
            fill_color="#3388ff",
            fill_opacity=0.1,
            stroke_color="#3388ff",
            stroke_width=2,
            label_field="zone_name",
        ),
    )
    service.register_layer(response_zones)
    layers.append(response_zones)

    # Hazard areas layer
    hazard_areas = GISLayer(
        id=uuid.uuid4(),
        name="Hazard Areas",
        layer_type=LayerType.INTERNAL,
        category=LayerCategory.ENVIRONMENTAL,
        description="Known hazard zones (flood, industrial, etc.)",
        style=LayerStyle(
            fill_color="#ff6b6b",
            fill_opacity=0.3,
            stroke_color="#ff0000",
            stroke_width=2,
            stroke_dash_array="5,5",
        ),
    )
    service.register_layer(hazard_areas)
    layers.append(hazard_areas)

    return layers
