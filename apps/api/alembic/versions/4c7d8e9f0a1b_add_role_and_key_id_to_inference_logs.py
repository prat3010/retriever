"""Add role and key_id columns to inference_logs.

Revision ID: 4c7d8e9f0a1b
Revises: 9b2c3d4e5f6a
Create Date: 2026-07-21 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "4c7d8e9f0a1b"
down_revision: str | None = "9b2c3d4e5f6a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "inference_logs",
        sa.Column("role", sa.String(50), nullable=True),
    )
    op.add_column(
        "inference_logs",
        sa.Column(
            "key_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("api_keys.key_id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_inference_logs_key_id", "inference_logs", ["key_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_inference_logs_key_id", table_name="inference_logs")
    op.drop_column("inference_logs", "key_id")
    op.drop_column("inference_logs", "role")
