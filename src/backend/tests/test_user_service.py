"""Tests for user service."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.role import Role
from app.services.user_service import UserService, UserError


@pytest.fixture
def user_service(db_session: AsyncSession) -> UserService:
    """Create a user service instance."""
    return UserService(db_session)


@pytest.fixture
async def sample_role(db_session: AsyncSession) -> Role:
    """Create a sample role for testing."""
    role = Role(
        id=uuid.uuid4(),
        name="responder",
        display_name="Responder",
        hierarchy_level=50,
        permissions=["incidents:read"],
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    return role


@pytest.fixture
async def sample_user(db_session: AsyncSession, sample_role: Role) -> User:
    """Create a sample user for testing."""
    from app.core.security import get_password_hash

    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password=get_password_hash("TestPassword123!"),
        full_name="Test User",
        role=UserRole.RESPONDER,
        role_id=sample_role.id,
        badge_number="12345",
        is_active=True,
        is_verified=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestUserService:
    """Test user service operations."""

    async def test_list_users(
        self, user_service: UserService, sample_user: User
    ):
        """Test listing users."""
        users, total = await user_service.list_users()
        assert total >= 1
        user_ids = [u.id for u in users]
        assert sample_user.id in user_ids

    async def test_list_users_with_search(
        self, user_service: UserService, sample_user: User
    ):
        """Test listing users with search filter."""
        users, total = await user_service.list_users(search="test@example")
        assert total >= 1
        user_ids = [u.id for u in users]
        assert sample_user.id in user_ids

        users, total = await user_service.list_users(search="nonexistent@example")
        assert total == 0

    async def test_list_users_with_role_filter(
        self, user_service: UserService, sample_user: User, sample_role: Role
    ):
        """Test listing users with role filter."""
        users, total = await user_service.list_users(role_id=sample_role.id)
        assert total >= 1
        user_ids = [u.id for u in users]
        assert sample_user.id in user_ids

    async def test_list_users_with_active_filter(
        self, user_service: UserService, sample_user: User
    ):
        """Test listing users with active status filter."""
        users, total = await user_service.list_users(is_active=True)
        assert total >= 1
        user_ids = [u.id for u in users]
        assert sample_user.id in user_ids

        users, total = await user_service.list_users(is_active=False)
        assert sample_user.id not in [u.id for u in users]

    async def test_get_user(
        self, user_service: UserService, sample_user: User
    ):
        """Test getting a user by ID."""
        user = await user_service.get_user(sample_user.id)
        assert user is not None
        assert user.id == sample_user.id
        assert user.email == "test@example.com"

    async def test_get_user_not_found(self, user_service: UserService):
        """Test getting a non-existent user."""
        user = await user_service.get_user(uuid.uuid4())
        assert user is None

    async def test_get_user_by_email(
        self, user_service: UserService, sample_user: User
    ):
        """Test getting a user by email."""
        user = await user_service.get_user_by_email("test@example.com")
        assert user is not None
        assert user.id == sample_user.id

    async def test_create_user(
        self, user_service: UserService, sample_role: Role
    ):
        """Test creating a new user."""
        user = await user_service.create_user(
            email="new@example.com",
            password="NewPassword123!",
            full_name="New User",
            role_id=sample_role.id,
            badge_number="54321",
        )

        assert user.id is not None
        assert user.email == "new@example.com"
        assert user.full_name == "New User"
        assert user.badge_number == "54321"
        assert user.is_active is True
        assert user.is_verified is False

    async def test_create_user_duplicate_email(
        self, user_service: UserService, sample_user: User
    ):
        """Test creating a user with duplicate email fails."""
        with pytest.raises(UserError, match="already registered"):
            await user_service.create_user(
                email="test@example.com",
                password="AnotherPassword123!",
                full_name="Another User",
            )

    async def test_create_user_weak_password(self, user_service: UserService):
        """Test creating a user with weak password fails."""
        with pytest.raises(UserError, match="at least 12 characters"):
            await user_service.create_user(
                email="weak@example.com",
                password="short",
                full_name="Weak Password User",
            )

        with pytest.raises(UserError, match="uppercase, lowercase, and numeric"):
            await user_service.create_user(
                email="weak@example.com",
                password="alllowercase123",
                full_name="Weak Password User",
            )

    async def test_update_user(
        self, user_service: UserService, sample_user: User
    ):
        """Test updating a user."""
        updated = await user_service.update_user(
            user_id=sample_user.id,
            full_name="Updated User",
            badge_number="99999",
        )

        assert updated.full_name == "Updated User"
        assert updated.badge_number == "99999"

    async def test_update_user_email(
        self, user_service: UserService, sample_user: User
    ):
        """Test updating user email."""
        updated = await user_service.update_user(
            user_id=sample_user.id,
            email="updated@example.com",
        )

        assert updated.email == "updated@example.com"

    async def test_update_user_duplicate_email(
        self, user_service: UserService, sample_user: User, db_session: AsyncSession
    ):
        """Test updating to duplicate email fails."""
        from app.core.security import get_password_hash

        other_user = User(
            id=uuid.uuid4(),
            email="other@example.com",
            hashed_password=get_password_hash("OtherPassword123!"),
            full_name="Other User",
            role=UserRole.RESPONDER,
        )
        db_session.add(other_user)
        await db_session.commit()

        with pytest.raises(UserError, match="already registered"):
            await user_service.update_user(
                user_id=sample_user.id,
                email="other@example.com",
            )

    async def test_update_user_not_found(self, user_service: UserService):
        """Test updating a non-existent user fails."""
        with pytest.raises(UserError, match="not found"):
            await user_service.update_user(
                user_id=uuid.uuid4(),
                full_name="Some Name",
            )

    async def test_deactivate_user(
        self, user_service: UserService, sample_user: User
    ):
        """Test deactivating a user."""
        updated = await user_service.deactivate_user(sample_user.id)
        assert updated.is_active is False

    async def test_activate_user(
        self, user_service: UserService, sample_user: User
    ):
        """Test activating a user."""
        # First deactivate
        await user_service.deactivate_user(sample_user.id)

        # Then activate
        updated = await user_service.activate_user(sample_user.id)
        assert updated.is_active is True
        assert updated.failed_login_attempts == 0
        assert updated.locked_until is None

    async def test_verify_user(
        self, user_service: UserService, sample_user: User
    ):
        """Test verifying a user."""
        updated = await user_service.verify_user(sample_user.id)
        assert updated.is_verified is True

    async def test_reset_password(
        self, user_service: UserService, sample_user: User
    ):
        """Test resetting user password."""
        old_hash = sample_user.hashed_password

        await user_service.reset_password(
            sample_user.id,
            "NewSecurePassword123!",
        )

        user = await user_service.get_user(sample_user.id)
        assert user.hashed_password != old_hash

    async def test_reset_password_weak(
        self, user_service: UserService, sample_user: User
    ):
        """Test resetting to weak password fails."""
        with pytest.raises(UserError, match="at least 12 characters"):
            await user_service.reset_password(sample_user.id, "weak")

    async def test_delete_user(
        self, user_service: UserService, sample_user: User
    ):
        """Test soft deleting a user."""
        await user_service.delete_user(sample_user.id)

        # User should not be found (soft deleted)
        user = await user_service.get_user(sample_user.id)
        assert user is None

    async def test_get_user_stats(
        self, user_service: UserService, sample_user: User
    ):
        """Test getting user statistics."""
        stats = await user_service.get_user_stats()

        assert "total" in stats
        assert "active" in stats
        assert "inactive" in stats
        assert "verified" in stats
        assert "unverified" in stats
        assert "by_role" in stats

        assert stats["total"] >= 1
        assert stats["active"] >= 1


class TestUserModel:
    """Test User model methods."""

    def test_role_name_with_role_obj(self):
        """Test role_name property with role object."""
        role = Role(
            name="commander",
            display_name="Commander",
            permissions=[],
        )
        user = User(
            email="test@example.com",
            hashed_password="hash",
            full_name="Test User",
            role=UserRole.RESPONDER,
        )
        user.role_obj = role

        assert user.role_name == "commander"

    def test_role_name_fallback(self):
        """Test role_name fallback to legacy role."""
        user = User(
            email="test@example.com",
            hashed_password="hash",
            full_name="Test User",
            role=UserRole.DISPATCHER,
        )

        assert user.role_name == "dispatcher"

    def test_role_display_name_with_role_obj(self):
        """Test role_display_name property with role object."""
        role = Role(
            name="commander",
            display_name="Incident Commander",
            permissions=[],
        )
        user = User(
            email="test@example.com",
            hashed_password="hash",
            full_name="Test User",
            role=UserRole.RESPONDER,
        )
        user.role_obj = role

        assert user.role_display_name == "Incident Commander"

    def test_role_display_name_fallback(self):
        """Test role_display_name fallback to formatted legacy role."""
        user = User(
            email="test@example.com",
            hashed_password="hash",
            full_name="Test User",
            role=UserRole.FIELD_UNIT_LEADER,
        )

        assert user.role_display_name == "Field Unit Leader"

    def test_has_permission_with_role_obj(self):
        """Test has_permission with role object."""
        role = Role(
            name="commander",
            display_name="Commander",
            permissions=["incidents:read", "incidents:create"],
        )
        user = User(
            email="test@example.com",
            hashed_password="hash",
            full_name="Test User",
            role=UserRole.RESPONDER,
        )
        user.role_obj = role

        assert user.has_permission("incidents:read") is True
        assert user.has_permission("incidents:delete") is False

    def test_has_permission_system_admin_fallback(self):
        """Test has_permission fallback for system admin."""
        user = User(
            email="test@example.com",
            hashed_password="hash",
            full_name="Test User",
            role=UserRole.SYSTEM_ADMIN,
        )

        # Without role_obj, system admin has all permissions
        assert user.has_permission("anything") is True

    def test_has_permission_non_admin_fallback(self):
        """Test has_permission fallback for non-admin."""
        user = User(
            email="test@example.com",
            hashed_password="hash",
            full_name="Test User",
            role=UserRole.RESPONDER,
        )

        # Without role_obj and not system admin
        assert user.has_permission("anything") is False
