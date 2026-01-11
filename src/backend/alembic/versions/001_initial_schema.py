"""Initial schema for ERIOP

Revision ID: 001
Revises:
Create Date: 2025-01-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create agencies table
    op.create_table(
        "agencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("settings", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("badge_number", sa.String(50), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column(
            "role",
            sa.Enum(
                "system_admin", "agency_admin", "commander", "dispatcher",
                "field_unit_leader", "responder", "public_user",
                name="userrole"
            ),
            default="responder",
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("is_verified", sa.Boolean, default=False, nullable=False),
        sa.Column("mfa_enabled", sa.Boolean, default=False, nullable=False),
        sa.Column("mfa_secret", sa.String(255), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer, default=0, nullable=False),
        sa.Column("locked_until", sa.String(50), nullable=True),
        sa.Column("agency_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agencies.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create alerts table
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source",
            sa.Enum(
                "fundamentum", "alarm_system", "axis_microphone",
                "security_system", "manual", "external_api",
                name="alertsource"
            ),
            nullable=False,
            index=True,
        ),
        sa.Column("source_id", sa.String(255), nullable=True, index=True),
        sa.Column("source_device_id", sa.String(255), nullable=True),
        sa.Column(
            "severity",
            sa.Enum("critical", "high", "medium", "low", "info", name="alertseverity"),
            default="medium",
            nullable=False,
            index=True,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "acknowledged", "processing", "resolved", "dismissed", name="alertstatus"),
            default="pending",
            nullable=False,
            index=True,
        ),
        sa.Column("alert_type", sa.String(100), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("zone", sa.String(100), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB, nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("acknowledgment_notes", sa.Text, nullable=True),
        sa.Column("dismissed_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("dismissal_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create incidents table
    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_number", sa.String(50), unique=True, nullable=False, index=True),
        sa.Column(
            "category",
            sa.Enum(
                "fire", "medical", "police", "rescue", "traffic", "weather",
                "hazmat", "utility", "intrusion", "assault", "theft", "threat",
                "welfare_check", "civil_assistance", "training", "other",
                name="incidentcategory"
            ),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Enum("1", "2", "3", "4", "5", name="incidentpriority"),
            default="3",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("new", "assigned", "en_route", "on_scene", "resolved", "closed", name="incidentstatus"),
            default="new",
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("building_info", sa.Text, nullable=True),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("arrived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_units", postgresql.JSONB, default=[]),
        sa.Column("parent_incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id"), nullable=True),
        sa.Column("agency_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agencies.id"), nullable=False),
        sa.Column("source_alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alerts.id"), nullable=True),
        sa.Column("timeline_events", postgresql.JSONB, default=[]),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create resources table (base)
    op.create_table(
        "resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "resource_type",
            sa.Enum("personnel", "vehicle", "equipment", name="resourcetype"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "available", "assigned", "en_route", "on_scene",
                "off_duty", "out_of_service",
                name="resourcestatus"
            ),
            default="available",
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("call_sign", sa.String(50), nullable=True),
        sa.Column("current_latitude", sa.Float, nullable=True),
        sa.Column("current_longitude", sa.Float, nullable=True),
        sa.Column("location_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("agency_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agencies.id"), nullable=False),
        sa.Column("metadata", postgresql.JSONB, default={}),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create personnel table
    op.create_table(
        "personnel",
        sa.Column("id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resources.id"), primary_key=True),
        sa.Column("badge_number", sa.String(50), nullable=False),
        sa.Column("rank", sa.String(100), nullable=True),
        sa.Column("specializations", postgresql.JSONB, default=[]),
        sa.Column("certifications", postgresql.JSONB, default=[]),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("assigned_vehicle_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Create vehicles table
    op.create_table(
        "vehicles",
        sa.Column("id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resources.id"), primary_key=True),
        sa.Column("vehicle_type", sa.String(100), nullable=False),
        sa.Column("make", sa.String(100), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("year", sa.Integer, nullable=True),
        sa.Column("license_plate", sa.String(20), nullable=True),
        sa.Column("vin", sa.String(50), nullable=True),
        sa.Column("equipment_inventory", postgresql.JSONB, default=[]),
        sa.Column("last_maintenance_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_maintenance_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create equipment table
    op.create_table(
        "equipment",
        sa.Column("id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resources.id"), primary_key=True),
        sa.Column("equipment_type", sa.String(100), nullable=False),
        sa.Column("serial_number", sa.String(100), nullable=True),
        sa.Column("manufacturer", sa.String(100), nullable=True),
        sa.Column("assigned_to_personnel_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_to_vehicle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_inspection_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_inspection_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("equipment")
    op.drop_table("vehicles")
    op.drop_table("personnel")
    op.drop_table("resources")
    op.drop_table("incidents")
    op.drop_table("alerts")
    op.drop_table("users")
    op.drop_table("agencies")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS alertsource")
    op.execute("DROP TYPE IF EXISTS alertseverity")
    op.execute("DROP TYPE IF EXISTS alertstatus")
    op.execute("DROP TYPE IF EXISTS incidentcategory")
    op.execute("DROP TYPE IF EXISTS incidentpriority")
    op.execute("DROP TYPE IF EXISTS incidentstatus")
    op.execute("DROP TYPE IF EXISTS resourcetype")
    op.execute("DROP TYPE IF EXISTS resourcestatus")
