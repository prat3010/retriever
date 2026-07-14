"""Integration tests against real Postgres + Redis + RabbitMQ.

Run with::

    docker compose -f docker-compose.test.yml up -d
    INTEGRATION_TEST=1 uv run python -m pytest tests/test_integration.py -v
"""
import asyncio
import os

import pytest
from fastapi.testclient import TestClient

if not os.environ.get("INTEGRATION_TEST"):
    pytest.skip("Set INTEGRATION_TEST=1 to run", allow_module_level=True)

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/retriever_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/1")

from src.adapters.database.setup import initialize_database
from src.main import app

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    asyncio.run(initialize_database())


ADMIN_KEY = "dev-admin-master-key-change-in-production"
AUTH = {"X-Admin-Master-Key": ADMIN_KEY}


def test_readiness():
    response = client.get("/health/readiness")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_admin_tenant_lifecycle():
    from src.main import tenant_registry

    tenant = asyncio.run(tenant_registry.create_tenant(name="int-test", tier="standard"))
    assert tenant.status == "active"

    response = client.get(f"/v1/admin/tenants/{tenant.tenant_id}", headers=AUTH)
    assert response.status_code == 200
    assert response.json()["name"] == "int-test"

    response = client.delete(f"/v1/admin/tenants/{tenant.tenant_id}", headers=AUTH)
    assert response.status_code == 200
    assert response.json()["status"] == "deactivated"

    response = client.get("/v1/admin/tenants", headers=AUTH)
    assert response.json()["items"][0]["status"] == "inactive"
