"""Add emergency_checkpoints table for Sprint 10 Emergency Response Planning

Revision ID: 011
Revises: 008
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define checkpoint type enum
checkpointtype = postgresql.ENUM(
    'assembly_point', 'muster_station', 'first_aid', 'command_post',
    'triage_area', 'decontamination', 'staging_area', 'media_point',
    name='checkpointtype',
    create_type=False,
)


def upgrade() -> None:
    # Create enum with checkfirst
    checkpointtype.create(op.get_bind(), checkfirst=True)

    # Create emergency_checkpoints table
    op.create_table(
        "emergency_checkpoints",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # Building relationship (required)
        sa.Column(
            "building_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("buildings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Floor plan relationship (optional)
        sa.Column(
            "floor_plan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("floor_plans.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Basic Information
        sa.Column("name", sa.String(200), nullable=False),
        # Checkpoint type
        sa.Column("checkpoint_type", checkpointtype, nullable=False),
        # Position on floor plan (percentage 0-100)
        sa.Column("position_x", sa.Float, nullable=False),
        sa.Column("position_y", sa.Float, nullable=False),
        # Capacity (max people at this checkpoint)
        sa.Column("capacity", sa.Integer, nullable=True),
        # Equipment at this checkpoint (JSON array)
        sa.Column("equipment", postgresql.JSONB, nullable=True),
        # Responsible person
        sa.Column("responsible_person", sa.String(200), nullable=True),
        # Contact information (JSON object)
        sa.Column("contact_info", postgresql.JSONB, nullable=True),
        # Instructions for emergency responders
        sa.Column("instructions", sa.Text, nullable=True),
        # Active status
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Create indexes
    op.create_index(
        "ix_emergency_checkpoints_building_id",
        "emergency_checkpoints",
        ["building_id"],
    )
    op.create_index(
        "ix_emergency_checkpoints_floor_plan_id",
        "emergency_checkpoints",
        ["floor_plan_id"],
    )
    op.create_index(
        "ix_emergency_checkpoints_checkpoint_type",
        "emergency_checkpoints",
        ["checkpoint_type"],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_emergency_checkpoints_checkpoint_type", table_name="emergency_checkpoints")
    op.drop_index("ix_emergency_checkpoints_floor_plan_id", table_name="emergency_checkpoints")
    op.drop_index("ix_emergency_checkpoints_building_id", table_name="emergency_checkpoints")

    # Drop table
    op.drop_table("emergency_checkpoints")

    # Drop enum
    checkpointtype.drop(op.get_bind(), checkfirst=True)
