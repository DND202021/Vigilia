"""Resource models for personnel, vehicles, and equipment tracking."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, Float, ForeignKey, Enum as SQLEnum, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.agency import Agency


class ResourceType(str, Enum):
    """Type of resource."""

    PERSONNEL = "personnel"
    VEHICLE = "vehicle"
    EQUIPMENT = "equipment"


class ResourceStatus(str, Enum):
    """Resource availability status."""

    AVAILABLE = "available"
    ASSIGNED = "assigned"
    EN_ROUTE = "en_route"
    ON_SCENE = "on_scene"
    OFF_DUTY = "off_duty"
    OUT_OF_SERVICE = "out_of_service"


class Resource(Base, TimestampMixin, SoftDeleteMixin):
    """Base resource model with common fields."""

    __tablename__ = "resources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    resource_type: Mapped[ResourceType] = mapped_column(
        SQLEnum(ResourceType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    status: Mapped[ResourceStatus] = mapped_column(
        SQLEnum(ResourceStatus, values_callable=lambda x: [e.value for e in x]),
        default=ResourceStatus.AVAILABLE,
        nullable=False,
        index=True,
    )

    # Common fields
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    call_sign: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Current location
    current_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Agency ownership
    agency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agencies.id"),
        nullable=False,
    )
    agency: Mapped["Agency"] = relationship("Agency", back_populates="resources")

    # Type-specific data stored as JSON (column name is 'metadata' in DB)
    resource_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True
    )

    __mapper_args__ = {
        "polymorphic_on": "resource_type",
        "polymorphic_identity": "resource",
    }

    def __repr__(self) -> str:
        return f"<Resource(id={self.id}, type={self.resource_type}, name={self.name})>"


class Personnel(Resource):
    """Personnel resource model."""

    __tablename__ = "personnel"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resources.id"),
        primary_key=True,
    )

    # Personnel-specific fields
    badge_number: Mapped[str] = mapped_column(String(50), nullable=False)
    rank: Mapped[str | None] = mapped_column(String(100), nullable=True)
    specializations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    certifications: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Linked user account (if any)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    # Assigned vehicle
    assigned_vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    __mapper_args__ = {
        "polymorphic_identity": ResourceType.PERSONNEL,
    }


class Vehicle(Resource):
    """Vehicle resource model."""

    __tablename__ = "vehicles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resources.id"),
        primary_key=True,
    )

    # Vehicle-specific fields
    vehicle_type: Mapped[str] = mapped_column(String(100), nullable=False)
    make: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    year: Mapped[int | None] = mapped_column(nullable=True)
    license_plate: Mapped[str | None] = mapped_column(String(20), nullable=True)
    vin: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Equipment inventory on vehicle
    equipment_inventory: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Maintenance
    last_maintenance_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_maintenance_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __mapper_args__ = {
        "polymorphic_identity": ResourceType.VEHICLE,
    }


class Equipment(Resource):
    """Equipment resource model."""

    __tablename__ = "equipment"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resources.id"),
        primary_key=True,
    )

    # Equipment-specific fields
    equipment_type: Mapped[str] = mapped_column(String(100), nullable=False)
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Assignment
    assigned_to_personnel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    assigned_to_vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Maintenance
    last_inspection_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_inspection_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __mapper_args__ = {
        "polymorphic_identity": ResourceType.EQUIPMENT,
    }
