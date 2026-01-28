"""Add emergency procedures table

Revision ID: 009
Revises: 008
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create procedure_type enum
    procedure_type_enum = postgresql.ENUM(
        "evacuation",
        "fire",
        "medical",
        "hazmat",
        "lockdown",
        "active_shooter",
        "weather",
        "utility_failure",
        name="proceduretype",
        create_type=False,
    )
    procedure_type_enum.create(op.get_bind(), checkfirst=True)

    # Create emergency_procedures table
    op.create_table(
        "emergency_procedures",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "building_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("buildings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "procedure_type",
            procedure_type_enum,
            nullable=False,
        ),
        sa.Column("priority", sa.Integer, nullable=False, server_default="3"),
        sa.Column("steps", postgresql.JSON, nullable=True),
        sa.Column("contacts", postgresql.JSON, nullable=True),
        sa.Column("equipment_needed", postgresql.JSON, nullable=True),
        sa.Column("estimated_duration_minutes", sa.Integer, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes
    op.create_index(
        "idx_emergency_procedures_building_id",
        "emergency_procedures",
        ["building_id"],
    )
    op.create_index(
        "idx_emergency_procedures_procedure_type",
        "emergency_procedures",
        ["procedure_type"],
    )
    op.create_index(
        "idx_emergency_procedures_name",
        "emergency_procedures",
        ["name"],
    )


def downgrade() -> None:
    op.drop_index("idx_emergency_procedures_name", table_name="emergency_procedures")
    op.drop_index("idx_emergency_procedures_procedure_type", table_name="emergency_procedures")
    op.drop_index("idx_emergency_procedures_building_id", table_name="emergency_procedures")
    op.drop_table("emergency_procedures")

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS proceduretype")
