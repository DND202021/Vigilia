"""Add IoT foundation: device profiles, credentials, twins, telemetry hypertable.

Revision ID: 016
Revises: 015
Create Date: 2026-02-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create device profiles, credentials, twins, telemetry hypertable with policies."""

    # 1. Create device_profiles table
    op.create_table(
        "device_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("device_type", sa.String(50), nullable=False, index=True),
        sa.Column("telemetry_schema", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("attributes_server", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("attributes_client", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("alert_rules", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("default_config", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create GIN indexes for JSON columns (not auto-detected by Alembic)
    op.execute("""
        CREATE INDEX ix_device_profiles_telemetry_schema_gin
        ON device_profiles USING GIN (telemetry_schema);
    """)

    op.execute("""
        CREATE INDEX ix_device_profiles_alert_rules_gin
        ON device_profiles USING GIN (alert_rules);
    """)

    # 2. Create device_credentials table
    op.create_table(
        "device_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "device_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("iot_devices.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("credential_type", sa.String(20), nullable=False, index=True),
        sa.Column("access_token_hash", sa.String(255), nullable=True),
        sa.Column("certificate_pem", sa.Text, nullable=True),
        sa.Column("certificate_cn", sa.String(255), nullable=True, index=True),
        sa.Column("certificate_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 3. Create device_twins table
    op.create_table(
        "device_twins",
        sa.Column(
            "device_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("iot_devices.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("desired_config", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("desired_version", sa.Integer, nullable=False, server_default="0"),
        sa.Column("desired_updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reported_config", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("reported_version", sa.Integer, nullable=False, server_default="0"),
        sa.Column("reported_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_synced", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 4. Create device_telemetry table (will become hypertable)
    op.create_table(
        "device_telemetry",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "device_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("iot_devices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("value_numeric", sa.Float, nullable=True),
        sa.Column("value_string", sa.String(500), nullable=True),
        sa.Column("value_bool", sa.Boolean, nullable=True),
        sa.PrimaryKeyConstraint("time", "device_id", "metric_name"),
    )

    # 5. Convert device_telemetry to hypertable
    op.execute("""
        SELECT create_hypertable(
            'device_telemetry',
            by_range('time'),
            chunk_time_interval => INTERVAL '7 days',
            if_not_exists => TRUE
        );
    """)

    # 6. Add indexes on device_telemetry
    op.create_index(
        "ix_device_telemetry_device_time",
        "device_telemetry",
        ["device_id", "time"],
    )
    op.create_index(
        "ix_device_telemetry_metric",
        "device_telemetry",
        ["metric_name"],
    )

    # 7. Add compression policy
    op.execute("""
        ALTER TABLE device_telemetry SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'device_id,metric_name'
        );
    """)

    op.execute("""
        SELECT add_compression_policy(
            'device_telemetry',
            compress_after => INTERVAL '7 days'
        );
    """)

    # 8. Add retention policy
    op.execute("""
        SELECT add_retention_policy(
            'device_telemetry',
            drop_after => INTERVAL '90 days'
        );
    """)

    # 9. Create hourly continuous aggregate
    op.execute("""
        CREATE MATERIALIZED VIEW device_telemetry_hourly
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket('1 hour', time) AS bucket,
            device_id,
            metric_name,
            AVG(value_numeric) AS avg_value,
            MIN(value_numeric) AS min_value,
            MAX(value_numeric) AS max_value,
            COUNT(*) AS reading_count
        FROM device_telemetry
        GROUP BY bucket, device_id, metric_name;
    """)

    # 10. Add refresh policy for hourly aggregate
    op.execute("""
        SELECT add_continuous_aggregate_policy(
            'device_telemetry_hourly',
            start_offset => INTERVAL '3 hours',
            end_offset => INTERVAL '1 hour',
            schedule_interval => INTERVAL '30 minutes'
        );
    """)

    # 11. Add compression on hourly aggregate
    op.execute("""
        ALTER MATERIALIZED VIEW device_telemetry_hourly
        SET (timescaledb.compress = true);
    """)

    op.execute("""
        SELECT add_compression_policy(
            'device_telemetry_hourly',
            compress_after => INTERVAL '7 days'
        );
    """)

    # 12. Create daily continuous aggregate
    op.execute("""
        CREATE MATERIALIZED VIEW device_telemetry_daily
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket('1 day', time) AS bucket,
            device_id,
            metric_name,
            AVG(value_numeric) AS avg_value,
            MIN(value_numeric) AS min_value,
            MAX(value_numeric) AS max_value,
            COUNT(*) AS reading_count
        FROM device_telemetry
        GROUP BY bucket, device_id, metric_name;
    """)

    # 13. Add refresh policy for daily aggregate
    op.execute("""
        SELECT add_continuous_aggregate_policy(
            'device_telemetry_daily',
            start_offset => INTERVAL '7 days',
            end_offset => INTERVAL '1 day',
            schedule_interval => INTERVAL '12 hours'
        );
    """)

    # 14. Add compression on daily aggregate
    op.execute("""
        ALTER MATERIALIZED VIEW device_telemetry_daily
        SET (timescaledb.compress = true);
    """)

    op.execute("""
        SELECT add_compression_policy(
            'device_telemetry_daily',
            compress_after => INTERVAL '30 days'
        );
    """)

    # 15. Add profile_id and provisioning_status columns to iot_devices
    op.add_column(
        "iot_devices",
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("device_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "iot_devices",
        sa.Column(
            "provisioning_status",
            sa.String(20),
            nullable=True,
            server_default="unprovisioned",
        ),
    )
    op.create_index("ix_iot_devices_profile_id", "iot_devices", ["profile_id"])
    op.create_index("ix_iot_devices_provisioning_status", "iot_devices", ["provisioning_status"])


def downgrade() -> None:
    """Drop all IoT foundation tables and views."""

    # Drop columns from iot_devices
    op.drop_index("ix_iot_devices_provisioning_status", "iot_devices")
    op.drop_index("ix_iot_devices_profile_id", "iot_devices")
    op.drop_column("iot_devices", "provisioning_status")
    op.drop_column("iot_devices", "profile_id")

    # Drop materialized views (CASCADE removes policies)
    op.execute("DROP MATERIALIZED VIEW IF EXISTS device_telemetry_daily CASCADE;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS device_telemetry_hourly CASCADE;")

    # Drop device_telemetry table
    op.drop_index("ix_device_telemetry_metric", "device_telemetry")
    op.drop_index("ix_device_telemetry_device_time", "device_telemetry")
    op.drop_table("device_telemetry")

    # Drop device_twins table
    op.drop_table("device_twins")

    # Drop device_credentials table
    op.drop_table("device_credentials")

    # Drop device_profiles table (GIN indexes are dropped automatically)
    op.drop_table("device_profiles")
