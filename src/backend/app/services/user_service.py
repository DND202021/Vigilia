"""User service for user management operations."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserRole
from app.models.role import Role


class UserError(Exception):
    """User-related errors."""

    pass


class UserService:
    """Service for user management operations."""

    def __init__(self, db: AsyncSession):
        """Initialize user service with database session."""
        self.db = db

    async def list_users(
        self,
        agency_id: uuid.UUID | None = None,
        role_id: uuid.UUID | None = None,
        is_active: bool | None = None,
        is_verified: bool | None = None,
        search: str | None = None,
        include_deleted: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[User], int]:
        """List users with filtering and pagination."""
        conditions = []

        if not include_deleted:
            conditions.append(User.deleted_at == None)

        if agency_id is not None:
            conditions.append(User.agency_id == agency_id)

        if role_id is not None:
            conditions.append(User.role_id == role_id)

        if is_active is not None:
            conditions.append(User.is_active == is_active)

        if is_verified is not None:
            conditions.append(User.is_verified == is_verified)

        if search:
            search_term = f"%{search.lower()}%"
            conditions.append(
                or_(
                    User.email.ilike(search_term),
                    User.full_name.ilike(search_term),
                    User.badge_number.ilike(search_term),
                )
            )

        # Build query
        query = select(User).options(selectinload(User.role_obj), selectinload(User.agency))
        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count(User.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        users = list(result.scalars().all())

        return users, total

    async def get_user(self, user_id: uuid.UUID) -> User | None:
        """Get a user by ID."""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.role_obj), selectinload(User.agency))
            .where(and_(User.id == user_id, User.deleted_at == None))
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        """Get a user by email."""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.role_obj), selectinload(User.agency))
            .where(and_(User.email == email.lower(), User.deleted_at == None))
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        email: str,
        password: str,
        full_name: str,
        role_id: uuid.UUID | None = None,
        agency_id: uuid.UUID | None = None,
        badge_number: str | None = None,
        phone: str | None = None,
        is_verified: bool = False,
    ) -> User:
        """Create a new user."""
        # Check for duplicate email
        existing = await self.get_user_by_email(email)
        if existing:
            raise UserError("Email already registered")

        # Validate password
        self._validate_password(password)

        # Get default role if not provided
        legacy_role = UserRole.RESPONDER
        if role_id:
            role = await self._get_role(role_id)
            if role:
                # Map role name to legacy enum
                try:
                    legacy_role = UserRole(role.name)
                except ValueError:
                    legacy_role = UserRole.RESPONDER
        else:
            # Get default responder role
            from app.services.role_service import RoleService
            role_service = RoleService(self.db)
            default_role = await role_service.get_role_by_name("responder")
            if default_role:
                role_id = default_role.id

        user = User(
            email=email.lower(),
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=legacy_role,
            role_id=role_id,
            agency_id=agency_id,
            badge_number=badge_number,
            phone=phone,
            is_verified=is_verified,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        # Load relationships
        return await self.get_user(user.id)

    async def update_user(
        self,
        user_id: uuid.UUID,
        full_name: str | None = None,
        email: str | None = None,
        role_id: uuid.UUID | None = None,
        agency_id: uuid.UUID | None = None,
        badge_number: str | None = None,
        phone: str | None = None,
        is_verified: bool | None = None,
    ) -> User:
        """Update an existing user."""
        user = await self.get_user(user_id)
        if not user:
            raise UserError("User not found")

        if email is not None and email.lower() != user.email:
            # Check for duplicate email
            existing = await self.get_user_by_email(email)
            if existing:
                raise UserError("Email already registered")
            user.email = email.lower()

        if full_name is not None:
            user.full_name = full_name

        if role_id is not None:
            role = await self._get_role(role_id)
            if not role:
                raise UserError("Role not found")
            user.role_id = role_id
            # Update legacy role
            try:
                user.role = UserRole(role.name)
            except ValueError:
                pass

        if agency_id is not None:
            user.agency_id = agency_id

        if badge_number is not None:
            user.badge_number = badge_number

        if phone is not None:
            user.phone = phone

        if is_verified is not None:
            user.is_verified = is_verified

        await self.db.commit()
        return await self.get_user(user_id)

    async def deactivate_user(self, user_id: uuid.UUID) -> User:
        """Deactivate a user account."""
        user = await self.get_user(user_id)
        if not user:
            raise UserError("User not found")

        user.is_active = False
        await self.db.commit()
        return await self.get_user(user_id)

    async def activate_user(self, user_id: uuid.UUID) -> User:
        """Activate a user account."""
        user = await self.get_user(user_id)
        if not user:
            raise UserError("User not found")

        user.is_active = True
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.db.commit()
        return await self.get_user(user_id)

    async def verify_user(self, user_id: uuid.UUID) -> User:
        """Mark a user as verified."""
        user = await self.get_user(user_id)
        if not user:
            raise UserError("User not found")

        user.is_verified = True
        await self.db.commit()
        return await self.get_user(user_id)

    async def reset_password(
        self,
        user_id: uuid.UUID,
        new_password: str,
    ) -> None:
        """Reset a user's password (admin action)."""
        user = await self.get_user(user_id)
        if not user:
            raise UserError("User not found")

        self._validate_password(new_password)
        user.hashed_password = get_password_hash(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.db.commit()

    async def delete_user(self, user_id: uuid.UUID) -> None:
        """Soft delete a user."""
        user = await self.get_user(user_id)
        if not user:
            raise UserError("User not found")

        user.deleted_at = datetime.now(timezone.utc)
        user.is_active = False
        await self.db.commit()

    async def get_user_stats(
        self,
        agency_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Get user statistics."""
        conditions = [User.deleted_at == None]
        if agency_id:
            conditions.append(User.agency_id == agency_id)

        # Total users
        total_query = select(func.count(User.id)).where(and_(*conditions))
        total_result = await self.db.execute(total_query)
        total = total_result.scalar() or 0

        # Active users
        active_conditions = conditions + [User.is_active == True]
        active_query = select(func.count(User.id)).where(and_(*active_conditions))
        active_result = await self.db.execute(active_query)
        active = active_result.scalar() or 0

        # Verified users
        verified_conditions = conditions + [User.is_verified == True]
        verified_query = select(func.count(User.id)).where(and_(*verified_conditions))
        verified_result = await self.db.execute(verified_query)
        verified = verified_result.scalar() or 0

        # Users by role
        role_query = (
            select(Role.name, func.count(User.id))
            .join(User, User.role_id == Role.id)
            .where(and_(*conditions))
            .group_by(Role.name)
        )
        role_result = await self.db.execute(role_query)
        by_role = {name: count for name, count in role_result.all()}

        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "verified": verified,
            "unverified": total - verified,
            "by_role": by_role,
        }

    async def _get_role(self, role_id: uuid.UUID) -> Role | None:
        """Get a role by ID."""
        result = await self.db.execute(
            select(Role).where(and_(Role.id == role_id, Role.deleted_at == None))
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _validate_password(password: str) -> None:
        """Validate password strength."""
        if len(password) < 12:
            raise UserError("Password must be at least 12 characters long")

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)

        if not (has_upper and has_lower and has_digit):
            raise UserError(
                "Password must contain uppercase, lowercase, and numeric characters"
            )
