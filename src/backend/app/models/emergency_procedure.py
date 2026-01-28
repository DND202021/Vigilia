"""Emergency procedure model for emergency response planning."""

import uuid
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, JSON
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.building import Building


class ProcedureType(str, Enum):
    """Emergency procedure type classification."""

    EVACUATION = "evacuation"
    FIRE = "fire"
    MEDICAL = "medical"
    HAZMAT = "hazmat"
    LOCKDOWN = "lockdown"
    ACTIVE_SHOOTER = "active_shooter"
    WEATHER = "weather"
    UTILITY_FAILURE = "utility_failure"


class EmergencyProcedure(Base, TimestampMixin, SoftDeleteMixin):
    """Emergency procedure model for storing building emergency response procedures."""

    __tablename__ = "emergency_procedures"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Building relationship
    building_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    building: Mapped["Building"] = relationship(
        "Building",
        backref="emergency_procedures",
    )

    # Basic Information
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Procedure Classification
    procedure_type: Mapped[ProcedureType] = mapped_column(
        SQLEnum(ProcedureType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )

    # Priority (1-5, 1=highest)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    # Procedure Details (JSON arrays)
    # Format: [{"order": 1, "title": "...", "description": "...", "responsible_role": "...", "duration_minutes": 5}]
    steps: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Contact Information
    # Format: [{"name": "...", "role": "...", "phone": "...", "email": "..."}]
    contacts: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Equipment needed (array of strings)
    # Format: ["fire extinguisher", "first aid kit", "flashlight"]
    equipment_needed: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Duration estimate
    estimated_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<EmergencyProcedure(id={self.id}, name={self.name}, type={self.procedure_type.value})>"
