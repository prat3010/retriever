"""Integration tests against real Postgres + Redis + RabbitMQ.

Tests the repository layer directly (not through HTTP) to avoid
event-loop conflicts between anyio (Starlette) and pytest-asyncio.

Run with::

    docker compose -f docker-compose.test.yml up -d
    INTEGRATION_TEST=1 uv run python -m pytest tests/test_integration.py -v
"""
import os
from uuid import uuid4

import pytest

if not os.environ.get("INTEGRATION_TEST"):
    pytest.skip("Set INTEGRATION_TEST=1 to run", allow_module_level=True)

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/retriever_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/1")

from sqlalchemy import text

from src.adapters.database.connection import engine
from src.adapters.database.document_repository import SqlDocumentRepository
from src.adapters.database.setup import initialize_database
from src.adapters.database.tenant_repository import SqlTenantRegistry
from src.domain.abstractions.ingestion import Document


@pytest.fixture(scope="module", autouse=True)
async def setup_database():
    async with engine.connect() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        row = await conn.execute(text("SELECT COUNT(*) FROM pg_tables WHERE schemaname='public'"))
        if row.scalar() == 0:
            await initialize_database()


@pytest.mark.asyncio(loop_scope="module")
async def test_db_connection():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1 AS val"))
        assert result.scalar() == 1


@pytest.mark.asyncio(loop_scope="module")
async def test_redis_connection():
    from src.main import redis_client

    result = await redis_client.ping()
    assert result is True


@pytest.mark.asyncio(loop_scope="module")
async def test_tenant_crud():
    registry = SqlTenantRegistry()
    tenant = await registry.create_tenant(name="int-test", tier="standard", isolation_level="strict")
    assert tenant.status == "active"
    assert tenant.name == "int-test"

    got = await registry.get_tenant(tenant.tenant_id)
    assert got is not None
    assert got.name == "int-test"

    deactivated = await registry.deactivate_tenant(tenant.tenant_id)
    assert deactivated is True

    _entries, total = await registry.list_tenants()
    assert total >= 1


@pytest.mark.asyncio(loop_scope="module")
async def test_document_crud():
    registry = SqlTenantRegistry()
    tenant = await registry.create_tenant(name="doc-test", tier="standard", isolation_level="strict")
    tenant_id = str(tenant.tenant_id)

    doc = Document(
        document_id=str(uuid4()),
        tenant_id=tenant_id,
        filename="test.txt",
        file_hash="abc123",
        storage_path="/tmp/test.txt",
        file_size=10,
        mime_type="text/plain",
        status="PENDING",
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
    )

    repo = SqlDocumentRepository()
    await repo.create_document(tenant_id, doc)

    docs = await repo.list_documents(tenant_id)
    assert len(docs) == 1
    assert docs[0].filename == "test.txt"

    result = await repo.soft_delete(tenant_id, doc.document_id)
    assert result is not None
