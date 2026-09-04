"""Create compiled_prompt_programs table for Milestone 92.

Revision ID: g1h2i3j4k5l6
Revises: f1a2b3c4d5e6
Create Date: 2026-09-04 16:50:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "g1h2i3j4k5l6"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "compiled_prompt_programs",
        sa.Column("program_id", sa.String(128), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(128), nullable=False, server_default="rag_cot_optimized"),
        sa.Column("signature_name", sa.String(128), nullable=False, server_default="RAGAnswerSignature"),
        sa.Column("optimizer", sa.String(64), nullable=False, server_default="BootstrapFewShot"),
        sa.Column("dataset_id", sa.String(128), nullable=True),
        sa.Column("baseline_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("compiled_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("improvement_pct", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("metric_name", sa.String(64), nullable=False, server_default="faithfulness_and_relevancy"),
        sa.Column("compiled_instruction", sa.Text(), nullable=False, server_default=""),
        sa.Column("few_shot_demos", JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_compiled_prompts_tenant",
        "compiled_prompt_programs",
        ["tenant_id"],
    )
    op.create_index(
        "ix_compiled_prompts_tenant_active",
        "compiled_prompt_programs",
        ["tenant_id", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_compiled_prompts_tenant_active", table_name="compiled_prompt_programs")
    op.drop_index("ix_compiled_prompts_tenant", table_name="compiled_prompt_programs")
    op.drop_table("compiled_prompt_programs")
