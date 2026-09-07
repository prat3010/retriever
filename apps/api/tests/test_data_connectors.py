"""Unit tests for SaaS Data Connectors Framework."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.domain.abstractions.connector import ConnectorConfig
from src.domain.connectors.google_drive import GoogleDriveConnector
from src.domain.connectors.local_folder import LocalFolderConnector
from src.domain.connectors.registry import ConnectorRegistry
from src.domain.connectors.web_crawler import WebCrawlerConnector
from src.main import app

client = TestClient(app)


# ── 1. Connector Registry & Validation Tests ─────────────────────────────────


def test_connector_registry_resolution() -> None:
    """Verify ConnectorRegistry resolves connector instances by strategy name."""
    assert isinstance(ConnectorRegistry.get_connector("web_crawler"), WebCrawlerConnector)
    assert isinstance(ConnectorRegistry.get_connector("cloud_drive"), LocalFolderConnector)
    assert isinstance(ConnectorRegistry.get_connector("local_folder"), LocalFolderConnector)
    assert isinstance(ConnectorRegistry.get_connector("google_drive"), GoogleDriveConnector)

    with pytest.raises(NotImplementedError):
        ConnectorRegistry.get_connector("unknown_connector_type")


@pytest.mark.asyncio
async def test_local_folder_connector_fetch() -> None:
    """Verify LocalFolderConnector fetches genuine discovered documents from disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc1 = Path(tmpdir) / "doc1.txt"
        doc1.write_text("Quarterly engineering overview and technical roadmap.", encoding="utf-8")
        doc2 = Path(tmpdir) / "doc2.md"
        doc2.write_text("SaaS Architecture and multi-cloud security specs.", encoding="utf-8")

        connector = LocalFolderConnector()
        config = ConnectorConfig(
            id="conn_1",
            name="Local Docs",
            connector_type="local_folder",
            configuration={"folder_path": tmpdir},
        )

        valid = await connector.validate_credentials(config)
        assert valid is True

        docs = await connector.fetch_documents(config)
        assert len(docs) == 2
        filenames = [d.filename for d in docs]
        assert "doc1.txt" in filenames
        assert "doc2.md" in filenames

        matched_doc = next(d for d in docs if d.filename == "doc1.txt")
        assert "Quarterly engineering overview" in matched_doc.content
        assert matched_doc.metadata["source"] == "local_folder"


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

    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "sample_a.txt").write_text("Sample file A content", encoding="utf-8")
        (Path(tmpdir) / "sample_b.txt").write_text("Sample file B content", encoding="utf-8")

        # Create Connector
        create_payload = {
            "name": "Engineering Folder Connector",
            "connector_type": "local_folder",
            "sync_interval_minutes": 720,
            "configuration": {"folder_path": tmpdir},
        }

        create_res = client.post(
            f"/v1/admin/tenants/{tenant_id}/connectors",
            headers=headers,
            json=create_payload,
        )
        assert create_res.status_code == 201
        conn_data = create_res.json()
        conn_id = conn_data["id"]
        assert conn_data["name"] == "Engineering Folder Connector"
        assert conn_data["connector_type"] == "local_folder"

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
