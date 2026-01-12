"""Incident model for emergency event management."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Float, ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.agency import Agency
    from app.models.alert import Alert


class IncidentStatus(str, Enum):
    """Incident status enumeration."""

    NEW = "new"
    ASSIGNED = "assigned"
    EN_ROUTE = "en_route"
    ON_SCENE = "on_scene"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentPriority(int, Enum):
    """Incident priority levels (1=Critical, 5=Low)."""

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    MINIMAL = 5


class IncidentCategory(str, Enum):
    """Incident category enumeration."""

    FIRE = "fire"
    MEDICAL = "medical"
    POLICE = "police"
    RESCUE = "rescue"
    TRAFFIC = "traffic"
    WEATHER = "weather"
    HAZMAT = "hazmat"
    UTILITY = "utility"
    INTRUSION = "intrusion"
    ASSAULT = "assault"
    THEFT = "theft"
    THREAT = "threat"
    WELFARE_CHECK = "welfare_check"
    CIVIL_ASSISTANCE = "civil_assistance"
    TRAINING = "training"
    OTHER = "other"


class Incident(Base, TimestampMixin):
    """Incident model for emergency event management."""

    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Incident identification
    incident_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    # Classification
    category: Mapped[IncidentCategory] = mapped_column(
        SQLEnum(IncidentCategory, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(
        default=IncidentPriority.MEDIUM.value,
        nullable=False,
    )
    status: Mapped[IncidentStatus] = mapped_column(
        SQLEnum(IncidentStatus, values_callable=lambda x: [e.value for e in x]),
        default=IncidentStatus.NEW,
        nullable=False,
        index=True,
    )

    # Description
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Location
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    building_info: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timeline
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    arrived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Assigned units (stored as JSON array of resource IDs)
    assigned_units: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Parent incident for linking
    parent_incident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id"),
        nullable=True,
    )

    # Agency ownership
    agency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agencies.id"),
        nullable=False,
    )
    agency: Mapped["Agency"] = relationship("Agency", back_populates="incidents")

    # Source alert if created from alert
    source_alert_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alerts.id"),
        nullable=True,
    )
    source_alert: Mapped["Alert | None"] = relationship("Alert", back_populates="incidents")

    # Audit trail stored as JSON
    timeline_events: Mapped[list | None] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<Incident(id={self.id}, number={self.incident_number}, status={self.status})>"
