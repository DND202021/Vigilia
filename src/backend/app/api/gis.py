"""GIS Layer Management API endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user, require_permission, Permission
from app.models.user import User
from app.services.gis_layers import (
    GISLayerService,
    GISLayer,
    LayerType,
    LayerCategory,
    LayerStyle,
    BoundingBox,
    Feature,
    GeometryType,
    create_predefined_layers,
)

router = APIRouter()


# In-memory service instance
_gis_service: GISLayerService | None = None


def get_gis_service(db: AsyncSession = Depends(get_db)) -> GISLayerService:
    """Get or create GIS layer service."""
    global _gis_service
    if _gis_service is None:
        _gis_service = GISLayerService(db)
        # Initialize with predefined layers
        create_predefined_layers(_gis_service)
    return _gis_service


class StyleConfig(BaseModel):
    """Layer style configuration."""

    fill_color: str = "#3388ff"
    fill_opacity: float = 0.2
    stroke_color: str = "#3388ff"
    stroke_width: float = 2
    stroke_opacity: float = 1.0
    stroke_dash_array: str | None = None
    point_radius: float = 6
    point_icon: str | None = None
    label_field: str | None = None
    label_font_size: int = 12
    label_color: str = "#000000"
    cluster_enabled: bool = False
    cluster_radius: int = 50
    cluster_color: str = "#ff6b6b"


class LayerCreate(BaseModel):
    """Create GIS layer request."""

    name: str = Field(..., min_length=1, max_length=255)
    layer_type: str = Field(..., description="Layer type: geojson, wms, wfs, xyz, arcgis_rest, internal")
    category: str = Field("custom", description="Layer category")
    description: str | None = None
    source_url: str | None = None
    source_data: dict | None = None
    style: StyleConfig | None = None
    min_zoom: int = Field(0, ge=0, le=22)
    max_zoom: int = Field(22, ge=0, le=22)
    visible: bool = True
    opacity: float = Field(1.0, ge=0, le=1)
    z_index: int = 0
    attribution: str | None = None
    wms_layers: str | None = None
    wms_format: str = "image/png"
    wfs_typename: str | None = None
    arcgis_layer_id: int | None = None
    cache_enabled: bool = True
    cache_ttl_seconds: int = Field(3600, ge=0)


class LayerResponse(BaseModel):
    """GIS layer response."""

    id: str
    name: str
    layer_type: str
    category: str
    description: str | None
    source_url: str | None
    style: dict
    min_zoom: int
    max_zoom: int
    visible: bool
    opacity: float
    z_index: int
    attribution: str | None
    bounds: list[float] | None
    cache_enabled: bool
    created_at: datetime


class FeatureCreate(BaseModel):
    """Create feature request."""

    geometry_type: str = Field(..., description="Geometry type: Point, LineString, Polygon, etc.")
    coordinates: list = Field(..., description="GeoJSON coordinates")
    properties: dict = Field(default_factory=dict)


class InternalLayerCreate(BaseModel):
    """Create internal layer from features."""

    name: str = Field(..., min_length=1, max_length=255)
    category: str = "custom"
    description: str | None = None
    features: list[FeatureCreate]
    style: StyleConfig | None = None
    min_zoom: int = Field(0, ge=0, le=22)
    max_zoom: int = Field(22, ge=0, le=22)
    visible: bool = True


class BoundsQuery(BaseModel):
    """Bounding box query parameters."""

    min_lng: float = Field(..., ge=-180, le=180)
    min_lat: float = Field(..., ge=-90, le=90)
    max_lng: float = Field(..., ge=-180, le=180)
    max_lat: float = Field(..., ge=-90, le=90)


class LayerUpdate(BaseModel):
    """Update layer request."""

    name: str | None = None
    description: str | None = None
    style: StyleConfig | None = None
    visible: bool | None = None
    opacity: float | None = None
    z_index: int | None = None
    min_zoom: int | None = None
    max_zoom: int | None = None


@router.post("", response_model=LayerResponse)
async def create_layer(
    request: LayerCreate,
    service: GISLayerService = Depends(get_gis_service),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> LayerResponse:
    """Create a new GIS layer."""
    try:
        layer_type = LayerType(request.layer_type.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid layer type. Valid types: {[t.value for t in LayerType]}",
        )

    try:
        category = LayerCategory(request.category.lower())
    except ValueError:
        category = LayerCategory.CUSTOM

    # Build style
    style = LayerStyle()
    if request.style:
        style = LayerStyle(
            fill_color=request.style.fill_color,
            fill_opacity=request.style.fill_opacity,
            stroke_color=request.style.stroke_color,
            stroke_width=request.style.stroke_width,
            stroke_opacity=request.style.stroke_opacity,
            stroke_dash_array=request.style.stroke_dash_array,
            point_radius=request.style.point_radius,
            point_icon=request.style.point_icon,
            label_field=request.style.label_field,
            label_font_size=request.style.label_font_size,
            label_color=request.style.label_color,
            cluster_enabled=request.style.cluster_enabled,
            cluster_radius=request.style.cluster_radius,
            cluster_color=request.style.cluster_color,
        )

    layer = GISLayer(
        id=uuid.uuid4(),
        name=request.name,
        layer_type=layer_type,
        category=category,
        description=request.description,
        source_url=request.source_url,
        source_data=request.source_data,
        style=style,
        min_zoom=request.min_zoom,
        max_zoom=request.max_zoom,
        visible=request.visible,
        opacity=request.opacity,
        z_index=request.z_index,
        attribution=request.attribution,
        wms_layers=request.wms_layers,
        wms_format=request.wms_format,
        wfs_typename=request.wfs_typename,
        arcgis_layer_id=request.arcgis_layer_id,
        cache_enabled=request.cache_enabled,
        cache_ttl_seconds=request.cache_ttl_seconds,
    )

    service.register_layer(layer)

    return LayerResponse(
        id=str(layer.id),
        name=layer.name,
        layer_type=layer.layer_type.value,
        category=layer.category.value,
        description=layer.description,
        source_url=layer.source_url,
        style=layer.style.to_dict(),
        min_zoom=layer.min_zoom,
        max_zoom=layer.max_zoom,
        visible=layer.visible,
        opacity=layer.opacity,
        z_index=layer.z_index,
        attribution=layer.attribution,
        bounds=layer.bounds.to_list() if layer.bounds else None,
        cache_enabled=layer.cache_enabled,
        created_at=layer.created_at,
    )


@router.post("/internal", response_model=LayerResponse)
async def create_internal_layer(
    request: InternalLayerCreate,
    service: GISLayerService = Depends(get_gis_service),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> LayerResponse:
    """Create an internal layer from features."""
    try:
        category = LayerCategory(request.category.lower())
    except ValueError:
        category = LayerCategory.CUSTOM

    # Build style
    style = None
    if request.style:
        style = LayerStyle(
            fill_color=request.style.fill_color,
            fill_opacity=request.style.fill_opacity,
            stroke_color=request.style.stroke_color,
            stroke_width=request.style.stroke_width,
            stroke_opacity=request.style.stroke_opacity,
            stroke_dash_array=request.style.stroke_dash_array,
            point_radius=request.style.point_radius,
            point_icon=request.style.point_icon,
            label_field=request.style.label_field,
            label_font_size=request.style.label_font_size,
            label_color=request.style.label_color,
            cluster_enabled=request.style.cluster_enabled,
            cluster_radius=request.style.cluster_radius,
            cluster_color=request.style.cluster_color,
        )

    # Convert features
    features = []
    for idx, f in enumerate(request.features):
        try:
            geo_type = GeometryType(f.geometry_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid geometry type at index {idx}: {f.geometry_type}",
            )

        features.append(Feature(
            id=str(uuid.uuid4()),
            geometry_type=geo_type,
            coordinates=f.coordinates,
            properties=f.properties,
        ))

    layer = service.create_internal_layer(
        name=request.name,
        features=features,
        category=category,
        style=style,
        description=request.description,
        min_zoom=request.min_zoom,
        max_zoom=request.max_zoom,
        visible=request.visible,
    )

    return LayerResponse(
        id=str(layer.id),
        name=layer.name,
        layer_type=layer.layer_type.value,
        category=layer.category.value,
        description=layer.description,
        source_url=layer.source_url,
        style=layer.style.to_dict(),
        min_zoom=layer.min_zoom,
        max_zoom=layer.max_zoom,
        visible=layer.visible,
        opacity=layer.opacity,
        z_index=layer.z_index,
        attribution=layer.attribution,
        bounds=layer.bounds.to_list() if layer.bounds else None,
        cache_enabled=layer.cache_enabled,
        created_at=layer.created_at,
    )


@router.get("", response_model=list[LayerResponse])
async def list_layers(
    category: str | None = None,
    visible_only: bool = False,
    service: GISLayerService = Depends(get_gis_service),
    current_user: User = Depends(get_current_active_user),
) -> list[LayerResponse]:
    """List all GIS layers."""
    cat = None
    if category:
        try:
            cat = LayerCategory(category.lower())
        except ValueError:
            pass

    layers = service.list_layers(category=cat, visible_only=visible_only)

    return [
        LayerResponse(
            id=str(layer.id),
            name=layer.name,
            layer_type=layer.layer_type.value,
            category=layer.category.value,
            description=layer.description,
            source_url=layer.source_url,
            style=layer.style.to_dict(),
            min_zoom=layer.min_zoom,
            max_zoom=layer.max_zoom,
            visible=layer.visible,
            opacity=layer.opacity,
            z_index=layer.z_index,
            attribution=layer.attribution,
            bounds=layer.bounds.to_list() if layer.bounds else None,
            cache_enabled=layer.cache_enabled,
            created_at=layer.created_at,
        )
        for layer in layers
    ]


@router.get("/categories")
async def list_categories(
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """List available layer categories."""
    return {
        "categories": [
            {
                "id": cat.value,
                "name": cat.value.replace("_", " ").title(),
            }
            for cat in LayerCategory
        ]
    }


@router.get("/types")
async def list_layer_types(
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """List available layer types."""
    return {
        "types": [
            {
                "id": lt.value,
                "name": lt.value.upper(),
                "description": _get_layer_type_description(lt),
            }
            for lt in LayerType
        ]
    }


def _get_layer_type_description(layer_type: LayerType) -> str:
    """Get description for layer type."""
    descriptions = {
        LayerType.GEOJSON: "GeoJSON vector data",
        LayerType.SHAPEFILE: "ESRI Shapefile",
        LayerType.KML: "Keyhole Markup Language",
        LayerType.GPX: "GPS Exchange Format",
        LayerType.XYZ: "XYZ tile layer (e.g., OSM tiles)",
        LayerType.TMS: "Tile Map Service",
        LayerType.WMS: "Web Map Service",
        LayerType.WFS: "Web Feature Service",
        LayerType.WMTS: "Web Map Tile Service",
        LayerType.ARCGIS_REST: "ArcGIS REST API",
        LayerType.MAPBOX: "Mapbox tiles",
        LayerType.INTERNAL: "Internal data layer",
    }
    return descriptions.get(layer_type, "")


@router.get("/{layer_id}", response_model=LayerResponse)
async def get_layer(
    layer_id: str,
    service: GISLayerService = Depends(get_gis_service),
    current_user: User = Depends(get_current_active_user),
) -> LayerResponse:
    """Get a GIS layer by ID."""
    try:
        layer_uuid = uuid.UUID(layer_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid layer ID format",
        )

    layer = service.get_layer(layer_uuid)
    if not layer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layer not found",
        )

    return LayerResponse(
        id=str(layer.id),
        name=layer.name,
        layer_type=layer.layer_type.value,
        category=layer.category.value,
        description=layer.description,
        source_url=layer.source_url,
        style=layer.style.to_dict(),
        min_zoom=layer.min_zoom,
        max_zoom=layer.max_zoom,
        visible=layer.visible,
        opacity=layer.opacity,
        z_index=layer.z_index,
        attribution=layer.attribution,
        bounds=layer.bounds.to_list() if layer.bounds else None,
        cache_enabled=layer.cache_enabled,
        created_at=layer.created_at,
    )


@router.patch("/{layer_id}", response_model=LayerResponse)
async def update_layer(
    layer_id: str,
    update: LayerUpdate,
    service: GISLayerService = Depends(get_gis_service),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> LayerResponse:
    """Update a GIS layer."""
    try:
        layer_uuid = uuid.UUID(layer_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid layer ID format",
        )

    layer = service.get_layer(layer_uuid)
    if not layer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layer not found",
        )

    # Apply updates
    if update.name is not None:
        layer.name = update.name
    if update.description is not None:
        layer.description = update.description
    if update.visible is not None:
        layer.visible = update.visible
    if update.opacity is not None:
        layer.opacity = update.opacity
    if update.z_index is not None:
        layer.z_index = update.z_index
    if update.min_zoom is not None:
        layer.min_zoom = update.min_zoom
    if update.max_zoom is not None:
        layer.max_zoom = update.max_zoom

    if update.style:
        layer.style = LayerStyle(
            fill_color=update.style.fill_color,
            fill_opacity=update.style.fill_opacity,
            stroke_color=update.style.stroke_color,
            stroke_width=update.style.stroke_width,
            stroke_opacity=update.style.stroke_opacity,
            stroke_dash_array=update.style.stroke_dash_array,
            point_radius=update.style.point_radius,
            point_icon=update.style.point_icon,
            label_field=update.style.label_field,
            label_font_size=update.style.label_font_size,
            label_color=update.style.label_color,
            cluster_enabled=update.style.cluster_enabled,
            cluster_radius=update.style.cluster_radius,
            cluster_color=update.style.cluster_color,
        )

    layer.updated_at = datetime.utcnow()

    return LayerResponse(
        id=str(layer.id),
        name=layer.name,
        layer_type=layer.layer_type.value,
        category=layer.category.value,
        description=layer.description,
        source_url=layer.source_url,
        style=layer.style.to_dict(),
        min_zoom=layer.min_zoom,
        max_zoom=layer.max_zoom,
        visible=layer.visible,
        opacity=layer.opacity,
        z_index=layer.z_index,
        attribution=layer.attribution,
        bounds=layer.bounds.to_list() if layer.bounds else None,
        cache_enabled=layer.cache_enabled,
        created_at=layer.created_at,
    )


@router.delete("/{layer_id}")
async def delete_layer(
    layer_id: str,
    service: GISLayerService = Depends(get_gis_service),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> dict:
    """Delete a GIS layer."""
    try:
        layer_uuid = uuid.UUID(layer_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid layer ID format",
        )

    layer = service.get_layer(layer_uuid)
    if not layer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layer not found",
        )

    layer_name = layer.name
    service.unregister_layer(layer_uuid)

    return {"message": f"Layer '{layer_name}' deleted"}


@router.get("/{layer_id}/data")
async def get_layer_data(
    layer_id: str,
    min_lng: float | None = Query(None, ge=-180, le=180),
    min_lat: float | None = Query(None, ge=-90, le=90),
    max_lng: float | None = Query(None, ge=-180, le=180),
    max_lat: float | None = Query(None, ge=-90, le=90),
    service: GISLayerService = Depends(get_gis_service),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Get data for a GIS layer.

    Returns GeoJSON FeatureCollection for vector layers,
    or connection info for tile/service layers.
    """
    try:
        layer_uuid = uuid.UUID(layer_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid layer ID format",
        )

    bounds = None
    if all(v is not None for v in [min_lng, min_lat, max_lng, max_lat]):
        bounds = BoundingBox(
            min_lng=min_lng,
            min_lat=min_lat,
            max_lng=max_lng,
            max_lat=max_lat,
        )

    data = await service.fetch_layer_data(layer_uuid, bounds)

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layer not found or no data available",
        )

    return data


@router.post("/{layer_id}/cache/clear")
async def clear_layer_cache(
    layer_id: str,
    service: GISLayerService = Depends(get_gis_service),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> dict:
    """Clear cache for a layer."""
    try:
        layer_uuid = uuid.UUID(layer_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid layer ID format",
        )

    layer = service.get_layer(layer_uuid)
    if not layer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layer not found",
        )

    service.clear_cache(layer_uuid)

    return {"message": f"Cache cleared for layer '{layer.name}'"}


@router.post("/cache/clear-all")
async def clear_all_cache(
    service: GISLayerService = Depends(get_gis_service),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> dict:
    """Clear all layer caches."""
    service.clear_cache()
    return {"message": "All layer caches cleared"}
