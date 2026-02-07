"""Socket.IO Server for Real-time Updates."""

import socketio
from datetime import datetime
from typing import Any
import structlog

from app.core.config import settings
from app.core.metrics import (
    increment_websocket_connections,
    decrement_websocket_connections,
    record_websocket_connect,
    record_websocket_disconnect,
)

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
    user_id = auth.get("user_id") if auth else None
    user_name = auth.get("user_name") if auth else None
    connected_clients[sid] = {
        "token": token,
        "user_id": user_id,
        "user_name": user_name,
        "rooms": set(),
        "current_floor_plan_id": None,
    }

    # Join default room for all authenticated users
    await sio.enter_room(sid, "authenticated")
    connected_clients[sid]["rooms"].add("authenticated")

    # Track connection metrics
    increment_websocket_connections()
    # Detect transport type from environ
    # Socket.IO sends HTTP_UPGRADE header for WebSocket, not for polling
    transport = "websocket" if environ.get("HTTP_UPGRADE", "").lower() == "websocket" else "polling"
    record_websocket_connect(transport)

    logger.info("Client connected", sid=sid, transport=transport)
    return True


@sio.event
async def disconnect(sid: str) -> None:
    """Handle client disconnection."""
    if sid in connected_clients:
        del connected_clients[sid]
    # Track disconnection metrics
    decrement_websocket_connections()
    record_websocket_disconnect("normal")
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


# Floor plan room management for real-time collaborative editing
@sio.event
async def join_floor_plan(sid, data):
    """Join a floor plan editing session."""
    floor_plan_id = data.get('floor_plan_id')
    if not floor_plan_id:
        return {'error': 'floor_plan_id required'}

    room = f"floor_plan:{floor_plan_id}"
    await sio.enter_room(sid, room)

    # Track the floor plan
    if sid in connected_clients:
        connected_clients[sid]['current_floor_plan_id'] = floor_plan_id

    logger.info(f"Client {sid} joined floor plan room {room}")
    return {'status': 'joined', 'room': room}


@sio.event
async def leave_floor_plan(sid, data):
    """Leave a floor plan editing session."""
    floor_plan_id = data.get('floor_plan_id')
    if not floor_plan_id:
        return {'error': 'floor_plan_id required'}

    room = f"floor_plan:{floor_plan_id}"
    await sio.leave_room(sid, room)

    # Clear tracking
    if sid in connected_clients:
        connected_clients[sid]['current_floor_plan_id'] = None

    logger.info(f"Client {sid} left floor plan room {room}")
    return {'status': 'left', 'room': room}


@sio.event
async def marker_added(sid, data):
    """Handle marker added by client - broadcast to floor plan room."""
    floor_plan_id = data.get('floor_plan_id')
    marker = data.get('marker')
    client_id = data.get('client_id')

    if not floor_plan_id or not marker:
        return {'error': 'floor_plan_id and marker required'}

    room = f"floor_plan:{floor_plan_id}"
    user_id = connected_clients.get(sid, {}).get('user_id')

    # Broadcast to all in room except sender
    await sio.emit('marker:added', {
        'floor_plan_id': floor_plan_id,
        'marker': marker,
        'user_id': user_id,
        'client_id': client_id,
        'timestamp': datetime.utcnow().isoformat(),
    }, room=room, skip_sid=sid)

    return {'status': 'broadcast'}


@sio.event
async def marker_updated(sid, data):
    """Handle marker updated by client - broadcast to floor plan room."""
    floor_plan_id = data.get('floor_plan_id')
    marker_id = data.get('marker_id')
    updates = data.get('updates')
    client_id = data.get('client_id')

    if not floor_plan_id or not marker_id:
        return {'error': 'floor_plan_id and marker_id required'}

    room = f"floor_plan:{floor_plan_id}"
    user_id = connected_clients.get(sid, {}).get('user_id')

    await sio.emit('marker:updated', {
        'floor_plan_id': floor_plan_id,
        'marker_id': marker_id,
        'updates': updates,
        'user_id': user_id,
        'client_id': client_id,
        'timestamp': datetime.utcnow().isoformat(),
    }, room=room, skip_sid=sid)

    return {'status': 'broadcast'}


@sio.event
async def marker_deleted(sid, data):
    """Handle marker deleted by client - broadcast to floor plan room."""
    floor_plan_id = data.get('floor_plan_id')
    marker_id = data.get('marker_id')

    if not floor_plan_id or not marker_id:
        return {'error': 'floor_plan_id and marker_id required'}

    room = f"floor_plan:{floor_plan_id}"
    user_id = connected_clients.get(sid, {}).get('user_id')

    await sio.emit('marker:deleted', {
        'floor_plan_id': floor_plan_id,
        'marker_id': marker_id,
        'user_id': user_id,
        'timestamp': datetime.utcnow().isoformat(),
    }, room=room, skip_sid=sid)

    return {'status': 'broadcast'}


@sio.event
async def presence_editing(sid, data):
    """Handle presence heartbeat / editing status update."""
    floor_plan_id = data.get('floor_plan_id')
    is_editing = data.get('is_editing', False)

    if not floor_plan_id:
        return {'error': 'floor_plan_id required'}

    room = f"floor_plan:{floor_plan_id}"
    client_data = connected_clients.get(sid, {})
    user_id = client_data.get('user_id')
    user_name = client_data.get('user_name', 'Unknown')

    await sio.emit('presence:editing', {
        'floor_plan_id': floor_plan_id,
        'user_id': user_id,
        'user_name': user_name,
        'is_editing': is_editing,
        'timestamp': datetime.utcnow().isoformat(),
    }, room=room, skip_sid=sid)

    return {'status': 'broadcast'}


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


async def emit_markers_updated(floor_plan_id: str, building_id: str) -> None:
    """Emit markers updated event to building-specific room.

    This event notifies clients that markers on a floor plan have been updated,
    allowing other users viewing the same floor plan to refresh their markers.
    """
    try:
        data = {
            "floor_plan_id": floor_plan_id,
            "building_id": building_id,
        }
        await sio.emit("markers:updated", data, room=f"building:{building_id}")
        logger.info("Emitted markers:updated", building_id=building_id, floor_plan_id=floor_plan_id)
    except Exception as e:
        logger.error("Failed to emit markers:updated", building_id=building_id, floor_plan_id=floor_plan_id, error=str(e))


# Sprint 7: Real-time Floor Plan Emit Functions

async def emit_marker_added(floor_plan_id: str, marker: dict, user_id: str = None, client_id: str = None):
    """Emit marker added event to floor plan room."""
    room = f"floor_plan:{floor_plan_id}"
    await sio.emit('marker:added', {
        'floor_plan_id': floor_plan_id,
        'marker': marker,
        'user_id': user_id,
        'client_id': client_id,
        'timestamp': datetime.utcnow().isoformat(),
    }, room=room)
    logger.debug(f"Emitted marker:added to room {room}")


async def emit_marker_updated(floor_plan_id: str, marker_id: str, updates: dict, user_id: str = None, client_id: str = None):
    """Emit marker updated event to floor plan room."""
    room = f"floor_plan:{floor_plan_id}"
    await sio.emit('marker:updated', {
        'floor_plan_id': floor_plan_id,
        'marker_id': marker_id,
        'updates': updates,
        'user_id': user_id,
        'client_id': client_id,
        'timestamp': datetime.utcnow().isoformat(),
    }, room=room)
    logger.debug(f"Emitted marker:updated to room {room}")


async def emit_marker_deleted(floor_plan_id: str, marker_id: str, user_id: str = None):
    """Emit marker deleted event to floor plan room."""
    room = f"floor_plan:{floor_plan_id}"
    await sio.emit('marker:deleted', {
        'floor_plan_id': floor_plan_id,
        'marker_id': marker_id,
        'user_id': user_id,
        'timestamp': datetime.utcnow().isoformat(),
    }, room=room)
    logger.debug(f"Emitted marker:deleted to room {room}")


async def emit_presence_joined(floor_plan_id: str, user_data: dict):
    """Emit user joined floor plan event."""
    room = f"floor_plan:{floor_plan_id}"
    await sio.emit('presence:joined_floor_plan', {
        'floor_plan_id': floor_plan_id,
        'user_id': user_data.get('user_id'),
        'user_name': user_data.get('user_name'),
        'user_role': user_data.get('user_role'),
        'timestamp': datetime.utcnow().isoformat(),
    }, room=room)
    logger.debug(f"Emitted presence:joined_floor_plan to room {room}")


async def emit_presence_left(floor_plan_id: str, user_id: str):
    """Emit user left floor plan event."""
    room = f"floor_plan:{floor_plan_id}"
    await sio.emit('presence:left_floor_plan', {
        'floor_plan_id': floor_plan_id,
        'user_id': user_id,
        'timestamp': datetime.utcnow().isoformat(),
    }, room=room)
    logger.debug(f"Emitted presence:left_floor_plan to room {room}")


async def emit_presence_list(floor_plan_id: str, active_users: list):
    """Emit list of active users on floor plan."""
    room = f"floor_plan:{floor_plan_id}"
    await sio.emit('presence:list', {
        'floor_plan_id': floor_plan_id,
        'active_users': active_users,
        'timestamp': datetime.utcnow().isoformat(),
    }, room=room)
    logger.debug(f"Emitted presence:list to room {room} with {len(active_users)} users")


async def emit_device_position_updated(floor_plan_id: str, device_data: dict):
    """Emit device position updated on floor plan."""
    room = f"floor_plan:{floor_plan_id}"
    await sio.emit('device:position_updated', {
        'floor_plan_id': floor_plan_id,
        'device_id': device_data.get('device_id'),
        'position_x': device_data.get('position_x'),
        'position_y': device_data.get('position_y'),
        'timestamp': datetime.utcnow().isoformat(),
    }, room=room)
    logger.debug(f"Emitted device:position_updated to room {room}")


# Communication Hub - Channel Room Handlers

@sio.event
async def join_channel(sid: str, channel_id: str) -> dict:
    """Join a channel room for real-time messaging."""
    room = f"channel:{channel_id}"
    await sio.enter_room(sid, room)
    if sid in connected_clients:
        connected_clients[sid]["rooms"].add(room)
    logger.info("Client joined channel room", sid=sid, channel_id=channel_id)
    return {"status": "joined", "channel_id": channel_id}


@sio.event
async def leave_channel(sid: str, channel_id: str) -> dict:
    """Leave a channel room."""
    room = f"channel:{channel_id}"
    await sio.leave_room(sid, room)
    if sid in connected_clients:
        connected_clients[sid]["rooms"].discard(room)
    logger.info("Client left channel room", sid=sid, channel_id=channel_id)
    return {"status": "left", "channel_id": channel_id}


@sio.event
async def typing_start(sid: str, data: dict) -> None:
    """Handle user started typing in a channel."""
    channel_id = data.get("channel_id")
    if not channel_id:
        return

    room = f"channel:{channel_id}"
    client_data = connected_clients.get(sid, {})
    user_id = client_data.get("user_id")
    user_name = client_data.get("user_name", "Unknown")

    await sio.emit("typing:start", {
        "channel_id": channel_id,
        "user_id": user_id,
        "user_name": user_name,
        "timestamp": datetime.utcnow().isoformat(),
    }, room=room, skip_sid=sid)


@sio.event
async def typing_stop(sid: str, data: dict) -> None:
    """Handle user stopped typing in a channel."""
    channel_id = data.get("channel_id")
    if not channel_id:
        return

    room = f"channel:{channel_id}"
    client_data = connected_clients.get(sid, {})
    user_id = client_data.get("user_id")

    await sio.emit("typing:stop", {
        "channel_id": channel_id,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat(),
    }, room=room, skip_sid=sid)


# Communication Hub Emit Functions

async def emit_message_new(channel_id: str, message: dict) -> None:
    """Emit new message to channel room."""
    room = f"channel:{channel_id}"
    await sio.emit("message:new", {
        "channel_id": channel_id,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }, room=room)
    logger.debug(f"Emitted message:new to room {room}")


async def emit_message_edited(channel_id: str, message_id: str, content: str, edited_at: str) -> None:
    """Emit message edited event to channel room."""
    room = f"channel:{channel_id}"
    await sio.emit("message:edited", {
        "channel_id": channel_id,
        "message_id": message_id,
        "content": content,
        "edited_at": edited_at,
        "timestamp": datetime.utcnow().isoformat(),
    }, room=room)
    logger.debug(f"Emitted message:edited to room {room}")


async def emit_message_deleted(channel_id: str, message_id: str) -> None:
    """Emit message deleted event to channel room."""
    room = f"channel:{channel_id}"
    await sio.emit("message:deleted", {
        "channel_id": channel_id,
        "message_id": message_id,
        "timestamp": datetime.utcnow().isoformat(),
    }, room=room)
    logger.debug(f"Emitted message:deleted to room {room}")


async def emit_channel_created(user_ids: list[str], channel: dict) -> None:
    """Emit channel created event to specific users."""
    for user_id in user_ids:
        # Find all sids for this user
        for sid, client_data in connected_clients.items():
            if client_data.get("user_id") == user_id:
                await sio.emit("channel:created", channel, to=sid)
    logger.debug(f"Emitted channel:created to {len(user_ids)} users")


async def emit_channel_updated(channel_id: str, channel: dict) -> None:
    """Emit channel updated event to channel room."""
    room = f"channel:{channel_id}"
    await sio.emit("channel:updated", channel, room=room)
    logger.debug(f"Emitted channel:updated to room {room}")


async def emit_member_joined(channel_id: str, member: dict) -> None:
    """Emit member joined event to channel room."""
    room = f"channel:{channel_id}"
    await sio.emit("member:joined", {
        "channel_id": channel_id,
        "member": member,
        "timestamp": datetime.utcnow().isoformat(),
    }, room=room)
    logger.debug(f"Emitted member:joined to room {room}")


async def emit_member_left(channel_id: str, user_id: str) -> None:
    """Emit member left event to channel room."""
    room = f"channel:{channel_id}"
    await sio.emit("member:left", {
        "channel_id": channel_id,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat(),
    }, room=room)
    logger.debug(f"Emitted member:left to room {room}")


# Device Twin - Room Handlers

@sio.event
async def join_device(sid: str, device_id: str) -> dict:
    """Join a device room for real-time config updates."""
    room = f"device:{device_id}"
    await sio.enter_room(sid, room)
    if sid in connected_clients:
        connected_clients[sid]["rooms"].add(room)
    logger.info("Client joined device room", sid=sid, device_id=device_id)
    return {"status": "joined", "device_id": device_id}


@sio.event
async def leave_device(sid: str, device_id: str) -> dict:
    """Leave a device room."""
    room = f"device:{device_id}"
    await sio.leave_room(sid, room)
    if sid in connected_clients:
        connected_clients[sid]["rooms"].discard(room)
    logger.info("Client left device room", sid=sid, device_id=device_id)
    return {"status": "left", "device_id": device_id}


# Device Twin - Emit Functions

async def emit_device_config_updated(
    device_id: str,
    desired_config: dict | None = None,
    reported_config: dict | None = None,
    desired_version: int | None = None,
    reported_version: int | None = None,
    is_synced: bool = False,
) -> None:
    """Emit device config updated event to authenticated users and device room."""
    payload = {
        "device_id": device_id,
        "is_synced": is_synced,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if desired_config is not None:
        payload["desired_config"] = desired_config
        payload["desired_version"] = desired_version

    if reported_config is not None:
        payload["reported_config"] = reported_config
        payload["reported_version"] = reported_version

    await sio.emit("device:config:updated", payload, room="authenticated")
    await sio.emit("device:config:updated", payload, room=f"device:{device_id}")

    logger.debug(
        "Emitted device:config:updated",
        device_id=device_id,
        is_synced=is_synced,
    )


async def emit_device_config_synced(
    device_id: str,
    config: dict,
    synced_at: str,
) -> None:
    """Emit device config synced event when device transitions to synced state."""
    payload = {
        "device_id": device_id,
        "config": config,
        "synced_at": synced_at,
        "timestamp": datetime.utcnow().isoformat(),
    }

    await sio.emit("device:config:synced", payload, room="authenticated")
    await sio.emit("device:config:synced", payload, room=f"device:{device_id}")

    logger.info(
        "Emitted device:config:synced",
        device_id=device_id,
    )
