"""Audit log model for tracking system events."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, ForeignKey, Enum as SQLEnum, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class AuditAction(str, Enum):
    """Types of auditable actions."""

    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGED = "password_changed"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"

    # User management
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_ROLE_CHANGED = "user_role_changed"

    # Incident management
    INCIDENT_CREATED = "incident_created"
    INCIDENT_UPDATED = "incident_updated"
    INCIDENT_ASSIGNED = "incident_assigned"
    INCIDENT_ESCALATED = "incident_escalated"
    INCIDENT_CLOSED = "incident_closed"

    # Alert management
    ALERT_RECEIVED = "alert_received"
    ALERT_ACKNOWLEDGED = "alert_acknowledged"
    ALERT_DISMISSED = "alert_dismissed"
    ALERT_TO_INCIDENT = "alert_to_incident"

    # Resource management
    RESOURCE_CREATED = "resource_created"
    RESOURCE_UPDATED = "resource_updated"
    RESOURCE_DELETED = "resource_deleted"
    RESOURCE_ASSIGNED = "resource_assigned"
    RESOURCE_STATUS_CHANGED = "resource_status_changed"

    # System events
    SYSTEM_CONFIG_CHANGED = "system_config_changed"
    API_ACCESS = "api_access"
    PERMISSION_DENIED = "permission_denied"


class AuditLog(Base):
    """Audit log for tracking all system events."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # When the action occurred
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # What action was performed
    action: Mapped[AuditAction] = mapped_column(
        SQLEnum(AuditAction, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )

    # Who performed the action (nullable for system events)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    user: Mapped["User | None"] = relationship("User")

    # What entity was affected
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # Additional context
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Request metadata
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Before/after state for changes (JSON for flexibility)
    old_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Additional metadata
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_timestamp_action", "timestamp", "action"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, timestamp={self.timestamp})>"
