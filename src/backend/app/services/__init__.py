"""ERIOP Services Module."""

from app.services.auth_service import AuthService, AuthenticationError
from app.services.incident_service import IncidentService, IncidentError
from app.services.resource_service import ResourceService, ResourceError
from app.services.alert_service import AlertService, AlertError
from app.services.socketio import (
    sio,
    create_combined_app,
    emit_incident_created,
    emit_incident_updated,
    emit_alert_created,
    emit_alert_updated,
    emit_resource_updated,
)
from app.services.role_service import RoleService, RoleError, AVAILABLE_PERMISSIONS
from app.services.user_service import UserService, UserError

__all__ = [
    "AuthService",
    "AuthenticationError",
    "IncidentService",
    "IncidentError",
    "ResourceService",
    "ResourceError",
    "AlertService",
    "AlertError",
    "sio",
    "create_combined_app",
    "emit_incident_created",
    "emit_incident_updated",
    "emit_alert_created",
    "emit_alert_updated",
    "emit_resource_updated",
    "RoleService",
    "RoleError",
    "AVAILABLE_PERMISSIONS",
    "UserService",
    "UserError",
]
