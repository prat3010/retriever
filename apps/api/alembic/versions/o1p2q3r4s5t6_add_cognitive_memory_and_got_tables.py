"""Add cognitive memory and Graph-of-Thoughts persistence tables.

Revision ID: o1p2q3r4s5t6
Revises: n1o2p3q4r5s6
Create Date: 2026-09-21 06:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "o1p2q3r4s5t6"
down_revision: str | None = "n1o2p3q4r5s6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create cognitive_memories table
    op.execute("""
        CREATE TABLE IF NOT EXISTS cognitive_memories (
            id VARCHAR(64) PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            memory_type VARCHAR(50) NOT NULL DEFAULT 'episodic',
            query TEXT NOT NULL,
            distilled_insight TEXT NOT NULL DEFAULT '',
            tool_chain JSONB NOT NULL DEFAULT '[]'::jsonb,
            success BOOLEAN NOT NULL DEFAULT true,
            turns_count INTEGER NOT NULL DEFAULT 1,
            importance_score FLOAT NOT NULL DEFAULT 0.5,
            stability_score FLOAT NOT NULL DEFAULT 1.0,
            last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            access_count INTEGER NOT NULL DEFAULT 0,
            embedding VECTOR(768),
            meta_data JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cognitive_memories_tenant_type ON cognitive_memories(tenant_id, memory_type);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cognitive_memories_tenant_id ON cognitive_memories(tenant_id);")
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_cognitive_memories_embedding 
        ON cognitive_memories USING hnsw (embedding vector_cosine_ops) 
        WITH (m = 16, ef_construction = 64);
    """)

    # 2. Create got_graphs table
    op.execute("""
        CREATE TABLE IF NOT EXISTS got_graphs (
            graph_id VARCHAR(64) PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            query TEXT NOT NULL,
            root_id VARCHAR(64) NOT NULL,
            is_converged BOOLEAN NOT NULL DEFAULT false,
            best_score FLOAT NOT NULL DEFAULT 0.0,
            optimal_path JSONB NOT NULL DEFAULT '[]'::jsonb,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            total_latency_ms FLOAT NOT NULL DEFAULT 0.0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_got_graphs_tenant_converged ON got_graphs(tenant_id, is_converged);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_got_graphs_tenant_id ON got_graphs(tenant_id);")

    # 3. Create got_thoughts table
    op.execute("""
        CREATE TABLE IF NOT EXISTS got_thoughts (
            thought_id VARCHAR(64) PRIMARY KEY,
            graph_id VARCHAR(64) NOT NULL REFERENCES got_graphs(graph_id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            prompt TEXT NOT NULL,
            content TEXT NOT NULL,
            thought_type VARCHAR(50) NOT NULL DEFAULT 'generation',
            status VARCHAR(50) NOT NULL DEFAULT 'scored',
            parent_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
            child_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
            score FLOAT NOT NULL DEFAULT 0.0,
            grounding_score FLOAT NOT NULL DEFAULT 0.0,
            coherence_score FLOAT NOT NULL DEFAULT 0.0,
            constraint_score FLOAT NOT NULL DEFAULT 0.0,
            token_cost INTEGER NOT NULL DEFAULT 0,
            latency_ms FLOAT NOT NULL DEFAULT 0.0,
            iteration_depth INTEGER NOT NULL DEFAULT 0,
            is_optimal_path BOOLEAN NOT NULL DEFAULT false,
            meta_data JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_got_thoughts_graph_depth ON got_thoughts(graph_id, iteration_depth);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_got_thoughts_tenant_id ON got_thoughts(tenant_id);")

    # 4. Enforce Row Level Security (RLS) on new tables
    op.execute("""
        DO $$
        DECLARE
            tbl text;
            tables text[] := ARRAY['cognitive_memories', 'got_graphs', 'got_thoughts'];
        BEGIN
            FOREACH tbl IN ARRAY tables LOOP
                EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', tbl);
                EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY;', tbl);
                EXECUTE format('DROP POLICY IF EXISTS tenant_isolation_policy ON %I;', tbl);
                EXECUTE format('
                    CREATE POLICY tenant_isolation_policy ON %I
                    FOR ALL USING (
                        tenant_id = NULLIF(current_setting(''app.current_tenant_id'', true), '''')::uuid
                        OR current_setting(''app.bypass_rls'', true) = ''true''
                    );
                ', tbl);
            END LOOP;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS got_thoughts CASCADE;")
    op.execute("DROP TABLE IF EXISTS got_graphs CASCADE;")
    op.execute("DROP TABLE IF EXISTS cognitive_memories CASCADE;")
