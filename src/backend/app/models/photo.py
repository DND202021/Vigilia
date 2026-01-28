"""Building Photo model for image storage."""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class BuildingPhoto(Base):
    """Building photo model for storing images."""

    __tablename__ = "building_photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, index=True)
    floor_plan_id = Column(UUID(as_uuid=True), ForeignKey("floor_plans.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    taken_at = Column(DateTime, nullable=True)
    uploaded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    tags = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    building = relationship("Building", back_populates="building_photos")
    floor_plan = relationship("FloorPlan", foreign_keys=[floor_plan_id])
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "building_id": str(self.building_id),
            "floor_plan_id": str(self.floor_plan_id) if self.floor_plan_id else None,
            "title": self.title,
            "description": self.description,
            "file_url": self.file_url,
            "thumbnail_url": self.thumbnail_url,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "taken_at": self.taken_at.isoformat() if self.taken_at else None,
            "uploaded_by_id": str(self.uploaded_by_id) if self.uploaded_by_id else None,
            "uploaded_by_name": self.uploaded_by.full_name if self.uploaded_by else None,
            "tags": self.tags or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
