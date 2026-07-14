import sys

from sqlalchemy import text

from src.adapters.database.connection import engine
from src.adapters.database.models import Base


async def initialize_database() -> None:
    """Create all relational tables and apply Row-Level Security (RLS) policies."""
    print("Initializing database tables...", file=sys.stderr)
    async with engine.begin() as conn:
        # Create all tables defined in models
        await conn.run_sync(Base.metadata.create_all)

    async with engine.connect() as conn:
        print("Enabling Row-Level Security policies...", file=sys.stderr)
        # Enable RLS on customer data tables and register security policies
        tables_to_isolate = [
            "tenant_configs", "api_keys", "audit_logs",
            "documents", "document_chunks", "vector_records",
            "prompt_templates", "chat_sessions", "chat_messages",
            "inference_logs", "users",
        ]
        for table in tables_to_isolate:
            await conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
            await conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table};"))
            await conn.execute(
                text(
                    f"""
                    CREATE POLICY tenant_isolation_policy ON {table}
                    FOR ALL
                    USING (
                        tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                        OR current_setting('app.bypass_rls', true) = 'true'
                    );
                    """
                )
            )

        # Apply custom RLS on configurations table supporting global config (tenant_id IS NULL)
        await conn.execute(text("ALTER TABLE configurations ENABLE ROW LEVEL SECURITY;"))
        await conn.execute(text("DROP POLICY IF EXISTS tenant_isolation_policy ON configurations;"))
        await conn.execute(
            text(
                """
                CREATE POLICY tenant_isolation_policy ON configurations
                FOR ALL
                USING (
                    tenant_id IS NULL
                    OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                    OR current_setting('app.bypass_rls', true) = 'true'
                );
                """
            )
        )

        # Create HNSW cosine similarity index on vector_records
        print("Creating HNSW vector index...", file=sys.stderr)
        await conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_vector_records_embedding
                ON vector_records USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 200);
                """
            )
        )

        # Create GIN tsvector index on document_chunks for BM25 keyword search
        print("Creating GIN tsvector index...", file=sys.stderr)
        await conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_document_chunks_content_tsvector
                ON document_chunks USING gin (to_tsvector('english', content));
                """
            )
        )

        # Create index on chat_sessions created_at for ordering
        print("Creating chat_sessions created_at index...", file=sys.stderr)
        await conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_sessions_created_at
                ON chat_sessions (created_at DESC);
                """
            )
        )

        # Create compound index on prompt_templates for tenant lookups
        print("Creating prompt_templates compound index...", file=sys.stderr)
        await conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_prompt_templates_tenant_name
                ON prompt_templates (tenant_id, name);
                """
            )
        )

        # Create index on inference_logs for time-range queries
        print("Creating inference_logs created_at index...", file=sys.stderr)
        await conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_inference_logs_created_at
                ON inference_logs (created_at DESC);
                """
            )
        )

        await conn.commit()
    print("Database initialization complete.", file=sys.stderr)


if __name__ == "__main__":
    import asyncio
    asyncio.run(initialize_database())
