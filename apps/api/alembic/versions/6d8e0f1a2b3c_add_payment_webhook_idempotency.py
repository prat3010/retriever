"""Add payment webhook idempotency constraint.

Revision ID: 6d8e0f1a2b3c
Revises: 4c7d8e9f0a1b
Create Date: 2026-08-19 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "6d8e0f1a2b3c"
down_revision: str | None = "4c7d8e9f0a1b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payment_transactions",
        sa.Column("transaction_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(50), nullable=False, server_default="completed"),
        sa.Column("external_reference", sa.String(255), nullable=True),
        sa.Column("meta_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("transaction_id"),
        if_not_exists=True,
    )
    op.create_index(
        "uq_payment_transactions_provider_external_reference",
        "payment_transactions",
        ["provider", "external_reference"],
        unique=True,
        postgresql_where="external_reference IS NOT NULL",
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_payment_transactions_provider_external_reference",
        table_name="payment_transactions",
    )
    op.drop_table("payment_transactions")
