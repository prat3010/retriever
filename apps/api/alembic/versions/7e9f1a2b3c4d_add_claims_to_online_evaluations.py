"""Add claims JSONB column to online_evaluations table.

Revision ID: 7e9f1a2b3c4d
Revises: 6d8e0f1a2b3c
Create Date: 2026-08-31 10:15:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "7e9f1a2b3c4d"
down_revision: str | None = "6d8e0f1a2b3c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "online_evaluations",
        sa.Column("eval_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("message_id", sa.String(255), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("faithfulness", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("context_precision", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("hallucination_index", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("is_alert", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("claims", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("eval_id"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_online_evaluations_tenant_id",
        "online_evaluations",
        ["tenant_id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_online_evaluations_tenant_id", table_name="online_evaluations")
    op.drop_table("online_evaluations")
