"""Create missing tables, fix model-migration drift, add RLS.

Creates 5 tables that exist in models.py but were never added to any
migration (chat_sessions, chat_messages, inference_logs, vector_records,
prompt_templates). Fixes audit_logs column name mismatch (event_type →
action). Adds name column to chat_messages. Enables RLS on tables that
were missing it. Fixes column width mismatches.

Revision ID: 3e9a1b2c4d5f
Revises: 2c1d4e3f5a6b
Create Date: 2026-07-14 13:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "3e9a1b2c4d5f"
down_revision: str | None = "2c1d4e3f5a6b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Create 5 missing tables (IF NOT EXISTS for idempotency) ──────

    op.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_chat_sessions_tenant_id ON chat_sessions (tenant_id)")
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_chat_sessions_session_tenant
        ON chat_sessions (session_id, tenant_id)
    """)
    # user_id index created by M3 migration if table existed, else we create it
    op.execute("CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_id ON chat_sessions (user_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            message_id UUID PRIMARY KEY,
            session_id UUID NOT NULL,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
            role VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            name VARCHAR(255),
            tool_calls JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_chat_messages_tenant_id ON chat_messages (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_chat_messages_session_id ON chat_messages (session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_chat_messages_user_id ON chat_messages (user_id)")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_chat_messages_session_tenant'
            ) THEN
                ALTER TABLE chat_messages
                ADD CONSTRAINT fk_chat_messages_session_tenant
                FOREIGN KEY (session_id, tenant_id)
                REFERENCES chat_sessions(session_id, tenant_id)
                ON DELETE CASCADE;
            END IF;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS inference_logs (
            log_id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            session_id UUID REFERENCES chat_sessions(session_id) ON DELETE SET NULL,
            user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
            model_used VARCHAR(255) NOT NULL,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            latency_ms INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_inference_logs_tenant_id ON inference_logs (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_inference_logs_session_id ON inference_logs (session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_inference_logs_user_id ON inference_logs (user_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS vector_records (
            chunk_id UUID PRIMARY KEY REFERENCES document_chunks(chunk_id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            embedding vector(1536) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_vector_records_tenant_id ON vector_records (tenant_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS prompt_templates (
            prompt_id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            is_system_prompt BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_prompt_templates_tenant_id ON prompt_templates (tenant_id)")

    # ── 2. Fix audit_logs column mismatch ──────────────────────────
    # Model has `action`, migration created `event_type`. Rename and drop `actor`.
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'event_type'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'action'
            ) THEN
                ALTER TABLE audit_logs RENAME COLUMN event_type TO action;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'actor'
            ) THEN
                ALTER TABLE audit_logs DROP COLUMN actor;
            END IF;
        END $$;
    """)

    # ── 3. Add name column to chat_messages (if not already present) ──
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'chat_messages' AND column_name = 'name'
            ) THEN
                ALTER TABLE chat_messages ADD COLUMN name VARCHAR(255);
            END IF;
        END $$;
    """)

    # ── 4. Add RLS policies for tables missing them ────────────────
    rls_tables = [
        "chat_sessions", "chat_messages", "inference_logs",
        "vector_records", "prompt_templates",
    ]
    for table in rls_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies
                    WHERE tablename = '{table}' AND policyname = 'tenant_isolation_policy'
                ) THEN
                    CREATE POLICY tenant_isolation_policy ON {table}
                    FOR ALL
                    USING (
                        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                        OR current_setting('app.bypass_rls', true) = 'true'
                    );
                END IF;
            END $$;
        """)

    # ── 5. Fix column width mismatches (model widened these, migration had narrower) ──
    op.alter_column("tenants", "name", type_=sa.String(255))
    op.alter_column("tenant_configs", "active_model", type_=sa.String(255))
    op.alter_column("api_keys", "name", type_=sa.String(255))
    op.alter_column("api_keys", "prefix", type_=sa.String(50))
    op.alter_column("api_keys", "key_hash", type_=sa.String(255))


def downgrade() -> None:
    # Reverse column width changes
    op.execute("ALTER TABLE api_keys ALTER COLUMN key_hash TYPE VARCHAR(64)")
    op.execute("ALTER TABLE api_keys ALTER COLUMN prefix TYPE VARCHAR(16)")
    op.execute("ALTER TABLE api_keys ALTER COLUMN name TYPE VARCHAR(100)")
    op.execute("ALTER TABLE tenant_configs ALTER COLUMN active_model TYPE VARCHAR(100)")
    op.execute("ALTER TABLE tenants ALTER COLUMN name TYPE VARCHAR(100)")

    # Drop RLS policies
    for table in ["prompt_templates", "vector_records", "inference_logs", "chat_messages", "chat_sessions"]:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Remove name column from chat_messages
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'chat_messages' AND column_name = 'name'
            ) THEN
                ALTER TABLE chat_messages DROP COLUMN name;
            END IF;
        END $$;
    """)

    # Restore audit_logs columns
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'action'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'event_type'
            ) THEN
                ALTER TABLE audit_logs RENAME COLUMN action TO event_type;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_logs' AND column_name = 'actor'
            ) THEN
                ALTER TABLE audit_logs ADD COLUMN actor VARCHAR(100) NOT NULL DEFAULT '';
            END IF;
        END $$;
    """)

    # Drop the 5 tables (IF EXISTS since they may not have existed before for some DBs)
    for table in ["prompt_templates", "vector_records", "inference_logs", "chat_messages", "chat_sessions"]:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
