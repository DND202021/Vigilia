"""Add device status history table

Revision ID: 008
Revises: 007
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create device_status_history table
    op.create_table(
        "device_status_history",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "device_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("iot_devices.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("old_status", sa.String(20), nullable=True),
        sa.Column("new_status", sa.String(20), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("connection_quality", sa.Integer, nullable=True),
    )

    # Create composite index for efficient queries
    op.create_index(
        "idx_device_status_history_device_changed",
        "device_status_history",
        ["device_id", "changed_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_device_status_history_device_changed", table_name="device_status_history")
    op.drop_table("device_status_history")
