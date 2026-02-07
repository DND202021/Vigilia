"""Add IOT_TELEMETRY to AlertSource enum.

Revision ID: 017
Revises: 016
Create Date: 2026-02-07
"""

from alembic import op

# revision identifiers
revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add iot_telemetry value to alertsource PostgreSQL enum."""
    op.execute("ALTER TYPE alertsource ADD VALUE IF NOT EXISTS 'iot_telemetry'")


def downgrade() -> None:
    """PostgreSQL does not support removing enum values."""
    pass
