"""Add reranker_engine column to tenant_configs table.

Revision ID: 9b0c1d2e3f4a
Revises: 8a0b1c2d3e4f
Create Date: 2026-08-31 11:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9b0c1d2e3f4a"
down_revision: str | None = "8a0b1c2d3e4f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenant_configs",
        sa.Column(
            "reranker_engine",
            sa.String(50),
            nullable=False,
            server_default="cohere",
        ),
    )


def downgrade() -> None:
    op.drop_column("tenant_configs", "reranker_engine")
