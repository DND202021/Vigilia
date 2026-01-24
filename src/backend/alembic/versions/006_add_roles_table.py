"""Add roles table and migrate users to new role system

Revision ID: 002
Revises: 001
Create Date: 2025-01-23

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Default system roles to seed
DEFAULT_ROLES = [
    {
        "id": str(uuid.uuid4()),
        "name": "system_admin",
        "display_name": "System Administrator",
        "description": "Full system access with all permissions",
        "hierarchy_level": 0,
        "color": "red",
        "is_system_role": True,
        "is_active": True,
        "permissions": ["system:admin"],
    },
    {
        "id": str(uuid.uuid4()),
        "name": "agency_admin",
        "display_name": "Agency Administrator",
        "description": "Manage agency users, view all incidents and resources",
        "hierarchy_level": 10,
        "color": "purple",
        "is_system_role": True,
        "is_active": True,
        "permissions": [
            "users:read",
            "users:create",
            "users:update",
            "users:manage_agency",
            "roles:read",
            "incidents:*",
            "resources:*",
            "alerts:*",
        ],
    },
    {
        "id": str(uuid.uuid4()),
        "name": "commander",
        "display_name": "Commander",
        "description": "Incident command with full operational authority",
        "hierarchy_level": 20,
        "color": "blue",
        "is_system_role": True,
        "is_active": True,
        "permissions": [
            "incidents:*",
            "resources:*",
            "alerts:*",
            "users:read",
        ],
    },
    {
        "id": str(uuid.uuid4()),
        "name": "dispatcher",
        "display_name": "Dispatcher",
        "description": "Dispatch operations and alert management",
        "hierarchy_level": 30,
        "color": "green",
        "is_system_role": True,
        "is_active": True,
        "permissions": [
            "incidents:read",
            "incidents:create",
            "incidents:update",
            "incidents:assign",
            "resources:read",
            "alerts:*",
        ],
    },
    {
        "id": str(uuid.uuid4()),
        "name": "field_unit_leader",
        "display_name": "Field Unit Leader",
        "description": "Lead field operations and manage assigned resources",
        "hierarchy_level": 40,
        "color": "orange",
        "is_system_role": True,
        "is_active": True,
        "permissions": [
            "incidents:read",
            "incidents:update",
            "resources:read",
            "resources:update",
            "alerts:read",
            "alerts:acknowledge",
        ],
    },
    {
        "id": str(uuid.uuid4()),
        "name": "responder",
        "display_name": "Responder",
        "description": "Field responder with basic operational access",
        "hierarchy_level": 50,
        "color": "gray",
        "is_system_role": True,
        "is_active": True,
        "permissions": [
            "incidents:read",
            "resources:read",
            "alerts:read",
        ],
    },
    {
        "id": str(uuid.uuid4()),
        "name": "public_user",
        "display_name": "Public User",
        "description": "Limited public access for reporting",
        "hierarchy_level": 100,
        "color": "slate",
        "is_system_role": True,
        "is_active": True,
        "permissions": [
            "incidents:report",
        ],
    },
]


def upgrade() -> None:
    # Create roles table
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(50), unique=True, nullable=False, index=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("hierarchy_level", sa.Integer, default=50, nullable=False),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column("is_system_role", sa.Boolean, default=False, nullable=False),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("permissions", postgresql.JSONB, default=[], nullable=False),  # JSONB for PostgreSQL
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Seed default system roles
    roles_table = sa.table(
        "roles",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("display_name", sa.String),
        sa.column("description", sa.String),
        sa.column("hierarchy_level", sa.Integer),
        sa.column("color", sa.String),
        sa.column("is_system_role", sa.Boolean),
        sa.column("is_active", sa.Boolean),
        sa.column("permissions", postgresql.JSONB),
    )

    op.bulk_insert(roles_table, DEFAULT_ROLES)

    # Add role_id column to users table
    op.add_column(
        "users",
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_users_role_id", "users", ["role_id"])
    op.create_foreign_key(
        "fk_users_role_id",
        "users",
        "roles",
        ["role_id"],
        ["id"],
    )

    # Migrate existing users to new role system
    # Map legacy role enum values to new role records
    conn = op.get_bind()

    # Get role IDs by name
    result = conn.execute(sa.text("SELECT id, name FROM roles"))
    role_mapping = {row[1]: row[0] for row in result}

    # Update each user's role_id based on their legacy role
    for legacy_role, role_id in role_mapping.items():
        conn.execute(
            sa.text(
                "UPDATE users SET role_id = :role_id WHERE role = :legacy_role"
            ),
            {"role_id": role_id, "legacy_role": legacy_role},
        )


def downgrade() -> None:
    # Remove foreign key and column from users
    op.drop_constraint("fk_users_role_id", "users", type_="foreignkey")
    op.drop_index("ix_users_role_id", "users")
    op.drop_column("users", "role_id")

    # Drop roles table
    op.drop_table("roles")
