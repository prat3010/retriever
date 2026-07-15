"""Add notes column to inference_logs.

Revision ID: 5a1b2c3d4e5f
Revises: 7b3c4d5e6f8g
Create Date: 2026-07-15 16:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5a1b2c3d4e5f"
down_revision: str | None = "7b3c4d5e6f8g"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "inference_logs",
        sa.Column("notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("inference_logs", "notes")
