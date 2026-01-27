"""Add IoT devices, audio clips, and notification preferences tables

Revision ID: 007
Revises: 006
Create Date: 2026-01-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create iot_devices table
    op.create_table(
        "iot_devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False, index=True),
        sa.Column("device_type", sa.String(20), nullable=False, index=True),
        sa.Column("serial_number", sa.String(100), nullable=True, unique=True, index=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("mac_address", sa.String(17), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("firmware_version", sa.String(50), nullable=True),
        sa.Column("manufacturer", sa.String(100), nullable=False, server_default="Axis"),
        sa.Column("building_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("floor_plan_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("floor_plans.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("position_x", sa.Float, nullable=True),
        sa.Column("position_y", sa.Float, nullable=True),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        sa.Column("location_name", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="offline", index=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connection_quality", sa.Integer, nullable=True),
        sa.Column("config", sa.JSON, server_default="{}"),
        sa.Column("capabilities", sa.JSON, server_default="[]"),
        sa.Column("metadata_extra", sa.JSON, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create audio_clips table
    op.create_table(
        "audio_clips",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("iot_devices.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("format", sa.String(20), nullable=False, server_default="wav"),
        sa.Column("sample_rate", sa.Integer, nullable=False, server_default="16000"),
        sa.Column("event_type", sa.String(50), nullable=False, index=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("peak_level_db", sa.Float, nullable=True),
        sa.Column("background_level_db", sa.Float, nullable=True),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_extra", sa.JSON, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    # Create notification_preferences table
    op.create_table(
        "notification_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("call_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sms_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("email_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("push_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("building_ids", sa.JSON, server_default="[]"),
        sa.Column("min_severity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("quiet_start", sa.Time, nullable=True),
        sa.Column("quiet_end", sa.Time, nullable=True),
        sa.Column("quiet_override_critical", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    # Add new columns to alerts table for IoT device integration
    op.add_column("alerts", sa.Column(
        "device_id", postgresql.UUID(as_uuid=True),
        sa.ForeignKey("iot_devices.id", ondelete="SET NULL"), nullable=True))
    op.add_column("alerts", sa.Column(
        "building_id", postgresql.UUID(as_uuid=True),
        sa.ForeignKey("buildings.id", ondelete="SET NULL"), nullable=True))
    op.add_column("alerts", sa.Column(
        "floor_plan_id", postgresql.UUID(as_uuid=True),
        sa.ForeignKey("floor_plans.id", ondelete="SET NULL"), nullable=True))
    op.add_column("alerts", sa.Column(
        "audio_clip_id", postgresql.UUID(as_uuid=True),
        sa.ForeignKey("audio_clips.id", ondelete="SET NULL"), nullable=True))
    op.add_column("alerts", sa.Column("peak_level_db", sa.Float, nullable=True))
    op.add_column("alerts", sa.Column("background_level_db", sa.Float, nullable=True))
    op.add_column("alerts", sa.Column("confidence", sa.Float, nullable=True))
    op.add_column("alerts", sa.Column("risk_level", sa.String(20), nullable=True))
    op.add_column("alerts", sa.Column(
        "occurrence_count", sa.Integer, nullable=False, server_default="1"))
    op.add_column("alerts", sa.Column(
        "last_occurrence", sa.DateTime(timezone=True), nullable=True))
    op.add_column("alerts", sa.Column(
        "assigned_to_id", postgresql.UUID(as_uuid=True),
        sa.ForeignKey("users.id"), nullable=True))

    # Create indexes on new alert columns
    op.create_index("idx_alerts_device_id", "alerts", ["device_id"])
    op.create_index("idx_alerts_building_id", "alerts", ["building_id"])


def downgrade() -> None:
    # Drop indexes on alert columns
    op.drop_index("idx_alerts_building_id", table_name="alerts")
    op.drop_index("idx_alerts_device_id", table_name="alerts")

    # Drop new columns from alerts
    op.drop_column("alerts", "assigned_to_id")
    op.drop_column("alerts", "last_occurrence")
    op.drop_column("alerts", "occurrence_count")
    op.drop_column("alerts", "risk_level")
    op.drop_column("alerts", "confidence")
    op.drop_column("alerts", "background_level_db")
    op.drop_column("alerts", "peak_level_db")
    op.drop_column("alerts", "audio_clip_id")
    op.drop_column("alerts", "floor_plan_id")
    op.drop_column("alerts", "building_id")
    op.drop_column("alerts", "device_id")

    # Drop new tables
    op.drop_table("notification_preferences")
    op.drop_table("audio_clips")
    op.drop_table("iot_devices")
