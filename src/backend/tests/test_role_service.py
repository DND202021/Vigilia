"""Tests for role service."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role
from app.services.role_service import RoleService, RoleError, AVAILABLE_PERMISSIONS


@pytest.fixture
def role_service(db_session: AsyncSession) -> RoleService:
    """Create a role service instance."""
    return RoleService(db_session)


@pytest.fixture
async def sample_role(db_session: AsyncSession) -> Role:
    """Create a sample role for testing."""
    role = Role(
        id=uuid.uuid4(),
        name="test_role",
        display_name="Test Role",
        description="A test role",
        hierarchy_level=50,
        color="blue",
        is_system_role=False,
        is_active=True,
        permissions=["incidents:read", "resources:read"],
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    return role


@pytest.fixture
async def system_role(db_session: AsyncSession) -> Role:
    """Create a system role for testing."""
    role = Role(
        id=uuid.uuid4(),
        name="system_test_role",
        display_name="System Test Role",
        description="A system test role",
        hierarchy_level=10,
        color="red",
        is_system_role=True,
        is_active=True,
        permissions=["system:admin"],
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    return role


class TestRoleService:
    """Test role service operations."""

    async def test_list_roles(
        self, role_service: RoleService, sample_role: Role
    ):
        """Test listing roles."""
        roles = await role_service.list_roles()
        assert len(roles) >= 1
        role_ids = [r.id for r in roles]
        assert sample_role.id in role_ids

    async def test_list_roles_exclude_inactive(
        self, role_service: RoleService, db_session: AsyncSession
    ):
        """Test listing roles excludes inactive by default."""
        inactive_role = Role(
            id=uuid.uuid4(),
            name="inactive_role",
            display_name="Inactive Role",
            hierarchy_level=50,
            is_active=False,
            permissions=[],
        )
        db_session.add(inactive_role)
        await db_session.commit()

        roles = await role_service.list_roles(include_inactive=False)
        role_ids = [r.id for r in roles]
        assert inactive_role.id not in role_ids

        roles_with_inactive = await role_service.list_roles(include_inactive=True)
        role_ids_with_inactive = [r.id for r in roles_with_inactive]
        assert inactive_role.id in role_ids_with_inactive

    async def test_get_role(
        self, role_service: RoleService, sample_role: Role
    ):
        """Test getting a role by ID."""
        role = await role_service.get_role(sample_role.id)
        assert role is not None
        assert role.id == sample_role.id
        assert role.name == "test_role"

    async def test_get_role_not_found(self, role_service: RoleService):
        """Test getting a non-existent role."""
        role = await role_service.get_role(uuid.uuid4())
        assert role is None

    async def test_get_role_by_name(
        self, role_service: RoleService, sample_role: Role
    ):
        """Test getting a role by name."""
        role = await role_service.get_role_by_name("test_role")
        assert role is not None
        assert role.id == sample_role.id

    async def test_create_role(self, role_service: RoleService):
        """Test creating a new role."""
        role = await role_service.create_role(
            name="new_role",
            display_name="New Role",
            description="A new role",
            hierarchy_level=60,
            color="green",
            permissions=["incidents:read"],
        )

        assert role.id is not None
        assert role.name == "new_role"
        assert role.display_name == "New Role"
        assert role.hierarchy_level == 60
        assert "incidents:read" in role.permissions

    async def test_create_role_duplicate_name(
        self, role_service: RoleService, sample_role: Role
    ):
        """Test creating a role with duplicate name fails."""
        with pytest.raises(RoleError, match="already exists"):
            await role_service.create_role(
                name="test_role",
                display_name="Another Test Role",
            )

    async def test_create_role_invalid_permission(self, role_service: RoleService):
        """Test creating a role with invalid permission fails."""
        with pytest.raises(RoleError, match="Invalid permission"):
            await role_service.create_role(
                name="invalid_perm_role",
                display_name="Invalid Perm Role",
                permissions=["invalid:permission"],
            )

    async def test_update_role(
        self, role_service: RoleService, sample_role: Role
    ):
        """Test updating a role."""
        updated = await role_service.update_role(
            role_id=sample_role.id,
            display_name="Updated Test Role",
            description="Updated description",
            color="purple",
        )

        assert updated.display_name == "Updated Test Role"
        assert updated.description == "Updated description"
        assert updated.color == "purple"

    async def test_update_role_not_found(self, role_service: RoleService):
        """Test updating a non-existent role fails."""
        with pytest.raises(RoleError, match="not found"):
            await role_service.update_role(
                role_id=uuid.uuid4(),
                display_name="Some Name",
            )

    async def test_update_system_role_restricted(
        self, role_service: RoleService, system_role: Role
    ):
        """Test updating system role has restrictions."""
        # Can update display_name
        updated = await role_service.update_role(
            role_id=system_role.id,
            display_name="Updated System Role",
        )
        assert updated.display_name == "Updated System Role"

        # Cannot update permissions
        with pytest.raises(RoleError, match="system roles"):
            await role_service.update_role(
                role_id=system_role.id,
                permissions=["incidents:read"],
            )

    async def test_delete_role(
        self, role_service: RoleService, sample_role: Role
    ):
        """Test soft deleting a role."""
        await role_service.delete_role(sample_role.id)

        # Role should not be found (soft deleted)
        role = await role_service.get_role(sample_role.id)
        assert role is None

    async def test_delete_role_not_found(self, role_service: RoleService):
        """Test deleting a non-existent role fails."""
        with pytest.raises(RoleError, match="not found"):
            await role_service.delete_role(uuid.uuid4())

    async def test_delete_system_role_fails(
        self, role_service: RoleService, system_role: Role
    ):
        """Test deleting a system role fails."""
        with pytest.raises(RoleError, match="system roles"):
            await role_service.delete_role(system_role.id)

    async def test_get_available_permissions(self, role_service: RoleService):
        """Test getting available permissions."""
        permissions = role_service.get_available_permissions()
        assert len(permissions) > 0
        assert all("key" in p for p in permissions)
        assert all("name" in p for p in permissions)
        assert all("description" in p for p in permissions)


class TestRoleModel:
    """Test Role model methods."""

    def test_has_permission_exact_match(self):
        """Test has_permission with exact match."""
        role = Role(
            name="test",
            display_name="Test",
            permissions=["incidents:read", "resources:read"],
        )
        assert role.has_permission("incidents:read") is True
        assert role.has_permission("incidents:create") is False

    def test_has_permission_system_admin(self):
        """Test has_permission for system admin."""
        role = Role(
            name="admin",
            display_name="Admin",
            permissions=["system:admin"],
        )
        assert role.has_permission("incidents:read") is True
        assert role.has_permission("anything:anything") is True

    def test_has_permission_wildcard(self):
        """Test has_permission with wildcard."""
        role = Role(
            name="test",
            display_name="Test",
            permissions=["incidents:*"],
        )
        assert role.has_permission("incidents:read") is True
        assert role.has_permission("incidents:create") is True
        assert role.has_permission("resources:read") is False

    def test_can_manage_role(self):
        """Test can_manage_role based on hierarchy."""
        admin_role = Role(
            name="admin",
            display_name="Admin",
            hierarchy_level=10,
            permissions=[],
        )
        user_role = Role(
            name="user",
            display_name="User",
            hierarchy_level=50,
            permissions=[],
        )

        assert admin_role.can_manage_role(user_role) is True
        assert user_role.can_manage_role(admin_role) is False
        assert user_role.can_manage_role(user_role) is False
