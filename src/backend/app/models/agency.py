"""Agency model for multi-tenancy support."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.incident import Incident
    from app.models.resource import Resource
    from app.models.building import Building


class Agency(Base, TimestampMixin, SoftDeleteMixin):
    """Agency model representing emergency service organizations."""

    __tablename__ = "agencies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Contact information
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Configuration
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="agency")
    incidents: Mapped[list["Incident"]] = relationship("Incident", back_populates="agency")
    resources: Mapped[list["Resource"]] = relationship("Resource", back_populates="agency")
    buildings: Mapped[list["Building"]] = relationship("Building", back_populates="agency")

    def __repr__(self) -> str:
        return f"<Agency(id={self.id}, code={self.code}, name={self.name})>"
