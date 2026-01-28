"""Building model for emergency response building information management."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, Float, Integer, Boolean, ForeignKey
from sqlalchemy import Enum as SQLEnum, DateTime, JSON, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.agency import Agency
    from app.models.incident import Incident
    from app.models.inspection import Inspection
    from app.models.photo import BuildingPhoto
    from app.models.document import BuildingDocument


class BuildingType(str, Enum):
    """Building type classification."""

    RESIDENTIAL_SINGLE = "residential_single"
    RESIDENTIAL_MULTI = "residential_multi"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    INSTITUTIONAL = "institutional"
    HEALTHCARE = "healthcare"
    EDUCATIONAL = "educational"
    GOVERNMENT = "government"
    RELIGIOUS = "religious"
    MIXED_USE = "mixed_use"
    PARKING = "parking"
    WAREHOUSE = "warehouse"
    HIGH_RISE = "high_rise"
    OTHER = "other"


class OccupancyType(str, Enum):
    """Building occupancy classification (based on fire codes)."""

    ASSEMBLY = "assembly"  # A - places of assembly
    BUSINESS = "business"  # B - office buildings
    EDUCATIONAL = "educational"  # E - schools
    FACTORY = "factory"  # F - factories
    HIGH_HAZARD = "high_hazard"  # H - hazardous materials
    INSTITUTIONAL = "institutional"  # I - hospitals, jails
    MERCANTILE = "mercantile"  # M - retail stores
    RESIDENTIAL = "residential"  # R - apartments, hotels
    STORAGE = "storage"  # S - warehouses
    UTILITY = "utility"  # U - utility buildings


class ConstructionType(str, Enum):
    """Building construction type (fire resistance rating)."""

    TYPE_I_FIRE_RESISTIVE = "type_i"  # Non-combustible, highest rating
    TYPE_II_NON_COMBUSTIBLE = "type_ii"  # Non-combustible, limited fire resistance
    TYPE_III_ORDINARY = "type_iii"  # Masonry exterior, wood interior
    TYPE_IV_HEAVY_TIMBER = "type_iv"  # Heavy timber construction
    TYPE_V_WOOD_FRAME = "type_v"  # Wood frame construction
    UNKNOWN = "unknown"


class HazardLevel(str, Enum):
    """Building hazard level for emergency response."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class Building(Base, TimestampMixin, SoftDeleteMixin):
    """Building model for storing complete building information for emergency response."""

    __tablename__ = "buildings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Basic Information
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    civic_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    street_name: Mapped[str] = mapped_column(String(200), nullable=False)
    street_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unit_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    province_state: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="Canada")

    # Full address (denormalized for search)
    full_address: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    # Location
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # Building Classification
    building_type: Mapped[BuildingType] = mapped_column(
        SQLEnum(BuildingType, values_callable=lambda x: [e.value for e in x]),
        default=BuildingType.OTHER,
        nullable=False,
    )
    occupancy_type: Mapped[OccupancyType | None] = mapped_column(
        SQLEnum(OccupancyType, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    construction_type: Mapped[ConstructionType] = mapped_column(
        SQLEnum(ConstructionType, values_callable=lambda x: [e.value for e in x]),
        default=ConstructionType.UNKNOWN,
        nullable=False,
    )

    # Building Specifications
    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year_renovated: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_floors: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    basement_levels: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_area_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    building_height_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_occupancy: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Emergency Response Information
    hazard_level: Mapped[HazardLevel] = mapped_column(
        SQLEnum(HazardLevel, values_callable=lambda x: [e.value for e in x]),
        default=HazardLevel.LOW,
        nullable=False,
    )
    has_sprinkler_system: Mapped[bool] = mapped_column(Boolean, default=False)
    has_fire_alarm: Mapped[bool] = mapped_column(Boolean, default=False)
    has_standpipe: Mapped[bool] = mapped_column(Boolean, default=False)
    has_elevator: Mapped[bool] = mapped_column(Boolean, default=False)
    elevator_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_generator: Mapped[bool] = mapped_column(Boolean, default=False)

    # Access Information
    primary_entrance: Mapped[str | None] = mapped_column(Text, nullable=True)
    secondary_entrances: Mapped[list | None] = mapped_column(JSON, nullable=True)
    roof_access: Mapped[str | None] = mapped_column(Text, nullable=True)
    staging_area: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_box_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    knox_box: Mapped[bool] = mapped_column(Boolean, default=False)

    # Hazardous Materials
    has_hazmat: Mapped[bool] = mapped_column(Boolean, default=False)
    hazmat_details: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Format: [{"material": "propane", "location": "basement", "quantity": "500L"}]

    # Utilities
    utilities_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Format: {"gas_shutoff": "north side", "electrical_panel": "basement", "water_shutoff": "front yard"}

    # Contact Information
    owner_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    owner_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    manager_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    manager_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Special Considerations
    special_needs_occupants: Mapped[bool] = mapped_column(Boolean, default=False)
    special_needs_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    animals_present: Mapped[bool] = mapped_column(Boolean, default=False)
    animals_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    security_features: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Format: ["alarm_system", "guard_dog", "armed_security", "cameras"]

    # Pre-Incident Plan
    pre_incident_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    tactical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_inspection_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_inspection_due: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # BIM Data (Building Information Model)
    bim_file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bim_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Stores extracted BIM information in JSON format

    # External Data References
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    data_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # e.g., "quebec_role", "google_places", "openstreetmap"

    # Photos and Documents
    photos: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Format: [{"url": "...", "description": "front view", "taken_at": "..."}]
    documents: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Format: [{"url": "...", "name": "floor_plan.pdf", "type": "floor_plan"}]

    # Agency ownership
    agency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agencies.id"),
        nullable=False,
    )
    agency: Mapped["Agency"] = relationship("Agency", back_populates="buildings")

    # Inspections
    inspections: Mapped[list["Inspection"]] = relationship(
        "Inspection", back_populates="building", cascade="all, delete-orphan"
    )

    # Photos (BuildingPhoto model)
    building_photos: Mapped[list["BuildingPhoto"]] = relationship(
        "BuildingPhoto", back_populates="building", cascade="all, delete-orphan"
    )

    # Documents (BuildingDocument model)
    building_documents: Mapped[list["BuildingDocument"]] = relationship(
        "BuildingDocument", back_populates="building", cascade="all, delete-orphan"
    )

    # Verification status
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Building(id={self.id}, name={self.name}, address={self.full_address})>"

    @property
    def display_address(self) -> str:
        """Generate display address from components."""
        parts = []
        if self.civic_number:
            parts.append(self.civic_number)
        parts.append(self.street_name)
        if self.street_type:
            parts.append(self.street_type)
        if self.unit_number:
            parts.append(f"#{self.unit_number}")
        return " ".join(parts)


class FloorPlan(Base, TimestampMixin):
    """Floor plan model for storing individual floor plans."""

    __tablename__ = "floor_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    building_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False,
    )
    building: Mapped["Building"] = relationship(
        "Building",
        backref="floor_plans",
    )

    # Floor identification
    floor_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # Negative for basement levels, 0 for ground, positive for upper floors
    floor_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # e.g., "Ground Floor", "Mezzanine", "Basement 1"

    # Floor specifications
    floor_area_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    ceiling_height_m: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Plan image/file
    plan_file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    plan_thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    plan_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    # For storing small plan images directly
    file_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # e.g., "pdf", "png", "svg", "dwg"

    # BIM/CAD data for this floor
    bim_floor_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Key locations on this floor
    key_locations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Format: [{"type": "stairwell", "name": "North Stairwell", "x": 100, "y": 200}]
    # Types: stairwell, elevator, fire_extinguisher, aed, electrical_panel, etc.

    # Emergency information for this floor
    emergency_exits: Mapped[list | None] = mapped_column(JSON, nullable=True)
    fire_equipment: Mapped[list | None] = mapped_column(JSON, nullable=True)
    hazards: Mapped[list | None] = mapped_column(JSON, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<FloorPlan(building_id={self.building_id}, floor={self.floor_number})>"
