"""Authentication service for user management and token operations."""

from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models.user import User, UserRole


class AuthenticationError(Exception):
    """Authentication related errors."""

    pass


class AuthService:
    """Service for authentication operations."""

    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30

    def __init__(self, db: AsyncSession):
        """Initialize auth service with database session."""
        self.db = db

    async def authenticate_user(self, email: str, password: str) -> User:
        """Authenticate user with email and password."""
        user = await self._get_user_by_email(email)

        if user is None:
            raise AuthenticationError("Invalid email or password")

        # Check if account is locked
        if user.locked_until:
            locked_until = datetime.fromisoformat(user.locked_until)
            if locked_until > datetime.now(timezone.utc):
                raise AuthenticationError(
                    f"Account is locked. Try again after {locked_until.isoformat()}"
                )
            else:
                # Lockout expired, reset
                user.locked_until = None
                user.failed_login_attempts = 0

        # Check if account is active
        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        # Verify password
        if not verify_password(password, user.hashed_password):
            await self._handle_failed_login(user)
            raise AuthenticationError("Invalid email or password")

        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.db.commit()

        return user

    async def create_tokens(self, user: User) -> dict[str, str]:
        """Create access and refresh tokens for user."""
        additional_claims = {
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "agency_id": str(user.agency_id) if user.agency_id else None,
        }

        access_token = create_access_token(
            subject=str(user.id),
            additional_claims=additional_claims,
        )
        refresh_token = create_refresh_token(subject=str(user.id))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def refresh_access_token(self, refresh_token: str) -> dict[str, str]:
        """Refresh access token using refresh token."""
        payload = verify_token(refresh_token, token_type="refresh")

        if payload is None:
            raise AuthenticationError("Invalid or expired refresh token")

        user_id = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Invalid token payload")

        user = await self._get_user_by_id(uuid.UUID(user_id))
        if user is None:
            raise AuthenticationError("User not found")

        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        return await self.create_tokens(user)

    async def create_user(
        self,
        email: str,
        password: str,
        full_name: str,
        role: UserRole = UserRole.RESPONDER,
        agency_id: uuid.UUID | None = None,
        badge_number: str | None = None,
    ) -> User:
        """Create a new user."""
        # Check if email already exists
        existing_user = await self._get_user_by_email(email)
        if existing_user:
            raise AuthenticationError("Email already registered")

        # Validate password strength
        self._validate_password(password)

        user = User(
            email=email.lower(),
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=role,
            agency_id=agency_id,
            badge_number=badge_number,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def get_current_user(self, token: str) -> User:
        """Get current user from access token."""
        payload = verify_token(token, token_type="access")

        if payload is None:
            raise AuthenticationError("Invalid or expired token")

        user_id = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Invalid token payload")

        user = await self._get_user_by_id(uuid.UUID(user_id))
        if user is None:
            raise AuthenticationError("User not found")

        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        return user

    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:
        """Change user password."""
        if not verify_password(current_password, user.hashed_password):
            raise AuthenticationError("Current password is incorrect")

        self._validate_password(new_password)

        user.hashed_password = get_password_hash(new_password)
        await self.db.commit()

    async def _get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def _get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def _handle_failed_login(self, user: User) -> None:
        """Handle failed login attempt."""
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= self.MAX_LOGIN_ATTEMPTS:
            lockout_until = datetime.now(timezone.utc).replace(
                microsecond=0
            ) + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)
            user.locked_until = lockout_until.isoformat()

        await self.db.commit()

    @staticmethod
    def _validate_password(password: str) -> None:
        """Validate password strength."""
        if len(password) < 12:
            raise AuthenticationError(
                "Password must be at least 12 characters long"
            )

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        if not (has_upper and has_lower and has_digit):
            raise AuthenticationError(
                "Password must contain uppercase, lowercase, and numeric characters"
            )
