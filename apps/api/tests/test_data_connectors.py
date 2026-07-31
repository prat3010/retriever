"""Unit tests for Milestone 36: SaaS Data Connectors Framework."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.domain.abstractions.connector import ConnectorConfig
from src.domain.connectors.cloud_drive import MockCloudDriveConnector
from src.domain.connectors.registry import ConnectorRegistry
from src.domain.connectors.web_crawler import WebCrawlerConnector
from src.main import app

client = TestClient(app)


# ── 1. Connector Registry & Validation Tests ─────────────────────────────────


def test_connector_registry_resolution() -> None:
    """Verify ConnectorRegistry resolves connector instances by strategy name."""
    assert isinstance(ConnectorRegistry.get_connector("web_crawler"), WebCrawlerConnector)
    assert isinstance(ConnectorRegistry.get_connector("cloud_drive"), MockCloudDriveConnector)
    assert isinstance(ConnectorRegistry.get_connector("google_drive"), MockCloudDriveConnector)
    assert isinstance(ConnectorRegistry.get_connector("unknown"), WebCrawlerConnector)


@pytest.mark.asyncio
async def test_mock_cloud_drive_connector_fetch() -> None:
    """Verify MockCloudDriveConnector fetches discovered documents."""
    connector = MockCloudDriveConnector()
    config = ConnectorConfig(
        id="conn_1",
        name="Team Drive",
        connector_type="google_drive",
        configuration={"folder_id": "folder_abc123"},
    )

    valid = await connector.validate_credentials(config)
    assert valid is True

    docs = await connector.fetch_documents(config)
    assert len(docs) == 2
    assert "folder_abc123" in docs[0].content
    assert docs[0].metadata["source"] == "google_drive"


# ── 2. Admin Connector Management APIs ────────────────────────────────────────


@patch("src.config.settings.ADMIN_MASTER_KEY", "test-admin-secret-key")
@patch("src.routers.admin.ingest_file_sync")
@patch("src.routers.admin.audit_logger")
@patch("src.routers.admin.config_service")
def test_admin_connector_lifecycle_crud(
    mock_config_service, mock_audit, mock_ingest_sync
) -> None:
    """Verify Admin Connector CRUD and sync execution endpoints."""
    headers = {"X-Admin-Master-Key": "test-admin-secret-key"}
    tenant_id = "tenant_connectors"

    from src.domain.abstractions.config import TenantConfiguration

    fake_config = TenantConfiguration(tenant_id=tenant_id)
    mock_config_service.get_tenant_config = AsyncMock(return_value=fake_config)
    mock_config_service.update_tenant_config = AsyncMock(return_value=None)
    mock_audit.write = AsyncMock(return_value=None)
    mock_ingest_sync.return_value = AsyncMock()

    # Create Connector
    create_payload = {
        "name": "Engineering Notion Connector",
        "connector_type": "notion",
        "sync_interval_minutes": 720,
        "configuration": {"folder_id": "notion_eng_docs"},
    }

    create_res = client.post(
        f"/v1/admin/tenants/{tenant_id}/connectors",
        headers=headers,
        json=create_payload,
    )
    assert create_res.status_code == 201
    conn_data = create_res.json()
    conn_id = conn_data["id"]
    assert conn_data["name"] == "Engineering Notion Connector"
    assert conn_data["connector_type"] == "notion"

    # List Connectors
    list_res = client.get(f"/v1/admin/tenants/{tenant_id}/connectors", headers=headers)
    assert list_res.status_code == 200
    assert any(c["id"] == conn_id for c in list_res.json())

    # Get Single Connector
    get_res = client.get(f"/v1/admin/tenants/{tenant_id}/connectors/{conn_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == conn_id

    # Trigger Sync
    sync_res = client.post(
        f"/v1/admin/tenants/{tenant_id}/connectors/{conn_id}/sync",
        headers=headers,
    )
    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    assert sync_data["status"] == "completed"
    assert sync_data["documentsDiscovered"] == 2
    assert sync_data["documentsIngested"] == 2

    # Delete Connector
    del_res = client.delete(f"/v1/admin/tenants/{tenant_id}/connectors/{conn_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"
