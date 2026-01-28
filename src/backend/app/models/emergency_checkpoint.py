"""EmergencyCheckpoint model for Sprint 10 Emergency Response Planning."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, Float, Integer, Boolean, ForeignKey
from sqlalchemy import Enum as SQLEnum, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.building import Building, FloorPlan


class CheckpointType(str, Enum):
    """Emergency checkpoint type classification."""

    ASSEMBLY_POINT = "assembly_point"
    MUSTER_STATION = "muster_station"
    FIRST_AID = "first_aid"
    COMMAND_POST = "command_post"
    TRIAGE_AREA = "triage_area"
    DECONTAMINATION = "decontamination"
    STAGING_AREA = "staging_area"
    MEDIA_POINT = "media_point"


class EmergencyCheckpoint(Base, TimestampMixin):
    """Emergency checkpoint model for managing emergency response locations."""

    __tablename__ = "emergency_checkpoints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Building relationship (required)
    building_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    building: Mapped["Building"] = relationship(
        "Building",
        backref="emergency_checkpoints",
    )

    # Floor plan relationship (optional)
    floor_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("floor_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    floor_plan: Mapped[Optional["FloorPlan"]] = relationship(
        "FloorPlan",
        backref="emergency_checkpoints",
    )

    # Basic Information
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Checkpoint type
    checkpoint_type: Mapped[CheckpointType] = mapped_column(
        SQLEnum(CheckpointType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )

    # Position on floor plan (percentage 0-100)
    position_x: Mapped[float] = mapped_column(Float, nullable=False)
    position_y: Mapped[float] = mapped_column(Float, nullable=False)

    # Capacity (max people at this checkpoint)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Equipment at this checkpoint
    # Format: [{"name": "First Aid Kit", "quantity": 2, "location": "Cabinet A"}]
    equipment: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Responsible person
    responsible_person: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Contact information
    # Format: {"phone": "555-1234", "email": "contact@example.com", "radio_channel": "Channel 5"}
    contact_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Instructions for emergency responders
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Active status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<EmergencyCheckpoint(id={self.id}, name={self.name}, type={self.checkpoint_type.value})>"
