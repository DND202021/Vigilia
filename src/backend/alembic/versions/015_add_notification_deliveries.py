"""Add notification_deliveries table for delivery tracking.

Revision ID: 015
Revises: 014
Create Date: 2026-02-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create notification_deliveries table with indexes and foreign keys."""
    op.create_table(
        "notification_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "alert_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("alerts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column(
            "external_id",
            sa.String(255),
            nullable=True,
            comment="SendGrid message ID, Twilio SID, etc.",
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Create indexes for common query patterns
    op.create_index(
        "ix_notification_deliveries_alert_id",
        "notification_deliveries",
        ["alert_id"],
    )
    op.create_index(
        "ix_notification_deliveries_user_id",
        "notification_deliveries",
        ["user_id"],
    )
    op.create_index(
        "ix_notification_deliveries_status",
        "notification_deliveries",
        ["status"],
    )
    op.create_index(
        "ix_notification_deliveries_alert_status",
        "notification_deliveries",
        ["alert_id", "status"],
    )
    op.create_index(
        "ix_notification_deliveries_user_status",
        "notification_deliveries",
        ["user_id", "status"],
    )


def downgrade() -> None:
    """Drop notification_deliveries table and all indexes."""
    op.drop_index("ix_notification_deliveries_user_status", "notification_deliveries")
    op.drop_index("ix_notification_deliveries_alert_status", "notification_deliveries")
    op.drop_index("ix_notification_deliveries_status", "notification_deliveries")
    op.drop_index("ix_notification_deliveries_user_id", "notification_deliveries")
    op.drop_index("ix_notification_deliveries_alert_id", "notification_deliveries")
    op.drop_table("notification_deliveries")
