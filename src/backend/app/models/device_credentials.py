"""Device credentials model for per-device authentication."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.device import IoTDevice


class CredentialType(str, Enum):
    """Device credential types."""
    ACCESS_TOKEN = "access_token"
    X509 = "x509"


class DeviceCredentials(Base, TimestampMixin):
    """Per-device authentication credentials (access token or X.509 certificate)."""

    __tablename__ = "device_credentials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iot_devices.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    credential_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Access token fields
    access_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # X.509 certificate fields
    certificate_pem: Mapped[str | None] = mapped_column(Text, nullable=True)
    certificate_cn: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    certificate_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship
    device: Mapped["IoTDevice"] = relationship("IoTDevice", back_populates="credentials")

    def __repr__(self) -> str:
        return f"<DeviceCredentials(id={self.id}, device_id={self.device_id}, type={self.credential_type})>"
