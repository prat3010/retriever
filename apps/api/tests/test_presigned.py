"""Presigned URL and Document Distribution Unit Tests.

Verifies:
- GET /v1/tenants/{tenantId}/documents/{documentId}/download-url fetches temporary URL.
- HMAC verification route handles link expiration, signature mismatch, and valid file serving.
"""

import os
import time
import uuid
import hmac
from hashlib import sha256
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.main import app, local_storage, document_repository
from src.adapters.api.security import verify_tenant_isolation, verify_scopes, get_current_user_id
from src.adapters.storage.local_storage import LocalStorage
from src.domain.abstractions.ingestion import Document


@pytest.fixture
def mock_user_context():
    return {
        "user_id": "11111111-1111-1111-1111-111111111111",
        "tenant_id": "22222222-2222-2222-2222-222222222222",
    }


@pytest.fixture(autouse=True)
def setup_dependency_overrides(mock_user_context):
    app.dependency_overrides[verify_tenant_isolation] = lambda: None
    app.dependency_overrides[verify_scopes] = lambda: None
    app.dependency_overrides[get_current_user_id] = lambda: mock_user_context["user_id"]
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_document_download_url_success(mock_user_context) -> None:
    """Verify standard client can request a presigned download URL."""
    tenant_id = mock_user_context["tenant_id"]
    document_id = str(uuid.uuid4())

    mock_doc = Document(
        document_id=document_id,
        tenant_id=tenant_id,
        filename="report.pdf",
        file_hash="hash-123",
        storage_path=f"./storage/{tenant_id}/report.pdf",
        file_size=1024,
        mime_type="application/pdf",
        status="completed",
        created_at="now",
        updated_at="now",
    )

    with patch.object(document_repository, "get_document", new_callable=AsyncMock) as mock_get_doc:
        mock_get_doc.return_value = mock_doc

        with patch.object(local_storage, "generate_presigned_url", new_callable=AsyncMock) as mock_presign:
            mock_presign.return_value = "/v1/local-downloads/fake-signed-path"

            client = TestClient(app)
            response = client.get(f"/v1/tenants/{tenant_id}/documents/{document_id}/download-url?expiry=600")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["documentId"] == document_id
            assert data["downloadUrl"] == "/v1/local-downloads/fake-signed-path"
            assert data["expiresInSeconds"] == 600
            
            mock_get_doc.assert_called_once_with(tenant_id, document_id)
            mock_presign.assert_called_once_with(mock_doc.storage_path, expiry_seconds=600)


@pytest.mark.asyncio
async def test_serve_local_download_expired() -> None:
    """Verify expired links are rejected with a 410 Gone error."""
    tenant_id = str(uuid.uuid4())
    filename = "report.pdf"
    expired_time = int(time.time()) - 10

    client = TestClient(app)
    response = client.get(
        f"/v1/local-downloads/{tenant_id}/{filename}?expires={expired_time}&signature=fake-sig"
    )

    assert response.status_code == status.HTTP_410_GONE
    assert "expired" in response.json()["detail"]


@pytest.mark.asyncio
async def test_serve_local_download_invalid_sig() -> None:
    """Verify invalid HMAC signatures are rejected with a 403 Forbidden error."""
    tenant_id = str(uuid.uuid4())
    filename = "report.pdf"
    future_time = int(time.time()) + 100

    client = TestClient(app)
    response = client.get(
        f"/v1/local-downloads/{tenant_id}/{filename}?expires={future_time}&signature=invalid-signature"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Invalid signature" in response.json()["detail"]


@pytest.mark.asyncio
async def test_serve_local_download_success(tmp_path) -> None:
    """Verify valid signature serves file from local filesystem."""
    tenant_id = str(uuid.uuid4())
    filename = "test.txt"
    future_time = int(time.time()) + 100

    # Create dummy file inside temporary directory
    tenant_dir = tmp_path / tenant_id
    tenant_dir.mkdir()
    dummy_file = tenant_dir / filename
    dummy_file.write_bytes(b"hello temporary document context")

    # Generate valid signature
    relative_path = f"{tenant_id}/{filename}"
    secret_key = b"local-storage-presign-key"
    msg = f"{relative_path}:{future_time}".encode()
    valid_sig = hmac.new(secret_key, msg=msg, digestmod=sha256).hexdigest()

    # Mock LocalStorage storage_dir to look at tmp_path
    mock_local_storage = MagicMock(spec=LocalStorage)
    mock_local_storage.storage_dir = str(tmp_path)

    with patch("src.main.local_storage", mock_local_storage):
        client = TestClient(app)
        response = client.get(
            f"/v1/local-downloads/{tenant_id}/{filename}?expires={future_time}&signature={valid_sig}"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.content == b"hello temporary document context"
