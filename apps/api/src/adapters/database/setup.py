import sys

from sqlalchemy import text

from src.adapters.database.connection import engine
from src.adapters.database.models import Base


async def _create_extensions_and_tables() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(Base.metadata.create_all)


async def _enable_rls_on_tables(conn) -> None:
    tables = [
        "tenant_configs", "api_keys", "audit_logs",
        "documents", "document_chunks", "vector_records",
        "prompt_templates", "chat_sessions", "chat_messages",
        "inference_logs", "users", "semantic_cache",
        "chat_message_feedback",
    ]
    for table in tables:
        await conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
        await conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table};"))
        await conn.execute(text(f"""
            CREATE POLICY tenant_isolation_policy ON {table}
            FOR ALL USING (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
                OR current_setting('app.bypass_rls', true) = 'true'
            );
        """))


async def _enable_rls_for_configurations(conn) -> None:
    await conn.execute(text("ALTER TABLE configurations ENABLE ROW LEVEL SECURITY;"))
    await conn.execute(text("DROP POLICY IF EXISTS tenant_isolation_policy ON configurations;"))
    await conn.execute(text("""
        CREATE POLICY tenant_isolation_policy ON configurations
        FOR ALL USING (
            tenant_id IS NULL
            OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            OR current_setting('app.bypass_rls', true) = 'true'
        );
    """))


async def _create_hnsw_indices(conn) -> None:
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_vector_records_embedding
        ON vector_records USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 200);
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_semantic_cache_embedding
        ON semantic_cache USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 200);
    """))


async def _create_gin_indices(conn) -> None:
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_document_chunks_content_tsvector
        ON document_chunks USING gin (to_tsvector('english', content));
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_document_chunks_meta_data
        ON document_chunks USING gin (meta_data);
    """))


async def _create_btree_indices(conn) -> None:
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_chat_sessions_created_at
        ON chat_sessions (created_at DESC);
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_prompt_templates_tenant_name
        ON prompt_templates (tenant_id, name);
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_inference_logs_created_at
        ON inference_logs (created_at DESC);
    """))
    await conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_document_chunks_tenant_doc_idx
        ON document_chunks (tenant_id, document_id, chunk_index);
    """))


async def initialize_database() -> None:
    print("Initializing database tables...", file=sys.stderr)
    await _create_extensions_and_tables()

    async with engine.connect() as conn:
        print("Enabling Row-Level Security policies...", file=sys.stderr)
        await _enable_rls_on_tables(conn)
        await _enable_rls_for_configurations(conn)

        print("Creating HNSW vector indices...", file=sys.stderr)
        await _create_hnsw_indices(conn)

        print("Creating GIN indices...", file=sys.stderr)
        await _create_gin_indices(conn)

        print("Creating B-tree indices...", file=sys.stderr)
        await _create_btree_indices(conn)

        await conn.commit()
    print("Database initialization complete.", file=sys.stderr)


if __name__ == "__main__":
    import asyncio
    asyncio.run(initialize_database())
