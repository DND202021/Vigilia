"""User model for authentication and authorization."""

import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.agency import Agency
    from app.models.role import Role


class UserRole(str, Enum):
    """User role enumeration (legacy, kept for migration compatibility)."""

    SYSTEM_ADMIN = "system_admin"
    AGENCY_ADMIN = "agency_admin"
    COMMANDER = "commander"
    DISPATCHER = "dispatcher"
    FIELD_UNIT_LEADER = "field_unit_leader"
    RESPONDER = "responder"
    PUBLIC_USER = "public_user"


class User(Base, TimestampMixin, SoftDeleteMixin):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile information
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    badge_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Legacy role field (kept for migration compatibility)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, values_callable=lambda x: [e.value for e in x]),
        default=UserRole.RESPONDER,
        nullable=False,
    )

    # New flexible role system
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id"),
        nullable=True,
        index=True,
    )
    role_obj: Mapped["Role | None"] = relationship("Role", back_populates="users")

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # MFA
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Failed login tracking
    failed_login_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Agency relationship (nullable for system admins)
    agency_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agencies.id"),
        nullable=True,
    )
    agency: Mapped["Agency | None"] = relationship("Agency", back_populates="users")

    @property
    def role_name(self) -> str:
        """Get the role name (from new system or legacy)."""
        if self.role_obj:
            return self.role_obj.name
        return self.role.value

    @property
    def role_display_name(self) -> str:
        """Get the role display name."""
        if self.role_obj:
            return self.role_obj.display_name
        # Fallback to formatted legacy role
        return self.role.value.replace("_", " ").title()

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        if self.role_obj:
            return self.role_obj.has_permission(permission)
        # Fallback: system_admin has all permissions
        return self.role == UserRole.SYSTEM_ADMIN

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role_name})>"
