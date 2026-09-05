"""Create edge_nodes and edge_sync_checkpoints tables for Milestone 98.

Revision ID: k1l2m3n4o5p6
Revises: j1k2l3m4n5o6
Create Date: 2026-09-05 13:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "k1l2m3n4o5p6"
down_revision: str | None = "j1k2l3m4n5o6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. edge_nodes table
    op.create_table(
        "edge_nodes",
        sa.Column("node_id", sa.String(128), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("device_name", sa.String(255), nullable=False),
        sa.Column("platform", sa.String(64), nullable=False, server_default="darwin_arm64"),
        sa.Column("last_synced_seq", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("status", sa.String(32), nullable=False, server_default="online"),
        sa.Column("meta_data", JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_edge_nodes_tenant_status", "edge_nodes", ["tenant_id", "status"])

    # 2. edge_sync_checkpoints table
    op.create_table(
        "edge_sync_checkpoints",
        sa.Column("checkpoint_id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("node_id", sa.String(128), nullable=False, index=True),
        sa.Column("sequence_num", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_edge_sync_checkpoints_tenant_seq", "edge_sync_checkpoints", ["tenant_id", "sequence_num"])


def downgrade() -> None:
    op.drop_index("ix_edge_sync_checkpoints_tenant_seq", table_name="edge_sync_checkpoints")
    op.drop_table("edge_sync_checkpoints")
    op.drop_index("ix_edge_nodes_tenant_status", table_name="edge_nodes")
    op.drop_table("edge_nodes")
