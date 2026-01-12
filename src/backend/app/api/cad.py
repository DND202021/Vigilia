"""CAD Integration API endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user, require_permission, Permission
from app.models.user import User
from app.services.cad_adapter import (
    CADVendor,
    CADAdapter,
    CADSyncService,
    GenericRESTAdapter,
    TriTechAdapter,
    create_adapter,
)

router = APIRouter()


# In-memory storage for CAD connections
_cad_connections: dict[str, dict] = {}
_sync_services: dict[str, CADSyncService] = {}


class CADConnectionCreate(BaseModel):
    """Create CAD connection request."""

    name: str = Field(..., min_length=1, max_length=255)
    vendor: str = Field(..., description="CAD vendor: generic, tritech, motorola, tyler, intergraph, mark43")
    base_url: str = Field(..., min_length=1)
    api_key: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    username: str | None = None
    password: str | None = None
    sync_enabled: bool = False
    sync_interval_seconds: int = Field(30, ge=10, le=300)
    field_mapping: dict | None = None


class CADConnectionResponse(BaseModel):
    """CAD connection response."""

    id: str
    name: str
    vendor: str
    base_url: str
    sync_enabled: bool
    sync_interval_seconds: int
    connected: bool
    last_sync: datetime | None


class CADIncidentResponse(BaseModel):
    """CAD incident response."""

    cad_id: str
    incident_number: str
    call_type: str
    priority: int
    status: str
    address: str
    city: str | None
    state: str | None
    latitude: float | None
    longitude: float | None
    caller_name: str | None
    caller_phone: str | None
    description: str | None
    assigned_units: list[str]


class CADUnitResponse(BaseModel):
    """CAD unit response."""

    cad_id: str
    unit_id: str
    call_sign: str
    unit_type: str
    status: str
    latitude: float | None
    longitude: float | None
    current_incident: str | None


class SyncStatusRequest(BaseModel):
    """Request to update unit status to CAD."""

    unit_id: str
    status: str
    incident_id: str | None = None


class SyncIncidentRequest(BaseModel):
    """Request to sync incident to CAD."""

    incident_id: str
    status: str | None = None
    comment: str | None = None


@router.post("", response_model=CADConnectionResponse)
async def create_cad_connection(
    request: CADConnectionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> CADConnectionResponse:
    """Create a new CAD connection."""
    try:
        vendor = CADVendor(request.vendor.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown vendor. Supported vendors: {[v.value for v in CADVendor]}",
        )

    connection_id = str(uuid.uuid4())

    config = {
        "base_url": request.base_url,
        "api_key": request.api_key,
        "client_id": request.client_id,
        "client_secret": request.client_secret,
        "username": request.username,
        "password": request.password,
        "field_mapping": request.field_mapping or {},
    }

    # Test connection
    adapter = create_adapter(vendor, config)
    connected = await adapter.connect()
    await adapter.disconnect()

    if not connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not connect to CAD system. Check configuration.",
        )

    # Store connection
    _cad_connections[connection_id] = {
        "id": connection_id,
        "name": request.name,
        "vendor": vendor.value,
        "config": config,
        "sync_enabled": request.sync_enabled,
        "sync_interval_seconds": request.sync_interval_seconds,
        "connected": connected,
        "last_sync": None,
    }

    # Start sync if enabled
    if request.sync_enabled:
        adapter = create_adapter(vendor, config)
        sync_service = CADSyncService(db, adapter)

        async def start_sync():
            try:
                await sync_service.start_sync(request.sync_interval_seconds)
            except Exception:
                pass

        _sync_services[connection_id] = sync_service
        background_tasks.add_task(start_sync)

    return CADConnectionResponse(
        id=connection_id,
        name=request.name,
        vendor=vendor.value,
        base_url=request.base_url,
        sync_enabled=request.sync_enabled,
        sync_interval_seconds=request.sync_interval_seconds,
        connected=connected,
        last_sync=None,
    )


@router.get("", response_model=list[CADConnectionResponse])
async def list_cad_connections(
    current_user: User = Depends(get_current_active_user),
) -> list[CADConnectionResponse]:
    """List all CAD connections."""
    return [
        CADConnectionResponse(
            id=conn["id"],
            name=conn["name"],
            vendor=conn["vendor"],
            base_url=conn["config"]["base_url"],
            sync_enabled=conn["sync_enabled"],
            sync_interval_seconds=conn["sync_interval_seconds"],
            connected=conn["connected"],
            last_sync=conn["last_sync"],
        )
        for conn in _cad_connections.values()
    ]


@router.get("/{connection_id}", response_model=CADConnectionResponse)
async def get_cad_connection(
    connection_id: str,
    current_user: User = Depends(get_current_active_user),
) -> CADConnectionResponse:
    """Get CAD connection by ID."""
    conn = _cad_connections.get(connection_id)
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CAD connection not found",
        )

    return CADConnectionResponse(
        id=conn["id"],
        name=conn["name"],
        vendor=conn["vendor"],
        base_url=conn["config"]["base_url"],
        sync_enabled=conn["sync_enabled"],
        sync_interval_seconds=conn["sync_interval_seconds"],
        connected=conn["connected"],
        last_sync=conn["last_sync"],
    )


@router.delete("/{connection_id}")
async def delete_cad_connection(
    connection_id: str,
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> dict:
    """Delete a CAD connection."""
    if connection_id not in _cad_connections:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CAD connection not found",
        )

    # Stop sync if running
    if connection_id in _sync_services:
        await _sync_services[connection_id].stop_sync()
        del _sync_services[connection_id]

    conn = _cad_connections.pop(connection_id)

    return {"message": f"CAD connection '{conn['name']}' deleted"}


@router.post("/{connection_id}/test")
async def test_cad_connection(
    connection_id: str,
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Test CAD connection."""
    conn = _cad_connections.get(connection_id)
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CAD connection not found",
        )

    try:
        vendor = CADVendor(conn["vendor"])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid vendor configuration",
        )

    adapter = create_adapter(vendor, conn["config"])
    connected = await adapter.connect()

    if connected:
        # Update connection status
        conn["connected"] = True
        await adapter.disconnect()
        return {"message": "Connection successful", "connected": True}
    else:
        conn["connected"] = False
        return {"message": "Connection failed", "connected": False}


@router.get("/{connection_id}/incidents", response_model=list[CADIncidentResponse])
async def fetch_cad_incidents(
    connection_id: str,
    active_only: bool = True,
    current_user: User = Depends(get_current_active_user),
) -> list[CADIncidentResponse]:
    """Fetch incidents from CAD system."""
    conn = _cad_connections.get(connection_id)
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CAD connection not found",
        )

    try:
        vendor = CADVendor(conn["vendor"])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid vendor configuration",
        )

    adapter = create_adapter(vendor, conn["config"])

    if not await adapter.connect():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to CAD system",
        )

    try:
        incidents = await adapter.fetch_incidents(active_only=active_only)

        return [
            CADIncidentResponse(
                cad_id=i.cad_id,
                incident_number=i.incident_number,
                call_type=i.call_type,
                priority=i.priority,
                status=i.status,
                address=i.address,
                city=i.city,
                state=i.state,
                latitude=i.latitude,
                longitude=i.longitude,
                caller_name=i.caller_name,
                caller_phone=i.caller_phone,
                description=i.description,
                assigned_units=i.assigned_units,
            )
            for i in incidents
        ]
    finally:
        await adapter.disconnect()


@router.get("/{connection_id}/units", response_model=list[CADUnitResponse])
async def fetch_cad_units(
    connection_id: str,
    current_user: User = Depends(get_current_active_user),
) -> list[CADUnitResponse]:
    """Fetch units from CAD system."""
    conn = _cad_connections.get(connection_id)
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CAD connection not found",
        )

    try:
        vendor = CADVendor(conn["vendor"])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid vendor configuration",
        )

    adapter = create_adapter(vendor, conn["config"])

    if not await adapter.connect():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to CAD system",
        )

    try:
        units = await adapter.fetch_units()

        return [
            CADUnitResponse(
                cad_id=u.cad_id,
                unit_id=u.unit_id,
                call_sign=u.call_sign,
                unit_type=u.unit_type,
                status=u.status,
                latitude=u.latitude,
                longitude=u.longitude,
                current_incident=u.current_incident,
            )
            for u in units
        ]
    finally:
        await adapter.disconnect()


@router.post("/{connection_id}/sync/start")
async def start_cad_sync(
    connection_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> dict:
    """Start CAD synchronization."""
    conn = _cad_connections.get(connection_id)
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CAD connection not found",
        )

    if connection_id in _sync_services:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sync already running",
        )

    try:
        vendor = CADVendor(conn["vendor"])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid vendor configuration",
        )

    adapter = create_adapter(vendor, conn["config"])
    sync_service = CADSyncService(db, adapter)

    async def start_sync():
        try:
            await sync_service.start_sync(conn["sync_interval_seconds"])
        except Exception:
            pass

    _sync_services[connection_id] = sync_service
    conn["sync_enabled"] = True
    background_tasks.add_task(start_sync)

    return {"message": "Sync started"}


@router.post("/{connection_id}/sync/stop")
async def stop_cad_sync(
    connection_id: str,
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
) -> dict:
    """Stop CAD synchronization."""
    if connection_id not in _cad_connections:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CAD connection not found",
        )

    if connection_id not in _sync_services:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sync not running",
        )

    await _sync_services[connection_id].stop_sync()
    del _sync_services[connection_id]
    _cad_connections[connection_id]["sync_enabled"] = False

    return {"message": "Sync stopped"}


@router.post("/{connection_id}/unit-status")
async def send_unit_status(
    connection_id: str,
    request: SyncStatusRequest,
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Send unit status update to CAD."""
    conn = _cad_connections.get(connection_id)
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CAD connection not found",
        )

    try:
        vendor = CADVendor(conn["vendor"])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid vendor configuration",
        )

    adapter = create_adapter(vendor, conn["config"])

    if not await adapter.connect():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to CAD system",
        )

    try:
        success = await adapter.send_unit_status(
            unit_id=request.unit_id,
            status=request.status,
            incident_id=request.incident_id,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update unit status in CAD",
            )

        return {"message": f"Unit {request.unit_id} status updated to {request.status}"}
    finally:
        await adapter.disconnect()


@router.post("/{connection_id}/incident-update")
async def send_incident_update(
    connection_id: str,
    request: SyncIncidentRequest,
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Send incident update to CAD."""
    conn = _cad_connections.get(connection_id)
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CAD connection not found",
        )

    try:
        vendor = CADVendor(conn["vendor"])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid vendor configuration",
        )

    adapter = create_adapter(vendor, conn["config"])

    if not await adapter.connect():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to CAD system",
        )

    try:
        success = await adapter.send_incident_update(
            incident_id=request.incident_id,
            status=request.status,
            comment=request.comment,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update incident in CAD",
            )

        return {"message": f"Incident {request.incident_id} updated"}
    finally:
        await adapter.disconnect()


@router.get("/vendors")
async def list_supported_vendors(
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """List supported CAD vendors."""
    vendors = {
        "generic": {
            "name": "Generic REST API",
            "description": "Custom REST API adapter with configurable field mapping",
            "required_fields": ["base_url"],
            "optional_fields": ["api_key", "username", "password", "field_mapping"],
        },
        "tritech": {
            "name": "TriTech/Hexagon CAD",
            "description": "TriTech InformCAD / Hexagon CAD integration",
            "required_fields": ["base_url", "client_id", "client_secret"],
            "optional_fields": [],
        },
        "motorola": {
            "name": "Motorola CommandCentral",
            "description": "Motorola Solutions CommandCentral CAD",
            "required_fields": ["base_url", "api_key"],
            "optional_fields": [],
            "status": "planned",
        },
        "tyler": {
            "name": "Tyler New World Systems",
            "description": "Tyler Technologies New World CAD",
            "required_fields": ["base_url", "username", "password"],
            "optional_fields": [],
            "status": "planned",
        },
        "intergraph": {
            "name": "Intergraph/Hexagon I/CAD",
            "description": "Hexagon Safety & Infrastructure I/CAD",
            "required_fields": ["base_url", "client_id", "client_secret"],
            "optional_fields": [],
            "status": "planned",
        },
        "mark43": {
            "name": "Mark43 CAD",
            "description": "Mark43 public safety software",
            "required_fields": ["base_url", "api_key"],
            "optional_fields": [],
            "status": "planned",
        },
        "central_square": {
            "name": "CentralSquare CAD",
            "description": "CentralSquare Technologies CAD",
            "required_fields": ["base_url", "api_key"],
            "optional_fields": [],
            "status": "planned",
        },
    }

    return {"vendors": vendors}
