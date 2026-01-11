"""Tests for authentication service."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth_service import AuthService, AuthenticationError
from app.models.user import User, UserRole


class TestAuthService:
    """Tests for AuthService."""

    @pytest.mark.asyncio
    async def test_create_user_success(self, db_session: AsyncSession, test_agency):
        """User creation should work with valid data."""
        auth_service = AuthService(db_session)

        user = await auth_service.create_user(
            email="newuser@example.com",
            password="SecurePassword123!",
            full_name="New User",
            role=UserRole.RESPONDER,
            agency_id=test_agency.id,
        )

        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.full_name == "New User"
        assert user.role == UserRole.RESPONDER
        assert user.agency_id == test_agency.id

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, db_session: AsyncSession, test_user: User):
        """Creating user with existing email should fail."""
        auth_service = AuthService(db_session)

        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.create_user(
                email=test_user.email,
                password="SecurePassword123!",
                full_name="Duplicate User",
            )

        assert "already registered" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_user_weak_password(self, db_session: AsyncSession):
        """Creating user with weak password should fail."""
        auth_service = AuthService(db_session)

        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.create_user(
                email="weak@example.com",
                password="weak",
                full_name="Weak Password User",
            )

        assert "12 characters" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, db_session: AsyncSession, test_user: User):
        """Authentication should work with correct credentials."""
        auth_service = AuthService(db_session)

        user = await auth_service.authenticate_user(
            email="test@example.com",
            password="TestPassword123!",
        )

        assert user.id == test_user.id
        assert user.email == test_user.email

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, db_session: AsyncSession, test_user: User):
        """Authentication should fail with wrong password."""
        auth_service = AuthService(db_session)

        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.authenticate_user(
                email="test@example.com",
                password="WrongPassword123!",
            )

        assert "Invalid email or password" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authenticate_user_nonexistent(self, db_session: AsyncSession):
        """Authentication should fail for non-existent user."""
        auth_service = AuthService(db_session)

        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.authenticate_user(
                email="nonexistent@example.com",
                password="SomePassword123!",
            )

        assert "Invalid email or password" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_tokens(self, db_session: AsyncSession, test_user: User):
        """Token creation should return access and refresh tokens."""
        auth_service = AuthService(db_session)

        tokens = await auth_service.create_tokens(test_user)

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_access_token(self, db_session: AsyncSession, test_user: User):
        """Token refresh should work with valid refresh token."""
        auth_service = AuthService(db_session)

        # Get initial tokens
        tokens = await auth_service.create_tokens(test_user)

        # Refresh
        new_tokens = await auth_service.refresh_access_token(tokens["refresh_token"])

        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        assert new_tokens["token_type"] == "bearer"
        # Verify the new access token is valid
        user = await auth_service.get_current_user(new_tokens["access_token"])
        assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token(self, db_session: AsyncSession):
        """Token refresh should fail with invalid token."""
        auth_service = AuthService(db_session)

        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.refresh_access_token("invalid.token.here")

        assert "Invalid" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_current_user(self, db_session: AsyncSession, test_user: User):
        """Getting current user from token should work."""
        auth_service = AuthService(db_session)

        tokens = await auth_service.create_tokens(test_user)
        user = await auth_service.get_current_user(tokens["access_token"])

        assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_change_password_success(self, db_session: AsyncSession, test_user: User):
        """Password change should work with correct current password."""
        auth_service = AuthService(db_session)

        await auth_service.change_password(
            user=test_user,
            current_password="TestPassword123!",
            new_password="NewSecurePassword123!",
        )

        # Verify can authenticate with new password
        user = await auth_service.authenticate_user(
            email=test_user.email,
            password="NewSecurePassword123!",
        )
        assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, db_session: AsyncSession, test_user: User):
        """Password change should fail with wrong current password."""
        auth_service = AuthService(db_session)

        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.change_password(
                user=test_user,
                current_password="WrongPassword123!",
                new_password="NewSecurePassword123!",
            )

        assert "incorrect" in str(exc_info.value)
