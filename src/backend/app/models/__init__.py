"""ERIOP Database Models."""

from app.models.base import Base, TimestampMixin
from app.models.role import Role, DEFAULT_ROLES
from app.models.user import User, UserRole
from app.models.agency import Agency
from app.models.incident import Incident, IncidentStatus, IncidentPriority, IncidentCategory
from app.models.resource import Resource, ResourceType, ResourceStatus, Personnel, Vehicle, Equipment
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertSource
from app.models.audit import AuditLog, AuditAction
from app.models.building import (
    Building,
    BuildingType,
    OccupancyType,
    ConstructionType,
    HazardLevel,
    FloorPlan,
)
from app.models.inspection import Inspection, InspectionType, InspectionStatus
from app.models.photo import BuildingPhoto
from app.models.device import IoTDevice, DeviceType, DeviceStatus
from app.models.device_status_history import DeviceStatusHistory
from app.models.audio_clip import AudioClip
from app.models.notification_preference import NotificationPreference
from app.models.document import BuildingDocument, DocumentCategory
from app.models.emergency_procedure import EmergencyProcedure, ProcedureType
from app.models.evacuation_route import EvacuationRoute, RouteType
from app.models.emergency_checkpoint import EmergencyCheckpoint, CheckpointType

__all__ = [
    "Base",
    "TimestampMixin",
    "Role",
    "DEFAULT_ROLES",
    "User",
    "UserRole",
    "Agency",
    "Incident",
    "IncidentStatus",
    "IncidentPriority",
    "IncidentCategory",
    "Resource",
    "ResourceType",
    "ResourceStatus",
    "Personnel",
    "Vehicle",
    "Equipment",
    "Alert",
    "AlertSeverity",
    "AlertStatus",
    "AlertSource",
    "AuditLog",
    "AuditAction",
    "Building",
    "BuildingType",
    "OccupancyType",
    "ConstructionType",
    "HazardLevel",
    "FloorPlan",
    "Inspection",
    "InspectionType",
    "InspectionStatus",
    "BuildingPhoto",
    "IoTDevice",
    "DeviceType",
    "DeviceStatus",
    "DeviceStatusHistory",
    "AudioClip",
    "NotificationPreference",
    "BuildingDocument",
    "DocumentCategory",
    "EmergencyProcedure",
    "ProcedureType",
    "EvacuationRoute",
    "RouteType",
    "EmergencyCheckpoint",
    "CheckpointType",
]
