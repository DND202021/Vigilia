"""Add evacuation routes table

Revision ID: 010
Revises: 008
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create evacuation_routes table
    op.create_table(
        "evacuation_routes",
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
        sa.Column(
            "floor_plan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("floor_plans.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("route_type", sa.String(50), nullable=False, server_default="primary"),
        sa.Column("waypoints", postgresql.JSON, nullable=True),
        sa.Column("color", sa.String(20), nullable=False, server_default="#ff0000"),
        sa.Column("line_width", sa.Integer, nullable=False, server_default="3"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("capacity", sa.Integer, nullable=True),
        sa.Column("estimated_time_seconds", sa.Integer, nullable=True),
        sa.Column("accessibility_features", postgresql.JSON, nullable=True),
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
    )

    # Create indexes
    op.create_index(
        "idx_evacuation_routes_building_id",
        "evacuation_routes",
        ["building_id"],
    )
    op.create_index(
        "idx_evacuation_routes_floor_plan_id",
        "evacuation_routes",
        ["floor_plan_id"],
    )
    op.create_index(
        "idx_evacuation_routes_route_type",
        "evacuation_routes",
        ["route_type"],
    )


def downgrade() -> None:
    op.drop_index("idx_evacuation_routes_route_type", table_name="evacuation_routes")
    op.drop_index("idx_evacuation_routes_floor_plan_id", table_name="evacuation_routes")
    op.drop_index("idx_evacuation_routes_building_id", table_name="evacuation_routes")
    op.drop_table("evacuation_routes")
