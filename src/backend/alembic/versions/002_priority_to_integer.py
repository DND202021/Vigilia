"""Change incident priority from enum to integer

Revision ID: 002
Revises: 001
Create Date: 2026-01-12

This migration documents the change from enum-based priority
to integer-based priority (1=Critical, 5=Low).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert priority column from enum to integer
    # Note: If database already has this change, this will be a no-op
    op.execute("""
        ALTER TABLE incidents
        ALTER COLUMN priority TYPE INTEGER
        USING CASE priority::text
            WHEN '1' THEN 1
            WHEN '2' THEN 2
            WHEN '3' THEN 3
            WHEN '4' THEN 4
            WHEN '5' THEN 5
            ELSE 3
        END
    """)

    # Drop the old enum type if it exists
    op.execute("DROP TYPE IF EXISTS incidentpriority")


def downgrade() -> None:
    # Recreate the enum type
    op.execute("""
        CREATE TYPE incidentpriority AS ENUM ('1', '2', '3', '4', '5')
    """)

    # Convert back to enum
    op.execute("""
        ALTER TABLE incidents
        ALTER COLUMN priority TYPE incidentpriority
        USING priority::text::incidentpriority
    """)
