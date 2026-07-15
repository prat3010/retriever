"""Add cost_usd column to inference_logs.

Revision ID: 7b3c4d5e6f8g
Revises: 4a2b3c5d6e7f
Create Date: 2026-07-15 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7b3c4d5e6f8g"
down_revision: str | None = "4a2b3c5d6e7f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "inference_logs",
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default=sa.text("0.0")),
    )


def downgrade() -> None:
    op.drop_column("inference_logs", "cost_usd")
