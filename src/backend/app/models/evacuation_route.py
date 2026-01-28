"""Evacuation route model for emergency response planning."""

import uuid
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


if TYPE_CHECKING:
    from app.models.building import Building, FloorPlan


class RouteType(str, Enum):
    """Evacuation route type classification."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    ACCESSIBLE = "accessible"
    EMERGENCY_VEHICLE = "emergency_vehicle"


class EvacuationRoute(Base, TimestampMixin):
    """Evacuation route model for storing evacuation paths and waypoints."""

    __tablename__ = "evacuation_routes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Building reference (required)
    building_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    building: Mapped["Building"] = relationship(
        "Building",
        backref="evacuation_routes",
    )

    # Floor plan reference (optional - route can span multiple floors)
    floor_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("floor_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    floor_plan: Mapped[Optional["FloorPlan"]] = relationship(
        "FloorPlan",
        backref="evacuation_routes",
    )

    # Route identification
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Route classification
    route_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=RouteType.PRIMARY.value,
        index=True,
    )

    # Waypoints: array of waypoint objects
    # Format: [{order: int, x: float, y: float, floor_plan_id: uuid, label: str}]
    # x, y are percentage coordinates (0-100)
    waypoints: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Visualization properties
    color: Mapped[str] = mapped_column(String(20), default="#ff0000", nullable=False)
    line_width: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Capacity and timing
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Accessibility features
    # Format: ["wheelchair", "no_stairs", "wide_corridors", etc.]
    accessibility_features: Mapped[list | None] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<EvacuationRoute(id={self.id}, name={self.name}, type={self.route_type})>"
