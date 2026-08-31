"""Add hybrid_alpha, active_lora_adapter and tenant_lora_adapters table.

Revision ID: 8a0b1c2d3e4f
Revises: 7e9f1a2b3c4d
Create Date: 2026-08-31 10:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "8a0b1c2d3e4f"
down_revision: str | None = "7e9f1a2b3c4d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add hybrid_alpha and active_lora_adapter to tenant_configs
    op.add_column(
        "tenant_configs",
        sa.Column("hybrid_alpha", sa.Float(), nullable=False, server_default=sa.text("0.7")),
    )
    op.add_column(
        "tenant_configs",
        sa.Column("active_lora_adapter", sa.String(255), nullable=True),
    )

    # 2. Create tenant_lora_adapters table
    op.create_table(
        "tenant_lora_adapters",
        sa.Column("adapter_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("domain_tag", sa.String(100), nullable=False, server_default="general"),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("loss_score", sa.Float(), nullable=True),
        sa.Column("weights_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("adapter_id"),
        if_not_exists=True,
    )
    op.create_index("ix_tenant_lora_adapters_tenant_id", "tenant_lora_adapters", ["tenant_id"], if_not_exists=True)
    op.create_index(
        "ix_tenant_lora_adapters_tenant_tag",
        "tenant_lora_adapters",
        ["tenant_id", "domain_tag"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_lora_adapters_tenant_tag", table_name="tenant_lora_adapters")
    op.drop_index("ix_tenant_lora_adapters_tenant_id", table_name="tenant_lora_adapters")
    op.drop_table("tenant_lora_adapters")
    op.drop_column("tenant_configs", "active_lora_adapter")
    op.drop_column("tenant_configs", "hybrid_alpha")
