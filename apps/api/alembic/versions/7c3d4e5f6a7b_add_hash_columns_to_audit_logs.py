"""Add entry_hash and previous_hash columns to audit_logs.

Revision ID: 7c3d4e5f6a7b
Revises: 6b2c3d4e5f6a
Create Date: 2026-07-15 16:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7c3d4e5f6a7b"
down_revision: str | None = "6b2c3d4e5f6a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("entry_hash", sa.String(64), nullable=True))
    op.add_column("audit_logs", sa.Column("previous_hash", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("audit_logs", "previous_hash")
    op.drop_column("audit_logs", "entry_hash")
