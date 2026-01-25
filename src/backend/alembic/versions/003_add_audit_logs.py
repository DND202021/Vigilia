"""Add audit_logs table

Revision ID: 003
Revises: 002
Create Date: 2026-01-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define enum type
auditaction_enum = postgresql.ENUM(
    "login", "logout", "login_failed", "password_changed",
    "mfa_enabled", "mfa_disabled",
    "user_created", "user_updated", "user_deleted", "user_role_changed",
    "incident_created", "incident_updated", "incident_assigned",
    "incident_escalated", "incident_closed",
    "alert_received", "alert_acknowledged", "alert_dismissed", "alert_to_incident",
    "resource_created", "resource_updated", "resource_deleted",
    "resource_assigned", "resource_status_changed",
    "system_config_changed", "api_access", "permission_denied",
    name="auditaction",
    create_type=False,
)


def upgrade() -> None:
    # Create audit action enum
    auditaction_enum.create(op.get_bind(), checkfirst=True)

    # Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("action", auditaction_enum, nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("entity_type", sa.String(50), nullable=True, index=True),
        sa.Column("entity_id", sa.String(50), nullable=True, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("old_values", postgresql.JSONB, nullable=True),
        sa.Column("new_values", postgresql.JSONB, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
    )

    # Create composite indexes
    op.create_index(
        "ix_audit_logs_entity",
        "audit_logs",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "ix_audit_logs_timestamp_action",
        "audit_logs",
        ["timestamp", "action"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_timestamp_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    op.drop_table("audit_logs")
    auditaction_enum.drop(op.get_bind(), checkfirst=True)
