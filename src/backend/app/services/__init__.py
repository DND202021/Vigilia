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
    emit_building_created,
    emit_building_updated,
    emit_floor_plan_uploaded,
    emit_floor_plan_updated,
    emit_markers_updated,
)
from app.services.role_service import RoleService, RoleError, AVAILABLE_PERMISSIONS
from app.services.user_service import UserService, UserError
from app.services.file_storage import FileStorageService, FileStorageError, get_file_storage
from app.services.device_service import DeviceService, DeviceError
from app.services.audio_storage_service import AudioStorageService, AudioStorageError
from app.services.notification_service import NotificationService
from app.services.bim_parser import (
    IFCParser,
    IFCParserError,
    BIMData,
    BIMFloorInfo,
    BIMKeyLocation,
)
from app.services.building_analytics_service import BuildingAnalyticsService, BuildingAnalyticsError
from app.services.channel_service import ChannelService
from app.services.message_service import MessageService

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
    "emit_building_created",
    "emit_building_updated",
    "emit_floor_plan_uploaded",
    "emit_floor_plan_updated",
    "emit_markers_updated",
    "RoleService",
    "RoleError",
    "AVAILABLE_PERMISSIONS",
    "UserService",
    "UserError",
    "FileStorageService",
    "FileStorageError",
    "get_file_storage",
    "DeviceService",
    "DeviceError",
    "AudioStorageService",
    "AudioStorageError",
    "NotificationService",
    "IFCParser",
    "IFCParserError",
    "BIMData",
    "BIMFloorInfo",
    "BIMKeyLocation",
    "BuildingAnalyticsService",
    "BuildingAnalyticsError",
    "ChannelService",
    "MessageService",
]
