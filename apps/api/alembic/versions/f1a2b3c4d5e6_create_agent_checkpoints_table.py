"""Create agent_checkpoints table for Milestone 91.

Revision ID: f1a2b3c4d5e6
Revises: e2f1a3b4c5d6
Create Date: 2026-09-04 16:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e2f1a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_checkpoints",
        sa.Column("checkpoint_id", sa.String(128), primary_key=True),
        sa.Column("thread_id", sa.String(128), nullable=False),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("node_name", sa.String(64), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("state_snapshot", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "ix_agent_checkpoints_tenant_thread",
        "agent_checkpoints",
        ["tenant_id", "thread_id"],
    )
    op.create_index(
        "ix_agent_checkpoints_thread_step",
        "agent_checkpoints",
        ["thread_id", "step_index"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_checkpoints_thread_step", table_name="agent_checkpoints")
    op.drop_index("ix_agent_checkpoints_tenant_thread", table_name="agent_checkpoints")
    op.drop_table("agent_checkpoints")
