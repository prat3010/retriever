"""Add LLM LoRA metadata columns to tenant_lora_adapters for Milestone 96.

Revision ID: i1j2k3l4m5n6
Revises: h1i2j3k4l5m6
Create Date: 2026-09-05 02:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "i1j2k3l4m5n6"
down_revision: str | None = "h1i2j3k4l5m6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenant_lora_adapters",
        sa.Column("adapter_type", sa.String(50), nullable=False, server_default="embedding"),
    )
    op.add_column(
        "tenant_lora_adapters",
        sa.Column("base_model", sa.String(255), nullable=True),
    )
    op.add_column(
        "tenant_lora_adapters",
        sa.Column("artifact_uri", sa.String(500), nullable=True),
    )
    op.add_column(
        "tenant_lora_adapters",
        sa.Column("alpha", sa.Float(), nullable=True, server_default=sa.text("16.0")),
    )
    op.add_column(
        "tenant_lora_adapters",
        sa.Column("target_modules", JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column(
        "tenant_lora_adapters",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("tenant_lora_adapters", "is_active")
    op.drop_column("tenant_lora_adapters", "target_modules")
    op.drop_column("tenant_lora_adapters", "alpha")
    op.drop_column("tenant_lora_adapters", "artifact_uri")
    op.drop_column("tenant_lora_adapters", "base_model")
    op.drop_column("tenant_lora_adapters", "adapter_type")
