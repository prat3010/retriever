"""Add scores JSONB column to chat_message_feedback.

Revision ID: 9b2c3d4e5f6a
Revises: 7c3d4e5f6a7b, 9a0b1c2d3e4f
Create Date: 2026-07-15 20:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9b2c3d4e5f6a"
down_revision: str | None = ("7c3d4e5f6a7b", "9a0b1c2d3e4f")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chat_message_feedback",
        sa.Column("scores", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_message_feedback", "scores")
