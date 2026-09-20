"""Enforce strict FORCE ROW LEVEL SECURITY and add vector partition tables.

Revision ID: n1o2p3q4r5s6
Revises: m1n2o3p4q5r6
Create Date: 2026-09-19 08:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "n1o2p3q4r5s6"
down_revision: str | None = "m1n2o3p4q5r6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 0. Add collection_id to documents, document_chunks, and vector_records if missing
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS collection_id UUID;")
    op.execute("CREATE INDEX IF NOT EXISTS ix_documents_collection_id ON documents(collection_id);")
    op.execute("ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS collection_id UUID;")
    op.execute("CREATE INDEX IF NOT EXISTS ix_document_chunks_collection_id ON document_chunks(collection_id);")
    op.execute("ALTER TABLE vector_records ADD COLUMN IF NOT EXISTS collection_id UUID;")
    op.execute("CREATE INDEX IF NOT EXISTS ix_vector_records_collection_id ON vector_records(collection_id);")

    # 1. Create vector_records_1024, vector_records_1536, and vector_records_3072 if not exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS vector_records_1024 (
            chunk_id UUID PRIMARY KEY REFERENCES document_chunks(chunk_id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            collection_id UUID,
            embedding VECTOR(1024) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_vector_records_1024_tenant_id ON vector_records_1024(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_vector_records_1024_collection_id ON vector_records_1024(collection_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_vector_records_1024_embedding ON vector_records_1024 USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS vector_records_1536 (
            chunk_id UUID PRIMARY KEY REFERENCES document_chunks(chunk_id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            collection_id UUID,
            embedding VECTOR(1536) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_vector_records_1536_tenant_id ON vector_records_1536(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_vector_records_1536_collection_id ON vector_records_1536(collection_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_vector_records_1536_embedding ON vector_records_1536 USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS vector_records_3072 (
            chunk_id UUID PRIMARY KEY REFERENCES document_chunks(chunk_id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            collection_id UUID,
            embedding VECTOR(3072) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_vector_records_3072_tenant_id ON vector_records_3072(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_vector_records_3072_collection_id ON vector_records_3072(collection_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_vector_records_3072_embedding ON vector_records_3072 USING hnsw ((embedding::halfvec(3072)) halfvec_cosine_ops) WITH (m = 16, ef_construction = 64)")

    # 2. Enforce and Force Row Level Security across all tenant tables
    op.execute("""
        DO $$
        DECLARE
            tbl text;
            tables text[] := ARRAY[
                'tenant_configs', 'api_keys', 'audit_logs',
                'documents', 'document_chunks', 'vector_records',
                'vector_records_1024', 'vector_records_1536', 'vector_records_3072',
                'prompt_templates', 'chat_sessions', 'chat_messages',
                'inference_logs', 'users', 'semantic_cache',
                'chat_message_feedback',
                'eval_datasets', 'eval_runs',
                'graph_triples', 'online_evaluations', 'payment_transactions',
                'telemetry_anomalies', 'agent_checkpoints',
                'compiled_prompt_programs', 'workflow_executions',
                'workflow_step_checkpoints',
                'tenant_lora_adapters', 'custom_plugins',
                'edge_nodes', 'edge_sync_checkpoints',
                'voice_sessions', 'voice_turns',
                'configurations'
            ];
        BEGIN
            FOREACH tbl IN ARRAY tables LOOP
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = tbl) THEN
                    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', tbl);
                    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY;', tbl);
                    EXECUTE format('DROP POLICY IF EXISTS tenant_isolation_policy ON %I;', tbl);
                    IF tbl = 'configurations' THEN
                        EXECUTE format('
                            CREATE POLICY tenant_isolation_policy ON %I
                            FOR ALL USING (
                                tenant_id IS NULL
                                OR tenant_id = NULLIF(current_setting(''app.current_tenant_id'', true), '''')::uuid
                                OR current_setting(''app.bypass_rls'', true) = ''true''
                            );
                        ', tbl);
                    ELSE
                        EXECUTE format('
                            CREATE POLICY tenant_isolation_policy ON %I
                            FOR ALL USING (
                                tenant_id = NULLIF(current_setting(''app.current_tenant_id'', true), '''')::uuid
                                OR current_setting(''app.bypass_rls'', true) = ''true''
                            );
                        ', tbl);
                    END IF;
                END IF;
            END LOOP;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS vector_records_3072 CASCADE;
        DROP TABLE IF EXISTS vector_records_1536 CASCADE;
    """)
