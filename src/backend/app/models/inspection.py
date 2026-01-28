"""Inspection model for building inspection tracking."""

import uuid
from datetime import datetime, date
from enum import Enum

from sqlalchemy import Column, String, Boolean, Text, DateTime, Date, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class InspectionType(str, Enum):
    """Inspection type enum."""
    FIRE_SAFETY = "fire_safety"
    STRUCTURAL = "structural"
    HAZMAT = "hazmat"
    GENERAL = "general"


class InspectionStatus(str, Enum):
    """Inspection status enum."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    OVERDUE = "overdue"


class Inspection(Base):
    """Building inspection model."""

    __tablename__ = "inspections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, index=True)
    inspection_type = Column(SQLEnum(InspectionType), nullable=False)
    scheduled_date = Column(Date, nullable=False, index=True)
    completed_date = Column(Date, nullable=True)
    status = Column(SQLEnum(InspectionStatus), nullable=False, default=InspectionStatus.SCHEDULED)
    inspector_name = Column(String(255), nullable=False)
    findings = Column(Text, nullable=True)
    follow_up_required = Column(Boolean, nullable=False, default=False)
    follow_up_date = Column(Date, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    building = relationship("Building", back_populates="inspections")
    created_by = relationship("User", foreign_keys=[created_by_id])

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "building_id": str(self.building_id),
            "inspection_type": self.inspection_type.value,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "completed_date": self.completed_date.isoformat() if self.completed_date else None,
            "status": self.status.value,
            "inspector_name": self.inspector_name,
            "findings": self.findings,
            "follow_up_required": self.follow_up_required,
            "follow_up_date": self.follow_up_date.isoformat() if self.follow_up_date else None,
            "created_by_id": str(self.created_by_id) if self.created_by_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
