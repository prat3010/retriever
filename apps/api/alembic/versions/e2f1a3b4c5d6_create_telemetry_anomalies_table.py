"""Create telemetry_anomalies table for Milestone 83.

Revision ID: e2f1a3b4c5d6
Revises: 9b0c1d2e3f4a
Create Date: 2026-09-03 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "e2f1a3b4c5d6"
down_revision: str | None = "9b0c1d2e3f4a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "telemetry_anomalies",
        sa.Column("anomaly_id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_id", sa.String(255), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False, server_default="api_key"),
        sa.Column(
            "key_id",
            UUID(as_uuid=True),
            sa.ForeignKey("api_keys.key_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("risk_level", sa.String(50), nullable=False, server_default="LOW"),
        sa.Column("anomaly_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("algorithm_used", sa.String(100), nullable=False, server_default="isolation_forest"),
        sa.Column("features", JSONB, nullable=False, server_default="{}"),
        sa.Column("contributing_factors", JSONB, nullable=False, server_default="[]"),
        sa.Column("is_quarantined", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    op.create_index(
        "ix_telemetry_anomalies_tenant_created",
        "telemetry_anomalies",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_telemetry_anomalies_risk_status",
        "telemetry_anomalies",
        ["risk_level", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_telemetry_anomalies_risk_status", table_name="telemetry_anomalies")
    op.drop_index("ix_telemetry_anomalies_tenant_created", table_name="telemetry_anomalies")
    op.drop_table("telemetry_anomalies")
