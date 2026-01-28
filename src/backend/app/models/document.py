"""Building Document model for file storage."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.building import Building
    from app.models.user import User


class DocumentCategory(str, Enum):
    """Document category enum."""
    PRE_PLAN = "pre_plan"
    FLOOR_PLAN = "floor_plan"
    PERMIT = "permit"
    INSPECTION = "inspection"
    MANUAL = "manual"
    OTHER = "other"


class BuildingDocument(Base, TimestampMixin):
    """Building document model for storing files."""

    __tablename__ = "building_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    building_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[DocumentCategory] = mapped_column(
        SQLEnum(DocumentCategory, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=DocumentCategory.OTHER,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    building: Mapped["Building"] = relationship("Building", back_populates="building_documents")
    uploaded_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[uploaded_by_id])

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "building_id": str(self.building_id),
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "file_url": self.file_url,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "uploaded_by_id": str(self.uploaded_by_id) if self.uploaded_by_id else None,
            "uploaded_by_name": self.uploaded_by.full_name if self.uploaded_by else None,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<BuildingDocument(id={self.id}, title={self.title}, building_id={self.building_id})>"
