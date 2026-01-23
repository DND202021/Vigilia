"""Role service for role management operations."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role, DEFAULT_ROLES


class RoleError(Exception):
    """Role-related errors."""

    pass


# All available permissions in the system
AVAILABLE_PERMISSIONS = [
    # System
    {"key": "system:admin", "name": "System Administrator", "description": "Full system access"},
    # Users
    {"key": "users:read", "name": "View Users", "description": "View user profiles"},
    {"key": "users:create", "name": "Create Users", "description": "Create new users"},
    {"key": "users:update", "name": "Update Users", "description": "Update user profiles"},
    {"key": "users:delete", "name": "Delete Users", "description": "Delete users"},
    {"key": "users:manage_agency", "name": "Manage Agency Users", "description": "Manage users within agency"},
    # Roles
    {"key": "roles:read", "name": "View Roles", "description": "View roles"},
    {"key": "roles:create", "name": "Create Roles", "description": "Create new roles"},
    {"key": "roles:update", "name": "Update Roles", "description": "Update roles"},
    {"key": "roles:delete", "name": "Delete Roles", "description": "Delete roles"},
    # Incidents
    {"key": "incidents:read", "name": "View Incidents", "description": "View incidents"},
    {"key": "incidents:create", "name": "Create Incidents", "description": "Create new incidents"},
    {"key": "incidents:update", "name": "Update Incidents", "description": "Update incidents"},
    {"key": "incidents:delete", "name": "Delete Incidents", "description": "Delete incidents"},
    {"key": "incidents:assign", "name": "Assign Incidents", "description": "Assign units to incidents"},
    {"key": "incidents:report", "name": "Report Incidents", "description": "Submit incident reports"},
    {"key": "incidents:*", "name": "All Incident Permissions", "description": "Full incident access"},
    # Resources
    {"key": "resources:read", "name": "View Resources", "description": "View resources"},
    {"key": "resources:create", "name": "Create Resources", "description": "Create new resources"},
    {"key": "resources:update", "name": "Update Resources", "description": "Update resources"},
    {"key": "resources:delete", "name": "Delete Resources", "description": "Delete resources"},
    {"key": "resources:*", "name": "All Resource Permissions", "description": "Full resource access"},
    # Alerts
    {"key": "alerts:read", "name": "View Alerts", "description": "View alerts"},
    {"key": "alerts:acknowledge", "name": "Acknowledge Alerts", "description": "Acknowledge alerts"},
    {"key": "alerts:resolve", "name": "Resolve Alerts", "description": "Resolve alerts"},
    {"key": "alerts:*", "name": "All Alert Permissions", "description": "Full alert access"},
]


class RoleService:
    """Service for role management operations."""

    def __init__(self, db: AsyncSession):
        """Initialize role service with database session."""
        self.db = db

    async def list_roles(
        self,
        include_inactive: bool = False,
        include_deleted: bool = False,
    ) -> list[Role]:
        """List all roles with optional filtering."""
        conditions = []

        if not include_inactive:
            conditions.append(Role.is_active == True)

        if not include_deleted:
            conditions.append(Role.deleted_at == None)

        query = select(Role)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(Role.hierarchy_level, Role.name)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_role(self, role_id: uuid.UUID) -> Role | None:
        """Get a role by ID."""
        result = await self.db.execute(
            select(Role).where(
                and_(Role.id == role_id, Role.deleted_at == None)
            )
        )
        return result.scalar_one_or_none()

    async def get_role_by_name(self, name: str) -> Role | None:
        """Get a role by name."""
        result = await self.db.execute(
            select(Role).where(
                and_(Role.name == name, Role.deleted_at == None)
            )
        )
        return result.scalar_one_or_none()

    async def create_role(
        self,
        name: str,
        display_name: str,
        description: str | None = None,
        hierarchy_level: int = 50,
        color: str | None = None,
        permissions: list[str] | None = None,
        is_system_role: bool = False,
    ) -> Role:
        """Create a new role."""
        # Check for duplicate name
        existing = await self.get_role_by_name(name)
        if existing:
            raise RoleError(f"Role with name '{name}' already exists")

        # Validate permissions
        if permissions:
            self._validate_permissions(permissions)

        role = Role(
            name=name.lower().replace(" ", "_"),
            display_name=display_name,
            description=description,
            hierarchy_level=hierarchy_level,
            color=color,
            permissions=permissions or [],
            is_system_role=is_system_role,
        )

        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)

        return role

    async def update_role(
        self,
        role_id: uuid.UUID,
        display_name: str | None = None,
        description: str | None = None,
        hierarchy_level: int | None = None,
        color: str | None = None,
        permissions: list[str] | None = None,
        is_active: bool | None = None,
    ) -> Role:
        """Update an existing role."""
        role = await self.get_role(role_id)
        if not role:
            raise RoleError("Role not found")

        # System roles have limited editability
        if role.is_system_role:
            # Can only update display_name, description, and color for system roles
            if hierarchy_level is not None or permissions is not None:
                raise RoleError("Cannot modify hierarchy or permissions of system roles")

        if display_name is not None:
            role.display_name = display_name

        if description is not None:
            role.description = description

        if hierarchy_level is not None:
            role.hierarchy_level = hierarchy_level

        if color is not None:
            role.color = color

        if permissions is not None:
            self._validate_permissions(permissions)
            role.permissions = permissions

        if is_active is not None:
            role.is_active = is_active

        await self.db.commit()
        await self.db.refresh(role)

        return role

    async def delete_role(self, role_id: uuid.UUID) -> None:
        """Soft delete a role."""
        role = await self.get_role(role_id)
        if not role:
            raise RoleError("Role not found")

        if role.is_system_role:
            raise RoleError("Cannot delete system roles")

        # Check if any users are assigned to this role
        from app.models.user import User
        result = await self.db.execute(
            select(User).where(
                and_(User.role_id == role_id, User.deleted_at == None)
            ).limit(1)
        )
        if result.scalar_one_or_none():
            raise RoleError("Cannot delete role with assigned users")

        role.deleted_at = datetime.now(timezone.utc)
        await self.db.commit()

    def get_available_permissions(self) -> list[dict]:
        """Get list of all available permissions."""
        return AVAILABLE_PERMISSIONS

    def _validate_permissions(self, permissions: list[str]) -> None:
        """Validate that all permissions are valid."""
        valid_keys = {p["key"] for p in AVAILABLE_PERMISSIONS}
        for perm in permissions:
            if perm not in valid_keys:
                raise RoleError(f"Invalid permission: {perm}")

    async def seed_default_roles(self) -> None:
        """Seed default system roles if they don't exist."""
        for role_data in DEFAULT_ROLES:
            existing = await self.get_role_by_name(role_data["name"])
            if not existing:
                await self.create_role(
                    name=role_data["name"],
                    display_name=role_data["display_name"],
                    description=role_data["description"],
                    hierarchy_level=role_data["hierarchy_level"],
                    color=role_data["color"],
                    permissions=role_data["permissions"],
                    is_system_role=True,
                )
