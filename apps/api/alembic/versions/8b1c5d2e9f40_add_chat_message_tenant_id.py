"""Add tenant isolation to chat messages.

Revision ID: 8b1c5d2e9f40
Revises: 7a7ee5dd77dd
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8b1c5d2e9f40"
down_revision: str | Sequence[str] | None = "7a7ee5dd77dd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Backfill tenant ownership from the parent session before enforcing RLS."""
    op.add_column("chat_messages", sa.Column("tenant_id", sa.UUID(), nullable=True))
    op.execute(
        """
        UPDATE chat_messages AS message
        SET tenant_id = session.tenant_id
        FROM chat_sessions AS session
        WHERE message.session_id = session.session_id
        """
    )
    op.alter_column("chat_messages", "tenant_id", nullable=False)
    op.create_foreign_key(
        "fk_chat_messages_tenant_id_tenants",
        "chat_messages",
        "tenants",
        ["tenant_id"],
        ["tenant_id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_chat_sessions_session_tenant",
        "chat_sessions",
        ["session_id", "tenant_id"],
    )
    op.drop_constraint("chat_messages_session_id_fkey", "chat_messages", type_="foreignkey")
    op.create_foreign_key(
        "fk_chat_messages_session_tenant",
        "chat_messages",
        "chat_sessions",
        ["session_id", "tenant_id"],
        ["session_id", "tenant_id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_chat_messages_tenant_id", "chat_messages", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_tenant_id", table_name="chat_messages")
    op.drop_constraint("fk_chat_messages_session_tenant", "chat_messages", type_="foreignkey")
    op.create_foreign_key(
        "chat_messages_session_id_fkey",
        "chat_messages",
        "chat_sessions",
        ["session_id"],
        ["session_id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("uq_chat_sessions_session_tenant", "chat_sessions", type_="unique")
    op.drop_constraint("fk_chat_messages_tenant_id_tenants", "chat_messages", type_="foreignkey")
    op.drop_column("chat_messages", "tenant_id")
