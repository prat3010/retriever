"""Add evaluation tables (datasets, questions, runs, results).

Revision ID: 9a0b1c2d3e4f
Revises: 8b1c5d2e9f40
Create Date: 2026-07-15 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9a0b1c2d3e4f"
down_revision: str | None = "8b1c5d2e9f40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "eval_datasets",
        sa.Column("dataset_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("dataset_id"),
    )
    op.create_index("ix_eval_datasets_tenant_id", "eval_datasets", ["tenant_id"])

    op.create_table(
        "eval_questions",
        sa.Column("question_id", sa.UUID(), nullable=False),
        sa.Column("dataset_id", sa.UUID(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("ground_truth_answer", sa.Text(), nullable=False),
        sa.Column("relevant_chunk_ids", sa.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dataset_id"], ["eval_datasets.dataset_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("question_id"),
    )
    op.create_index("ix_eval_questions_dataset_id", "eval_questions", ["dataset_id"])

    op.create_table(
        "eval_runs",
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("dataset_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("trigger", sa.String(20), nullable=False, server_default=sa.text("'manual'")),
        sa.Column("aggregate_scores", sa.JSONB(), nullable=True),
        sa.Column("question_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("completed_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dataset_id"], ["eval_datasets.dataset_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index("ix_eval_runs_tenant_id", "eval_runs", ["tenant_id"])

    op.create_table(
        "eval_run_results",
        sa.Column("result_id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("question_id", sa.UUID(), nullable=False),
        sa.Column("generated_answer", sa.Text(), nullable=True),
        sa.Column("retrieved_chunk_ids", sa.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("scores", sa.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["run_id"], ["eval_runs.run_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["eval_questions.question_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("result_id"),
    )
    op.create_index("ix_eval_run_results_run_id", "eval_run_results", ["run_id"])


def downgrade() -> None:
    op.drop_table("eval_run_results")
    op.drop_table("eval_runs")
    op.drop_table("eval_questions")
    op.drop_table("eval_datasets")
