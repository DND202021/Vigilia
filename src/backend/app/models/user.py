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


class UserRole(str, Enum):
    """User role enumeration."""

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

    # Role and permissions
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole),
        default=UserRole.RESPONDER,
        nullable=False,
    )

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

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
