"""Socket.IO Server for Real-time Updates."""

import socketio
from typing import Any
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Use Redis client manager for multi-worker support (gunicorn with multiple workers)
# This allows Socket.IO sessions to be shared across all workers
_client_manager = None
if settings.redis_url:
    try:
        _client_manager = socketio.AsyncRedisManager(settings.redis_url)
        logger.info("Socket.IO using Redis client manager for multi-worker support")
    except Exception as e:
        logger.warning("Failed to create Redis client manager, falling back to in-memory", error=str(e))

# Create Socket.IO server with ASGI support
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",  # Allow all origins for Socket.IO
    client_manager=_client_manager,
    logger=False,
    engineio_logger=False,
)

# socket_app will be set after FastAPI app is created
socket_app = None


def create_combined_app(fastapi_app: Any) -> Any:
    """Wrap FastAPI app with Socket.IO ASGI app."""
    return socketio.ASGIApp(sio, other_asgi_app=fastapi_app)

# Store connected clients with their user info
connected_clients: dict[str, dict[str, Any]] = {}


@sio.event
async def connect(sid: str, environ: dict[str, Any], auth: dict[str, Any] | None = None) -> bool:
    """Handle client connection."""
    logger.info("Client connecting", sid=sid, auth=auth)

    # Validate auth token if provided
    token = auth.get("token") if auth else None
    if not token:
        logger.warning("Client connection rejected: no token", sid=sid)
        return False

    # TODO: Validate JWT token and extract user info
    # For now, accept all connections with a token
    connected_clients[sid] = {
        "token": token,
        "rooms": set(),
    }

    # Join default room for all authenticated users
    await sio.enter_room(sid, "authenticated")
    connected_clients[sid]["rooms"].add("authenticated")

    logger.info("Client connected", sid=sid)
    return True


@sio.event
async def disconnect(sid: str) -> None:
    """Handle client disconnection."""
    if sid in connected_clients:
        del connected_clients[sid]
    logger.info("Client disconnected", sid=sid)


@sio.event
async def join_incident(sid: str, incident_id: str) -> None:
    """Join a specific incident room for updates."""
    room = f"incident:{incident_id}"
    await sio.enter_room(sid, room)
    if sid in connected_clients:
        connected_clients[sid]["rooms"].add(room)
    logger.info("Client joined incident room", sid=sid, incident_id=incident_id)


@sio.event
async def leave_incident(sid: str, incident_id: str) -> None:
    """Leave a specific incident room."""
    room = f"incident:{incident_id}"
    await sio.leave_room(sid, room)
    if sid in connected_clients:
        connected_clients[sid]["rooms"].discard(room)
    logger.info("Client left incident room", sid=sid, incident_id=incident_id)


# Emit functions for use by other parts of the application
async def emit_incident_created(incident: dict[str, Any]) -> None:
    """Emit incident created event to all authenticated users."""
    await sio.emit("incident:created", incident, room="authenticated")
    logger.info("Emitted incident:created", incident_id=incident.get("id"))


async def emit_incident_updated(incident: dict[str, Any]) -> None:
    """Emit incident updated event."""
    incident_id = incident.get("id")
    # Emit to all authenticated users and to incident-specific room
    await sio.emit("incident:updated", incident, room="authenticated")
    await sio.emit("incident:updated", incident, room=f"incident:{incident_id}")
    logger.info("Emitted incident:updated", incident_id=incident_id)


async def emit_alert_created(alert: dict[str, Any]) -> None:
    """Emit alert created event to all authenticated users."""
    await sio.emit("alert:created", alert, room="authenticated")
    logger.info("Emitted alert:created", alert_id=alert.get("id"))


async def emit_alert_updated(alert: dict[str, Any]) -> None:
    """Emit alert updated event to all authenticated users."""
    await sio.emit("alert:updated", alert, room="authenticated")
    logger.info("Emitted alert:updated", alert_id=alert.get("id"))


async def emit_resource_updated(resource: dict[str, Any]) -> None:
    """Emit resource updated event to all authenticated users."""
    await sio.emit("resource:updated", resource, room="authenticated")
    logger.info("Emitted resource:updated", resource_id=resource.get("id"))


async def emit_device_status(device_data: dict[str, Any]) -> None:
    """Emit device status change to all authenticated users."""
    await sio.emit("device:status", device_data, room="authenticated")
    logger.info("Emitted device:status", device_id=device_data.get("device_id"))


async def emit_device_alert(device_alert: dict[str, Any]) -> None:
    """Emit device alert event to all authenticated users."""
    await sio.emit("device:alert", device_alert, room="authenticated")
    logger.info("Emitted device:alert", device_id=device_alert.get("device_id"))


# Building-specific rooms for targeted alert delivery
@sio.event
async def join_building(sid: str, building_id: str) -> None:
    """Join a building room to receive building-specific alerts."""
    room = f"building:{building_id}"
    await sio.enter_room(sid, room)
    if sid in connected_clients:
        connected_clients[sid]["rooms"].add(room)
    logger.info("Client joined building room", sid=sid, building_id=building_id)


@sio.event
async def leave_building(sid: str, building_id: str) -> None:
    """Leave a building room."""
    room = f"building:{building_id}"
    await sio.leave_room(sid, room)
    if sid in connected_clients:
        connected_clients[sid]["rooms"].discard(room)
    logger.info("Client left building room", sid=sid, building_id=building_id)


# Building emit functions for real-time building updates
async def emit_building_created(building: dict) -> None:
    """Emit building created event to all authenticated users."""
    try:
        await sio.emit("building:created", building, room="authenticated")
        logger.info("Emitted building:created", building_id=building.get("id"))
    except Exception as e:
        logger.error("Failed to emit building:created", building_id=building.get("id"), error=str(e))


async def emit_building_updated(building: dict, building_id: str) -> None:
    """Emit building updated event to authenticated users and building-specific room."""
    try:
        await sio.emit("building:updated", building, room="authenticated")
        await sio.emit("building:updated", building, room=f"building:{building_id}")
        logger.info("Emitted building:updated", building_id=building_id)
    except Exception as e:
        logger.error("Failed to emit building:updated", building_id=building_id, error=str(e))


async def emit_floor_plan_uploaded(floor_plan: dict, building_id: str) -> None:
    """Emit floor plan uploaded event to building-specific room."""
    try:
        await sio.emit("floor_plan:uploaded", floor_plan, room=f"building:{building_id}")
        logger.info("Emitted floor_plan:uploaded", building_id=building_id, floor_plan_id=floor_plan.get("id"))
    except Exception as e:
        logger.error("Failed to emit floor_plan:uploaded", building_id=building_id, floor_plan_id=floor_plan.get("id"), error=str(e))


async def emit_floor_plan_updated(floor_plan: dict, building_id: str) -> None:
    """Emit floor plan updated event to building-specific room."""
    try:
        await sio.emit("floor_plan:updated", floor_plan, room=f"building:{building_id}")
        logger.info("Emitted floor_plan:updated", building_id=building_id, floor_plan_id=floor_plan.get("id"))
    except Exception as e:
        logger.error("Failed to emit floor_plan:updated", building_id=building_id, floor_plan_id=floor_plan.get("id"), error=str(e))
