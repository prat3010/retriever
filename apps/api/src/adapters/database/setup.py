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
        tables_to_isolate = ["tenant_configs", "api_keys", "audit_logs"]
        for table in tables_to_isolate:
            await conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
            # Drop policy if exists to avoid conflicts
            await conn.execute(text(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table};"))
            # Create policy linking context current_tenant_id to tenant_id or bypass-rls key
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
        await conn.commit()
    print("Database initialization complete.", file=sys.stderr)


if __name__ == "__main__":
    import asyncio
    asyncio.run(initialize_database())
