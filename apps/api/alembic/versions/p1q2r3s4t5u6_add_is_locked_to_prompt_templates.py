"""Add is_locked to prompt_templates table.

Revision ID: p1q2r3s4t5u6
Revises: o1p2q3r4s5t6
Create Date: 2026-09-28 19:50:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "p1q2r3s4t5u6"
down_revision: str | None = "o1p2q3r4s5t6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE prompt_templates 
        ADD COLUMN IF NOT EXISTS is_locked BOOLEAN NOT NULL DEFAULT FALSE;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE prompt_templates 
        DROP COLUMN IF EXISTS is_locked;
    """)
