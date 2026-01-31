"""Add icon_type and icon_color fields to iot_devices table.

Revision ID: 013
Revises: 012
Create Date: 2025-01-31
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add icon_type and icon_color columns to iot_devices."""
    op.add_column(
        "iot_devices",
        sa.Column("icon_type", sa.String(50), nullable=True),
    )
    op.add_column(
        "iot_devices",
        sa.Column("icon_color", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    """Remove icon_type and icon_color columns from iot_devices."""
    op.drop_column("iot_devices", "icon_color")
    op.drop_column("iot_devices", "icon_type")
