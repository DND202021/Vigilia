"""Add building_documents, building_photos, and inspections tables for Sprint 6

Revision ID: 012
Revises: 011
Create Date: 2026-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define enums
document_category = postgresql.ENUM(
    'pre_plan', 'floor_plan', 'permit', 'inspection', 'manual', 'other',
    name='documentcategory',
    create_type=False,
)

inspection_type = postgresql.ENUM(
    'fire_safety', 'structural', 'hazmat', 'general',
    name='inspectiontype',
    create_type=False,
)

inspection_status = postgresql.ENUM(
    'scheduled', 'in_progress', 'completed', 'failed', 'overdue',
    name='inspectionstatus',
    create_type=False,
)


def upgrade() -> None:
    # Create enums
    document_category.create(op.get_bind(), checkfirst=True)
    inspection_type.create(op.get_bind(), checkfirst=True)
    inspection_status.create(op.get_bind(), checkfirst=True)

    # Create building_documents table
    op.create_table(
        "building_documents",
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
        sa.Column("category", document_category, nullable=False, server_default="other"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("file_url", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=True),
        sa.Column("file_size", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "uploaded_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
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

    op.create_index(
        "ix_building_documents_building_id",
        "building_documents",
        ["building_id"],
    )

    # Create building_photos table
    op.create_table(
        "building_photos",
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
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("file_url", sa.String(500), nullable=False),
        sa.Column("thumbnail_url", sa.String(500), nullable=True),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "uploaded_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("tags", postgresql.JSON, nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_building_photos_building_id",
        "building_photos",
        ["building_id"],
    )
    op.create_index(
        "ix_building_photos_floor_plan_id",
        "building_photos",
        ["floor_plan_id"],
    )

    # Create inspections table
    op.create_table(
        "inspections",
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
        sa.Column("inspection_type", inspection_type, nullable=False),
        sa.Column("scheduled_date", sa.Date, nullable=False),
        sa.Column("completed_date", sa.Date, nullable=True),
        sa.Column("status", inspection_status, nullable=False, server_default="scheduled"),
        sa.Column("inspector_name", sa.String(255), nullable=False),
        sa.Column("findings", sa.Text, nullable=True),
        sa.Column("follow_up_required", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("follow_up_date", sa.Date, nullable=True),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
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

    op.create_index(
        "ix_inspections_building_id",
        "inspections",
        ["building_id"],
    )
    op.create_index(
        "ix_inspections_scheduled_date",
        "inspections",
        ["scheduled_date"],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_inspections_scheduled_date", table_name="inspections")
    op.drop_index("ix_inspections_building_id", table_name="inspections")
    op.drop_index("ix_building_photos_floor_plan_id", table_name="building_photos")
    op.drop_index("ix_building_photos_building_id", table_name="building_photos")
    op.drop_index("ix_building_documents_building_id", table_name="building_documents")

    # Drop tables
    op.drop_table("inspections")
    op.drop_table("building_photos")
    op.drop_table("building_documents")

    # Drop enums
    inspection_status.drop(op.get_bind(), checkfirst=True)
    inspection_type.drop(op.get_bind(), checkfirst=True)
    document_category.drop(op.get_bind(), checkfirst=True)
