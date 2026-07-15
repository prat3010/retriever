"""Create chat_message_feedback table.

Revision ID: 6f1d7e5a6b2c
Revises: 3e9a1b2c4d5f
Create Date: 2026-07-15 00:00:00.000000
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op


revision: str = "6f1d7e5a6b2c"
down_revision: str | None = "3e9a1b2c4d5f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create chat_message_feedback table
    op.create_table(
        "chat_message_feedback",
        sa.Column("feedback_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("feedback_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["chat_messages.message_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("feedback_id"),
    )
    
    # Create indices
    op.create_index("ix_chat_message_feedback_tenant_id", "chat_message_feedback", ["tenant_id"])
    op.create_index("ix_chat_message_feedback_message_id", "chat_message_feedback", ["message_id"])
    op.create_index("ix_chat_message_feedback_user_id", "chat_message_feedback", ["user_id"])

    # Enable Row-Level Security (RLS)
    op.execute("ALTER TABLE chat_message_feedback ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON chat_message_feedback
        FOR ALL
        USING (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            OR current_setting('app.bypass_rls', true) = 'true'
        );
    """)


def downgrade() -> None:
    # Drop RLS Policy
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON chat_message_feedback;")
    op.execute("ALTER TABLE chat_message_feedback DISABLE ROW LEVEL SECURITY;")
    
    # Drop indices
    op.drop_index("ix_chat_message_feedback_user_id", "chat_message_feedback")
    op.drop_index("ix_chat_message_feedback_message_id", "chat_message_feedback")
    op.drop_index("ix_chat_message_feedback_tenant_id", "chat_message_feedback")
    
    # Drop table
    op.drop_table("chat_message_feedback")
