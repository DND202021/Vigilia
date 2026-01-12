"""Socket.IO Server for Real-time Updates."""

import socketio
from typing import Any
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Create Socket.IO server with ASGI support
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",  # Allow all origins for Socket.IO
    logger=True,
    engineio_logger=True,
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
