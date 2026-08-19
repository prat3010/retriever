"""Add payment webhook idempotency constraint.

Revision ID: 6d8e0f1a2b3c
Revises: 4c7d8e9f0a1b
Create Date: 2026-08-19 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "6d8e0f1a2b3c"
down_revision: str | None = "4c7d8e9f0a1b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_payment_transactions_provider_external_reference",
        "payment_transactions",
        ["provider", "external_reference"],
        unique=True,
        postgresql_where="external_reference IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_index(
        "uq_payment_transactions_provider_external_reference",
        table_name="payment_transactions",
    )
