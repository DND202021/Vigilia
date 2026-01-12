"""Add buildings and floor_plans tables

Revision ID: 005
Revises: 004
Create Date: 2026-01-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create building type enum
    op.execute("""
        CREATE TYPE buildingtype AS ENUM (
            'residential_single', 'residential_multi', 'commercial', 'industrial',
            'institutional', 'healthcare', 'educational', 'government',
            'religious', 'mixed_use', 'parking', 'warehouse', 'high_rise', 'other'
        )
    """)

    # Create occupancy type enum
    op.execute("""
        CREATE TYPE occupancytype AS ENUM (
            'assembly', 'business', 'educational', 'factory', 'high_hazard',
            'institutional', 'mercantile', 'residential', 'storage', 'utility'
        )
    """)

    # Create construction type enum
    op.execute("""
        CREATE TYPE constructiontype AS ENUM (
            'type_i', 'type_ii', 'type_iii', 'type_iv', 'type_v', 'unknown'
        )
    """)

    # Create hazard level enum
    op.execute("""
        CREATE TYPE hazardlevel AS ENUM (
            'low', 'moderate', 'high', 'extreme'
        )
    """)

    # Create buildings table
    op.create_table(
        "buildings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),

        # Basic Information
        sa.Column("name", sa.String(200), nullable=False, index=True),
        sa.Column("civic_number", sa.String(20), nullable=True),
        sa.Column("street_name", sa.String(200), nullable=False),
        sa.Column("street_type", sa.String(50), nullable=True),
        sa.Column("unit_number", sa.String(50), nullable=True),
        sa.Column("city", sa.String(100), nullable=False, index=True),
        sa.Column("province_state", sa.String(100), nullable=False),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("country", sa.String(100), default="Canada"),
        sa.Column("full_address", sa.String(500), nullable=False, index=True),

        # Location
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),

        # Building Classification
        sa.Column(
            "building_type",
            sa.Enum(
                'residential_single', 'residential_multi', 'commercial', 'industrial',
                'institutional', 'healthcare', 'educational', 'government',
                'religious', 'mixed_use', 'parking', 'warehouse', 'high_rise', 'other',
                name="buildingtype",
                create_type=False,
            ),
            default="other",
            nullable=False,
        ),
        sa.Column(
            "occupancy_type",
            sa.Enum(
                'assembly', 'business', 'educational', 'factory', 'high_hazard',
                'institutional', 'mercantile', 'residential', 'storage', 'utility',
                name="occupancytype",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "construction_type",
            sa.Enum(
                'type_i', 'type_ii', 'type_iii', 'type_iv', 'type_v', 'unknown',
                name="constructiontype",
                create_type=False,
            ),
            default="unknown",
            nullable=False,
        ),

        # Building Specifications
        sa.Column("year_built", sa.Integer, nullable=True),
        sa.Column("year_renovated", sa.Integer, nullable=True),
        sa.Column("total_floors", sa.Integer, default=1, nullable=False),
        sa.Column("basement_levels", sa.Integer, default=0, nullable=False),
        sa.Column("total_area_sqm", sa.Float, nullable=True),
        sa.Column("building_height_m", sa.Float, nullable=True),
        sa.Column("max_occupancy", sa.Integer, nullable=True),

        # Emergency Response Information
        sa.Column(
            "hazard_level",
            sa.Enum(
                'low', 'moderate', 'high', 'extreme',
                name="hazardlevel",
                create_type=False,
            ),
            default="low",
            nullable=False,
        ),
        sa.Column("has_sprinkler_system", sa.Boolean, default=False),
        sa.Column("has_fire_alarm", sa.Boolean, default=False),
        sa.Column("has_standpipe", sa.Boolean, default=False),
        sa.Column("has_elevator", sa.Boolean, default=False),
        sa.Column("elevator_count", sa.Integer, nullable=True),
        sa.Column("has_generator", sa.Boolean, default=False),

        # Access Information
        sa.Column("primary_entrance", sa.Text, nullable=True),
        sa.Column("secondary_entrances", postgresql.JSONB, nullable=True),
        sa.Column("roof_access", sa.Text, nullable=True),
        sa.Column("staging_area", sa.Text, nullable=True),
        sa.Column("key_box_location", sa.String(200), nullable=True),
        sa.Column("knox_box", sa.Boolean, default=False),

        # Hazardous Materials
        sa.Column("has_hazmat", sa.Boolean, default=False),
        sa.Column("hazmat_details", postgresql.JSONB, nullable=True),

        # Utilities
        sa.Column("utilities_info", postgresql.JSONB, nullable=True),

        # Contact Information
        sa.Column("owner_name", sa.String(200), nullable=True),
        sa.Column("owner_phone", sa.String(50), nullable=True),
        sa.Column("owner_email", sa.String(200), nullable=True),
        sa.Column("manager_name", sa.String(200), nullable=True),
        sa.Column("manager_phone", sa.String(50), nullable=True),
        sa.Column("emergency_contact_name", sa.String(200), nullable=True),
        sa.Column("emergency_contact_phone", sa.String(50), nullable=True),

        # Special Considerations
        sa.Column("special_needs_occupants", sa.Boolean, default=False),
        sa.Column("special_needs_details", sa.Text, nullable=True),
        sa.Column("animals_present", sa.Boolean, default=False),
        sa.Column("animals_details", sa.Text, nullable=True),
        sa.Column("security_features", postgresql.JSONB, nullable=True),

        # Pre-Incident Plan
        sa.Column("pre_incident_plan", sa.Text, nullable=True),
        sa.Column("tactical_notes", sa.Text, nullable=True),
        sa.Column("last_inspection_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_inspection_due", sa.DateTime(timezone=True), nullable=True),

        # BIM Data
        sa.Column("bim_file_url", sa.String(500), nullable=True),
        sa.Column("bim_data", postgresql.JSONB, nullable=True),

        # External Data References
        sa.Column("external_id", sa.String(100), nullable=True, index=True),
        sa.Column("data_source", sa.String(100), nullable=True),

        # Photos and Documents
        sa.Column("photos", postgresql.JSONB, nullable=True),
        sa.Column("documents", postgresql.JSONB, nullable=True),

        # Agency ownership
        sa.Column(
            "agency_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agencies.id"),
            nullable=False,
        ),

        # Verification status
        sa.Column("is_verified", sa.Boolean, default=False),
        sa.Column(
            "verified_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),

        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create floor_plans table
    op.create_table(
        "floor_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),

        sa.Column(
            "building_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("buildings.id", ondelete="CASCADE"),
            nullable=False,
        ),

        # Floor identification
        sa.Column("floor_number", sa.Integer, nullable=False),
        sa.Column("floor_name", sa.String(50), nullable=True),

        # Floor specifications
        sa.Column("floor_area_sqm", sa.Float, nullable=True),
        sa.Column("ceiling_height_m", sa.Float, nullable=True),

        # Plan image/file
        sa.Column("plan_file_url", sa.String(500), nullable=True),
        sa.Column("plan_thumbnail_url", sa.String(500), nullable=True),
        sa.Column("plan_data", sa.LargeBinary, nullable=True),
        sa.Column("file_type", sa.String(50), nullable=True),

        # BIM/CAD data for this floor
        sa.Column("bim_floor_data", postgresql.JSONB, nullable=True),

        # Key locations on this floor
        sa.Column("key_locations", postgresql.JSONB, nullable=True),

        # Emergency information for this floor
        sa.Column("emergency_exits", postgresql.JSONB, nullable=True),
        sa.Column("fire_equipment", postgresql.JSONB, nullable=True),
        sa.Column("hazards", postgresql.JSONB, nullable=True),

        sa.Column("notes", sa.Text, nullable=True),

        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create indexes
    op.create_index(
        "ix_buildings_location",
        "buildings",
        ["latitude", "longitude"],
    )
    op.create_index(
        "ix_buildings_agency",
        "buildings",
        ["agency_id"],
    )
    op.create_index(
        "ix_floor_plans_building",
        "floor_plans",
        ["building_id", "floor_number"],
    )

    # Add building_id to incidents table
    op.add_column(
        "incidents",
        sa.Column(
            "building_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("buildings.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_incidents_building",
        "incidents",
        ["building_id"],
    )


def downgrade() -> None:
    # Remove building_id from incidents table
    op.drop_index("ix_incidents_building", table_name="incidents")
    op.drop_column("incidents", "building_id")

    # Drop indexes
    op.drop_index("ix_floor_plans_building", table_name="floor_plans")
    op.drop_index("ix_buildings_agency", table_name="buildings")
    op.drop_index("ix_buildings_location", table_name="buildings")

    # Drop tables
    op.drop_table("floor_plans")
    op.drop_table("buildings")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS hazardlevel")
    op.execute("DROP TYPE IF EXISTS constructiontype")
    op.execute("DROP TYPE IF EXISTS occupancytype")
    op.execute("DROP TYPE IF EXISTS buildingtype")
