"""Create voice_sessions and voice_turns tables for Milestone 100.

Revision ID: m1n2o3p4q5r6
Revises: l1m2n3o4p5q6
Create Date: 2026-09-05 15:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "m1n2o3p4q5r6"
down_revision: str | None = "l1m2n3o4p5q6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. voice_sessions table
    op.create_table(
        "voice_sessions",
        sa.Column("session_id", sa.String(128), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("user_id", sa.String(128), nullable=False, server_default="usr_anonymous"),
        sa.Column("state", sa.String(32), nullable=False, server_default="initializing"),
        sa.Column("sample_rate_hz", sa.Integer(), nullable=False, server_default="16000"),
        sa.Column("channels", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("vad_sensitivity", sa.Float(), nullable=False, server_default="0.65"),
        sa.Column("selected_voice", sa.String(64), nullable=False, server_default="neural_natural"),
        sa.Column("audio_codec", sa.String(32), nullable=False, server_default="pcm16"),
        sa.Column("total_turns", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_ping_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("meta_data", JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_voice_sessions_tenant_state", "voice_sessions", ["tenant_id", "state"])

    # 2. voice_turns table
    op.create_table(
        "voice_turns",
        sa.Column("turn_id", sa.String(128), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(128),
            sa.ForeignKey("voice_sessions.session_id", ondelete="CASCADE"),
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
        sa.Column("user_transcript", sa.Text(), nullable=False),
        sa.Column("agent_response_text", sa.Text(), nullable=False),
        sa.Column("time_to_transcribe_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("time_to_first_audio_byte_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_turn_duration_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_voice_turns_session_created", "voice_turns", ["session_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_voice_turns_session_created", table_name="voice_turns")
    op.drop_table("voice_turns")
    op.drop_index("ix_voice_sessions_tenant_state", table_name="voice_sessions")
    op.drop_table("voice_sessions")
