"""Create multicloud_cluster_nodes and multicloud_failover_events tables for Milestone 99.

Revision ID: l1m2n3o4p5q6
Revises: k1l2m3n4o5p6
Create Date: 2026-09-05 15:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "l1m2n3o4p5q6"
down_revision: str | None = "k1l2m3n4o5p6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. multicloud_cluster_nodes table
    op.create_table(
        "multicloud_cluster_nodes",
        sa.Column("node_id", sa.String(128), primary_key=True),
        sa.Column("cloud_provider", sa.String(64), nullable=False, server_default="oracle"),
        sa.Column("region", sa.String(64), nullable=False, index=True),
        sa.Column("endpoint_url", sa.String(512), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="standby_replica"),
        sa.Column("is_voting_member", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("priority_weight", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="12.0"),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("meta_data", JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_multicloud_nodes_region_role", "multicloud_cluster_nodes", ["region", "role"])

    # 2. multicloud_failover_events table
    op.create_table(
        "multicloud_failover_events",
        sa.Column("event_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("old_leader", sa.String(64), nullable=False),
        sa.Column("new_leader", sa.String(64), nullable=False),
        sa.Column("generation_term", sa.Integer(), nullable=False),
        sa.Column("trigger_type", sa.String(64), nullable=False, server_default="manual_operator_override"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("quorum_votes_acquired", sa.Integer(), nullable=False),
        sa.Column("total_voting_nodes", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("operator_id", sa.String(128), nullable=False, server_default="admin"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_multicloud_events_term", "multicloud_failover_events", ["generation_term", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_multicloud_events_term", table_name="multicloud_failover_events")
    op.drop_table("multicloud_failover_events")
    op.drop_index("ix_multicloud_nodes_region_role", table_name="multicloud_cluster_nodes")
    op.drop_table("multicloud_cluster_nodes")
