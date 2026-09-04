"""Create workflow_executions and workflow_step_checkpoints tables for Milestone 95.

Revision ID: h1i2j3k4l5m6
Revises: g1h2i3j4k5l6
Create Date: 2026-09-05 01:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "h1i2j3k4l5m6"
down_revision: str | None = "g1h2i3j4k5l6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. workflow_executions table
    op.create_table(
        "workflow_executions",
        sa.Column("execution_id", sa.String(128), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("workflow_name", sa.String(128), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued", index=True),
        sa.Column("trigger_event", sa.String(128), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=True, index=True),
        sa.Column("input_payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("output_payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("total_steps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_steps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_step_name", sa.String(128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("webhook_url", sa.String(512), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_workflow_executions_tenant_status",
        "workflow_executions",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_workflow_executions_tenant_name",
        "workflow_executions",
        ["tenant_id", "workflow_name"],
    )
    op.create_index(
        "ix_workflow_executions_tenant_idemp",
        "workflow_executions",
        ["tenant_id", "idempotency_key"],
    )

    # 2. workflow_step_checkpoints table
    op.create_table(
        "workflow_step_checkpoints",
        sa.Column("step_id", sa.String(256), primary_key=True),
        sa.Column(
            "execution_id",
            sa.String(128),
            sa.ForeignKey("workflow_executions.execution_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("step_name", sa.String(128), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("memoized_output", JSONB, nullable=False, server_default="{}"),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("execution_time_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_workflow_steps_exec_step",
        "workflow_step_checkpoints",
        ["execution_id", "step_name"],
    )
    op.create_index(
        "ix_workflow_steps_tenant_status",
        "workflow_step_checkpoints",
        ["tenant_id", "status"],
    )

    # 3. Enable RLS and Tenant Isolation Policies
    op.execute("ALTER TABLE workflow_executions ENABLE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON workflow_executions;")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON workflow_executions
        FOR ALL USING (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            OR current_setting('app.bypass_rls', true) = 'true'
        );
    """)

    op.execute("ALTER TABLE workflow_step_checkpoints ENABLE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON workflow_step_checkpoints;")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON workflow_step_checkpoints
        FOR ALL USING (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            OR current_setting('app.bypass_rls', true) = 'true'
        );
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON workflow_step_checkpoints;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON workflow_executions;")
    op.drop_index("ix_workflow_steps_tenant_status", table_name="workflow_step_checkpoints")
    op.drop_index("ix_workflow_steps_exec_step", table_name="workflow_step_checkpoints")
    op.drop_table("workflow_step_checkpoints")
    op.drop_index("ix_workflow_executions_tenant_idemp", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_tenant_name", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_tenant_status", table_name="workflow_executions")
    op.drop_table("workflow_executions")
