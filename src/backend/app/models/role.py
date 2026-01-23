"""Role model for flexible role-based access control."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.user import User


class Role(Base, TimestampMixin, SoftDeleteMixin):
    """Role model for flexible RBAC."""

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Hierarchy level (lower = more privileges, 0 = system admin)
    hierarchy_level: Mapped[int] = mapped_column(Integer, default=50, nullable=False)

    # UI display
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # System roles cannot be deleted
    is_system_role: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Role status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Permissions stored as JSON array (uses JSONB on PostgreSQL, JSON on SQLite)
    # Example: ["incidents:read", "incidents:create", "resources:read"]
    permissions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Relationship to users
    users: Mapped[list["User"]] = relationship("User", back_populates="role_obj")

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name}, level={self.hierarchy_level})>"

    def has_permission(self, permission: str) -> bool:
        """Check if role has a specific permission."""
        # System admin has all permissions
        if "system:admin" in self.permissions:
            return True

        # Check for exact permission or wildcard
        if permission in self.permissions:
            return True

        # Check for wildcard permissions (e.g., "incidents:*" covers "incidents:read")
        parts = permission.split(":")
        if len(parts) == 2:
            wildcard = f"{parts[0]}:*"
            if wildcard in self.permissions:
                return True

        return False

    def can_manage_role(self, other_role: "Role") -> bool:
        """Check if this role can manage another role (based on hierarchy)."""
        # Can only manage roles at lower privilege level (higher number)
        return self.hierarchy_level < other_role.hierarchy_level


# Default system roles configuration
DEFAULT_ROLES = [
    {
        "name": "system_admin",
        "display_name": "System Administrator",
        "description": "Full system access with all permissions",
        "hierarchy_level": 0,
        "color": "red",
        "is_system_role": True,
        "permissions": ["system:admin"],
    },
    {
        "name": "agency_admin",
        "display_name": "Agency Administrator",
        "description": "Manage agency users, view all incidents and resources",
        "hierarchy_level": 10,
        "color": "purple",
        "is_system_role": True,
        "permissions": [
            "users:read",
            "users:create",
            "users:update",
            "users:manage_agency",
            "roles:read",
            "incidents:*",
            "resources:*",
            "alerts:*",
        ],
    },
    {
        "name": "commander",
        "display_name": "Commander",
        "description": "Incident command with full operational authority",
        "hierarchy_level": 20,
        "color": "blue",
        "is_system_role": True,
        "permissions": [
            "incidents:*",
            "resources:*",
            "alerts:*",
            "users:read",
        ],
    },
    {
        "name": "dispatcher",
        "display_name": "Dispatcher",
        "description": "Dispatch operations and alert management",
        "hierarchy_level": 30,
        "color": "green",
        "is_system_role": True,
        "permissions": [
            "incidents:read",
            "incidents:create",
            "incidents:update",
            "incidents:assign",
            "resources:read",
            "alerts:*",
        ],
    },
    {
        "name": "field_unit_leader",
        "display_name": "Field Unit Leader",
        "description": "Lead field operations and manage assigned resources",
        "hierarchy_level": 40,
        "color": "orange",
        "is_system_role": True,
        "permissions": [
            "incidents:read",
            "incidents:update",
            "resources:read",
            "resources:update",
            "alerts:read",
            "alerts:acknowledge",
        ],
    },
    {
        "name": "responder",
        "display_name": "Responder",
        "description": "Field responder with basic operational access",
        "hierarchy_level": 50,
        "color": "gray",
        "is_system_role": True,
        "permissions": [
            "incidents:read",
            "resources:read",
            "alerts:read",
        ],
    },
    {
        "name": "public_user",
        "display_name": "Public User",
        "description": "Limited public access for reporting",
        "hierarchy_level": 100,
        "color": "slate",
        "is_system_role": True,
        "permissions": [
            "incidents:report",
        ],
    },
]
