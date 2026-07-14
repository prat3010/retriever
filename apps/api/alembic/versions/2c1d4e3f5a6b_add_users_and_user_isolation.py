"""Add users table and user-level isolation.

Revision ID: 2c1d4e3f5a6b
Revises: 8b1c5d2e9f40
Create Date: 2026-07-14 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2c1d4e3f5a6b"
down_revision: str | None = "8b1c5d2e9f40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("tenant_id", "external_id", name="uq_users_tenant_external"),
    )
    op.create_index(op.f("ix_users_tenant_id"), "users", ["tenant_id"])
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")
    op.execute("CREATE POLICY tenant_isolation_policy ON users FOR ALL USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid OR current_setting('app.bypass_rls', true) = 'true');")

    # Add role to api_keys
    op.add_column(
        "api_keys",
        sa.Column("role", sa.String(50), nullable=False, server_default="client"),
    )

    # Add encrypted LLM key to tenant_configs
    op.add_column(
        "tenant_configs",
        sa.Column("llm_api_key_encrypted", sa.Text(), nullable=True),
    )

    # Add user_id to chat_sessions
    op.add_column(
        "chat_sessions",
        sa.Column("user_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_chat_sessions_user_id",
        "chat_sessions", "users",
        ["user_id"], ["user_id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])

    # Add user_id to chat_messages
    op.add_column(
        "chat_messages",
        sa.Column("user_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_chat_messages_user_id",
        "chat_messages", "users",
        ["user_id"], ["user_id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])

    # Add user_id to inference_logs
    op.add_column(
        "inference_logs",
        sa.Column("user_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_inference_logs_user_id",
        "inference_logs", "users",
        ["user_id"], ["user_id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_inference_logs_user_id", "inference_logs", ["user_id"])


def downgrade() -> None:
    # Remove user_id from inference_logs
    op.drop_index("ix_inference_logs_user_id", table_name="inference_logs")
    op.drop_constraint("fk_inference_logs_user_id", "inference_logs", type_="foreignkey")
    op.drop_column("inference_logs", "user_id")

    # Remove user_id from chat_messages
    op.drop_index("ix_chat_messages_user_id", table_name="chat_messages")
    op.drop_constraint("fk_chat_messages_user_id", "chat_messages", type_="foreignkey")
    op.drop_column("chat_messages", "user_id")

    # Remove user_id from chat_sessions
    op.drop_index("ix_chat_sessions_user_id", table_name="chat_sessions")
    op.drop_constraint("fk_chat_sessions_user_id", "chat_sessions", type_="foreignkey")
    op.drop_column("chat_sessions", "user_id")

    # Remove llm_api_key_encrypted from tenant_configs
    op.drop_column("tenant_configs", "llm_api_key_encrypted")

    # Remove role from api_keys
    op.drop_column("api_keys", "role")

    # Drop users table
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON users;")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY;")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_constraint("uq_users_tenant_external", "users", type_="unique")
    op.drop_table("users")
