"""Geospatial Query API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.services.geospatial import GeospatialService, GeoPoint

router = APIRouter()


class PointRequest(BaseModel):
    """Geographic point."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class NearbyIncidentResponse(BaseModel):
    """Nearby incident response."""

    id: str
    incident_number: str
    title: str
    category: str
    priority: int
    status: str
    latitude: float
    longitude: float
    distance_km: float


class NearbyResourceResponse(BaseModel):
    """Nearby resource response."""

    id: str
    name: str
    call_sign: str | None
    resource_type: str
    status: str
    latitude: float
    longitude: float
    distance_km: float


class NearbyAlertResponse(BaseModel):
    """Nearby alert response."""

    id: str
    title: str
    alert_type: str
    severity: str
    status: str
    latitude: float
    longitude: float
    distance_km: float


class ClusterResponse(BaseModel):
    """Cluster center response."""

    center: PointRequest
    count: int
    entity_ids: list[str]


class PolygonSearchRequest(BaseModel):
    """Polygon search request."""

    polygon: list[PointRequest]
    entity_type: str = "incident"


@router.get("/nearby/incidents", response_model=list[NearbyIncidentResponse])
async def find_nearby_incidents(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(10.0, ge=0.1, le=100),
    limit: int = Query(50, ge=1, le=200),
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[NearbyIncidentResponse]:
    """Find incidents within a radius of a point."""
    service = GeospatialService(db)
    center = GeoPoint(latitude=latitude, longitude=longitude)

    results = await service.find_nearby_incidents(
        center=center,
        radius_km=radius_km,
        limit=limit,
        active_only=active_only,
    )

    return [
        NearbyIncidentResponse(
            id=str(r.item.id),
            incident_number=r.item.incident_number,
            title=r.item.title,
            category=r.item.category.value,
            priority=r.item.priority,
            status=r.item.status.value,
            latitude=r.item.latitude,
            longitude=r.item.longitude,
            distance_km=round(r.distance_km, 2),
        )
        for r in results
    ]


@router.get("/nearby/resources", response_model=list[NearbyResourceResponse])
async def find_nearby_resources(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(10.0, ge=0.1, le=100),
    limit: int = Query(50, ge=1, le=200),
    available_only: bool = True,
    resource_types: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[NearbyResourceResponse]:
    """Find resources within a radius of a point."""
    service = GeospatialService(db)
    center = GeoPoint(latitude=latitude, longitude=longitude)

    # Parse resource types
    types_list = None
    if resource_types:
        types_list = [t.strip() for t in resource_types.split(",")]

    results = await service.find_nearby_resources(
        center=center,
        radius_km=radius_km,
        limit=limit,
        available_only=available_only,
        resource_types=types_list,
    )

    return [
        NearbyResourceResponse(
            id=str(r.item.id),
            name=r.item.name,
            call_sign=r.item.call_sign,
            resource_type=r.item.resource_type.value,
            status=r.item.status.value,
            latitude=r.item.current_latitude,
            longitude=r.item.current_longitude,
            distance_km=round(r.distance_km, 2),
        )
        for r in results
    ]


@router.get("/nearby/alerts", response_model=list[NearbyAlertResponse])
async def find_nearby_alerts(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(10.0, ge=0.1, le=100),
    limit: int = Query(50, ge=1, le=200),
    pending_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[NearbyAlertResponse]:
    """Find alerts within a radius of a point."""
    service = GeospatialService(db)
    center = GeoPoint(latitude=latitude, longitude=longitude)

    results = await service.find_nearby_alerts(
        center=center,
        radius_km=radius_km,
        limit=limit,
        pending_only=pending_only,
    )

    return [
        NearbyAlertResponse(
            id=str(r.item.id),
            title=r.item.title,
            alert_type=r.item.alert_type,
            severity=r.item.severity.value,
            status=r.item.status.value,
            latitude=r.item.latitude,
            longitude=r.item.longitude,
            distance_km=round(r.distance_km, 2),
        )
        for r in results
    ]


@router.post("/polygon")
async def search_in_polygon(
    request: PolygonSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Find entities within a polygon area."""
    if len(request.polygon) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Polygon must have at least 3 points",
        )

    service = GeospatialService(db)
    polygon = [GeoPoint(latitude=p.latitude, longitude=p.longitude) for p in request.polygon]

    try:
        entities = await service.find_in_polygon(
            polygon=polygon,
            entity_type=request.entity_type,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Format response based on entity type
    results = []
    for entity in entities:
        if request.entity_type == "incident":
            results.append({
                "id": str(entity.id),
                "incident_number": entity.incident_number,
                "title": entity.title,
                "latitude": entity.latitude,
                "longitude": entity.longitude,
            })
        elif request.entity_type == "resource":
            results.append({
                "id": str(entity.id),
                "name": entity.name,
                "call_sign": entity.call_sign,
                "latitude": entity.current_latitude,
                "longitude": entity.current_longitude,
            })
        else:  # alert
            results.append({
                "id": str(entity.id),
                "title": entity.title,
                "alert_type": entity.alert_type,
                "latitude": entity.latitude,
                "longitude": entity.longitude,
            })

    return {
        "entity_type": request.entity_type,
        "count": len(results),
        "results": results,
    }


@router.get("/clusters", response_model=list[ClusterResponse])
async def get_clusters(
    entity_type: str = "incident",
    grid_size_km: float = Query(5.0, ge=1, le=50),
    min_cluster_size: int = Query(2, ge=2, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[ClusterResponse]:
    """Get clusters of entities for map visualization."""
    service = GeospatialService(db)

    try:
        clusters = await service.get_cluster_centers(
            entity_type=entity_type,
            grid_size_km=grid_size_km,
            min_cluster_size=min_cluster_size,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return [
        ClusterResponse(
            center=PointRequest(
                latitude=c["center"]["latitude"],
                longitude=c["center"]["longitude"],
            ),
            count=c["count"],
            entity_ids=c["entity_ids"],
        )
        for c in clusters
    ]
