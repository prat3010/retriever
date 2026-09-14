"""Unit and Integration tests for Community Connectors Ecosystem (Milestone 111)."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.domain.abstractions.config import TenantConfiguration
from src.domain.abstractions.connector import (
    BaseConnector,
    ConnectorConfig,
    ConnectorManifest,
    ConnectorSyncState,
    DiscoveredDocument,
)
from src.domain.connectors.cloud_storage import S3StorageConnector
from src.domain.connectors.database_cdc import DatabaseCdcConnector
from src.domain.connectors.github import GitHubConnector
from src.domain.connectors.registry import ConnectorRegistry, register_connector
from src.domain.connectors.slack import SlackConnector
from src.main import app

client = TestClient(app)


# ── 1. Connector Manifests & Registry Tests ───────────────────────────────────


def test_connector_manifests_catalog() -> None:
    """Verify ConnectorRegistry lists complete manifests for all enterprise connectors."""
    manifests = ConnectorRegistry.list_manifests()
    types = {m.connector_type for m in manifests}

    expected_types = {
        "database_cdc",
        "s3",
        "github",
        "slack",
        "web_crawler",
        "google_drive",
        "notion",
        "local_folder",
    }
    for et in expected_types:
        assert et in types, f"Missing expected connector manifest: {et}"

    for m in manifests:
        assert m.name
        assert m.description
        assert m.icon
        assert isinstance(m.supports_incremental, bool)
        assert isinstance(m.required_parameters, list)


@patch("src.config.settings.ADMIN_MASTER_KEY", "test-admin-secret-key")
def test_admin_connector_manifests_endpoint() -> None:
    """Verify GET /v1/admin/connectors/manifests returns HTTP 200 with catalog."""
    headers = {"X-Admin-Master-Key": "test-admin-secret-key"}
    res = client.get("/v1/admin/connectors/manifests", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "manifests" in data
    assert data["total"] >= 8
    manifest_types = [m["connector_type"] for m in data["manifests"]]
    assert "database_cdc" in manifest_types
    assert "s3" in manifest_types
    assert "github" in manifest_types
    assert "slack" in manifest_types


# ── 2. Database Change-Data-Capture (CDC) Connector Tests ─────────────────────


@pytest.mark.asyncio
async def test_database_cdc_connector_lifecycle() -> None:
    """Verify DatabaseCdcConnector formats rows and tracks high-watermarks."""
    connector = DatabaseCdcConnector()
    manifest = connector.get_manifest()
    assert manifest.connector_type == "database_cdc"
    assert manifest.supports_incremental is True

    # Test Credential Validation
    valid_cfg = ConnectorConfig(
        id="conn_cdc_1",
        name="Postgres CDC",
        connector_type="postgres_cdc",
        configuration={
            "offline_sandbox": True,
            "host": "localhost",
            "database": "production_db",
            "user": "postgres",
            "tables": ["knowledge_base"],
        },
    )
    assert await connector.validate_credentials(valid_cfg) is True

    # Mock database records
    records = [
        {
            "id": "kb-101",
            "title": "Architecture Blueprint",
            "content": "Hexagonal domain boundaries and pgvector storage.",
            "author": "Prateek",
            "updated_at": "2026-09-14T01:00:00Z",
        },
        {
            "id": "kb-102",
            "title": "Incident Runbook",
            "content": "Procedures for Redis Sentinel and database failover.",
            "author": "Ops Team",
            "updated_at": "2026-09-14T02:00:00Z",
        },
    ]

    valid_cfg.configuration["mock_records"] = {"knowledge_base": records}

    # Initial Sync (watermark is 0)
    docs, state1 = await connector.fetch_incremental(valid_cfg, ConnectorSyncState())
    assert len(docs) == 2
    assert state1.watermark == "2026-09-14T02:00:00Z"
    assert docs[0].filename == "cdc_knowledge_base_kb-101.md"
    assert "# Table: knowledge_base" in docs[0].content
    assert "**Record ID**: `kb-101`" in docs[0].content
    assert "| **author** | Prateek |" in docs[0].content

    # Incremental Sync with new record
    new_record = {
        "id": "kb-103",
        "title": "Security Whitepaper",
        "content": "Zero-trust micro-enclaves and AES-256-GCM.",
        "author": "Security Team",
        "updated_at": "2026-09-14T03:00:00Z",
    }
    valid_cfg.configuration["mock_records"]["knowledge_base"].append(new_record)

    docs2, state2 = await connector.fetch_incremental(valid_cfg, state1)
    assert len(docs2) == 1
    assert docs2[0].filename == "cdc_knowledge_base_kb-103.md"
    assert state2.watermark == "2026-09-14T03:00:00Z"


# ── 3. Cloud Object Storage (S3 / R2) Connector Tests ─────────────────────────


@pytest.mark.asyncio
async def test_s3_storage_connector_lifecycle() -> None:
    """Verify S3StorageConnector fetches objects and skips unmodified ETags."""
    connector = S3StorageConnector()
    manifest = connector.get_manifest()
    assert manifest.connector_type == "s3"
    assert manifest.supports_incremental is True

    cfg = ConnectorConfig(
        id="conn_s3_1",
        name="Engineering Docs Bucket",
        connector_type="s3",
        configuration={
            "offline_sandbox": True,
            "bucket_name": "retriever-docs-vault",
            "mock_objects": [
                {
                    "key": "specs/architecture.md",
                    "content": "# Platform Architecture Specification",
                    "etag": "etag-v1",
                    "mime_type": "text/markdown",
                },
                {
                    "key": "contracts/agreement.pdf",
                    "content": "[PDF Binary Data]",
                    "etag": "etag-pdf-1",
                    "mime_type": "application/pdf",
                },
            ],
        },
    )

    assert await connector.validate_credentials(cfg) is True

    # 1. First fetch discovers both objects
    docs, state1 = await connector.fetch_incremental(cfg, ConnectorSyncState())
    assert len(docs) == 2
    assert docs[0].filename == "architecture.md"
    assert docs[1].filename == "agreement.pdf"
    assert state1.metadata["seen_etags"]["specs/architecture.md"] == "etag-v1"

    # 2. Second fetch with identical ETags discovers 0 new objects
    docs2, state2 = await connector.fetch_incremental(cfg, state1)
    assert len(docs2) == 0

    # 3. Object modified with new ETag is re-discovered
    cfg.configuration["mock_objects"][0]["etag"] = "etag-v2"
    cfg.configuration["mock_objects"][0]["content"] = "# Updated Platform Spec"
    docs3, state3 = await connector.fetch_incremental(cfg, state2)
    assert len(docs3) == 1
    assert docs3[0].content == "# Updated Platform Spec"
    assert state3.metadata["seen_etags"]["specs/architecture.md"] == "etag-v2"


# ── 4. GitHub Connector Tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_github_connector_lifecycle() -> None:
    """Verify GitHubConnector extracts issues/PRs and formats markdown."""
    connector = GitHubConnector()
    manifest = connector.get_manifest()
    assert manifest.connector_type == "github"
    assert manifest.supports_incremental is True

    cfg = ConnectorConfig(
        id="conn_gh_1",
        name="GitHub Repo Docs",
        connector_type="github",
        configuration={
            "offline_sandbox": True,
            "repo": "prat3010/retriever",
            "mock_data": {
                "issues": [
                    {
                        "number": 42,
                        "title": "Support CDC Logical Replication",
                        "body": "Add PostgreSQL wal2json CDC streaming connector.",
                        "state": "closed",
                        "user": {"login": "prateeksharma"},
                        "labels": [{"name": "enhancement"}, {"name": "connectors"}],
                        "updated_at": "2026-09-14T04:00:00Z",
                    }
                ]
            },
        },
    )

    assert await connector.validate_credentials(cfg) is True

    docs, state = await connector.fetch_incremental(cfg, ConnectorSyncState())
    assert len(docs) == 1
    doc = docs[0]
    assert doc.filename == "github_prat3010_retriever_issue_42.md"
    assert "# GitHub Issue #42: Support CDC Logical Replication" in doc.content
    assert "@prateeksharma" in doc.content
    assert "enhancement, connectors" in doc.content
    assert state.watermark == "2026-09-14T04:00:00Z"


# ── 5. Slack Connector Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_slack_connector_lifecycle() -> None:
    """Verify SlackConnector aggregates conversation threads into markdown."""
    connector = SlackConnector()
    manifest = connector.get_manifest()
    assert manifest.connector_type == "slack"
    assert manifest.supports_incremental is True

    cfg = ConnectorConfig(
        id="conn_slack_1",
        name="Engineering Slack Channel",
        connector_type="slack",
        configuration={
            "offline_sandbox": True,
            "channels": ["C_ENG_DEV"],
            "mock_messages": {
                "C_ENG_DEV": [
                    {
                        "ts": "1726280000.000100",
                        "user": "U_PRATEEK",
                        "text": "Milestone 111 connectors architecture is now live.",
                        "replies": [
                            {
                                "user": "U_ALICE",
                                "text": "CDC replication is working with 0 latency.",
                                "ts": "1726280010.000200",
                            }
                        ],
                    }
                ]
            },
        },
    )

    assert await connector.validate_credentials(cfg) is True

    docs, state = await connector.fetch_incremental(cfg, ConnectorSyncState())
    assert len(docs) == 1
    doc = docs[0]
    assert "slack_C_ENG_DEV_1726280000_000100.md" in doc.filename
    assert "Milestone 111 connectors architecture" in doc.content
    assert "## Thread Replies" in doc.content
    assert "CDC replication is working" in doc.content
    assert state.watermark == "1726280000.000100"


# ── 6. Custom Connector Ingestion SDK Tests ───────────────────────────────────


def test_custom_connector_registration_decorator() -> None:
    """Verify @register_connector allows third-party dynamic connector registration."""

    @register_connector("community_salesforce")
    class CommunitySalesforceConnector(BaseConnector):
        def get_manifest(self) -> ConnectorManifest:
            return ConnectorManifest(
                connector_type="community_salesforce",
                name="Community Salesforce CRM",
                description="Community-authored Salesforce CRM objects connector.",
                icon="cloud",
                supports_incremental=True,
            )

        async def validate_credentials(self, config: ConnectorConfig) -> bool:
            return True

        async def fetch_documents(self, config: ConnectorConfig) -> list[DiscoveredDocument]:
            return [
                DiscoveredDocument(
                    filename="lead_1.md",
                    content="# Lead: Enterprise Corp",
                    mime_type="text/markdown",
                )
            ]

    # Verify registration in ConnectorRegistry
    resolved = ConnectorRegistry.get_connector("community_salesforce")
    assert isinstance(resolved, CommunitySalesforceConnector)
    assert resolved.get_manifest().name == "Community Salesforce CRM"

    manifest_types = [m.connector_type for m in ConnectorRegistry.list_manifests()]
    assert "community_salesforce" in manifest_types


# ── 7. Admin Incremental Sync Integration Test ────────────────────────────────


@patch("src.config.settings.ADMIN_MASTER_KEY", "test-admin-secret-key")
@patch("src.routers.admin.ingest_file_sync")
@patch("src.routers.admin.audit_logger")
@patch("src.routers.admin.config_service")
def test_admin_trigger_incremental_sync(
    mock_config_service, mock_audit, mock_ingest_sync
) -> None:
    """Verify admin sync endpoint executes incrementally and persists _sync_state."""
    headers = {"X-Admin-Master-Key": "test-admin-secret-key"}
    tenant_id = "tenant_cdc_sync"

    conn = ConnectorConfig(
        id="conn_cdc_test",
        name="Production Database CDC",
        connector_type="database_cdc",
        configuration={
            "offline_sandbox": True,
            "host": "localhost",
            "database": "db",
            "user": "postgres",
            "tables": ["customers"],
            "mock_records": {
                "customers": [
                    {
                        "id": "c-1",
                        "name": "Acme Inc",
                        "updated_at": "2026-09-14T05:00:00Z",
                    }
                ]
            },
        },
    )

    fake_config = TenantConfiguration(tenant_id=tenant_id, connectors=[conn])
    mock_config_service.get_tenant_config = AsyncMock(return_value=fake_config)
    mock_config_service.update_tenant_config = AsyncMock(return_value=None)
    mock_audit.write = AsyncMock(return_value=None)
    mock_ingest_sync.return_value = AsyncMock()

    res = client.post(
        f"/v1/admin/tenants/{tenant_id}/connectors/{conn.id}/sync",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["documentsDiscovered"] == 1
    assert data["documentsIngested"] == 1

    # Verify that _sync_state was written to connector configuration
    assert "_sync_state" in conn.configuration
    assert conn.configuration["_sync_state"]["watermark"] == "2026-09-14T05:00:00Z"
