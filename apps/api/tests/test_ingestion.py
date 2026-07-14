import os
import shutil
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from workers.src.tasks import process_document_async

from src.domain.abstractions.identity import UserContext
from src.domain.abstractions.ingestion import Document
from src.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_storage() -> None:
    storage_dir = "./storage"
    if os.path.exists(storage_dir):
        shutil.rmtree(storage_dir)
    yield
    if os.path.exists(storage_dir):
        shutil.rmtree(storage_dir)


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.main.document_repository.create_document", new_callable=AsyncMock)
@patch("src.main.document_repository.find_by_hash", new_callable=AsyncMock)
@patch("src.adapters.broker.celery_publisher.celery_app.send_task")
def test_document_upload_success(mock_send_task, mock_find_by_hash, mock_create, mock_validate) -> None:
    tenant_id = str(uuid.uuid4())
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id=tenant_id,
        roles=["integrator"],
        scopes=["document:write"],
    )
    mock_find_by_hash.return_value = None

    headers = {"Authorization": "Bearer ret_live_validtoken.secret"}
    file_content = b"Sample text contents to parse and chunk."
    response = client.post(
        f"/v1/tenants/{tenant_id}/documents",
        files={"file": ("sample.txt", file_content, "text/plain")},
        headers=headers,
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert "documentId" in body
    assert "fileHash" in body
    doc_id = body["documentId"]

    mock_create.assert_awaited_once()
    mock_send_task.assert_called_once()
    call_args = mock_send_task.call_args
    assert call_args[1]["args"][0] == doc_id


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.main.document_repository.find_by_hash", new_callable=AsyncMock)
def test_document_upload_deduplication(mock_find_by_hash, mock_validate) -> None:
    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id=tenant_id,
        roles=["integrator"],
        scopes=["document:write"],
    )
    mock_find_by_hash.return_value = Document(
        document_id=doc_id,
        tenant_id=tenant_id,
        filename="existing.txt",
        file_hash="mockedhash",
        storage_path="/path/to/existing",
        file_size=100,
        mime_type="text/plain",
        status="INDEXED",
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
    )

    headers = {"Authorization": "Bearer ret_live_validtoken.secret"}
    response = client.post(
        f"/v1/tenants/{tenant_id}/documents",
        files={"file": ("sample.txt", b"Existing text.", "text/plain")},
        headers=headers,
    )

    assert response.status_code == 202
    assert response.json()["documentId"] == doc_id
    assert response.json()["status"] == "pending"


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.main.document_repository.list_documents", new_callable=AsyncMock)
@patch("src.main.document_repository.get_document", new_callable=AsyncMock)
def test_document_list_and_get(mock_get, mock_list, mock_validate) -> None:
    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id=tenant_id,
        roles=["integrator"],
        scopes=["document:read"],
    )

    mock_doc = Document(
        document_id=doc_id,
        tenant_id=tenant_id,
        filename="doc1.txt",
        file_hash="hash1",
        storage_path="/path",
        file_size=200,
        mime_type="text/plain",
        status="INDEXED",
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
    )
    mock_list.return_value = [mock_doc]
    mock_get.return_value = mock_doc

    headers = {"Authorization": "Bearer ret_live_validtoken.secret"}

    response = client.get(f"/v1/tenants/{tenant_id}/documents", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["documentId"] == doc_id

    response = client.get(f"/v1/tenants/{tenant_id}/documents/{doc_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "INDEXED"


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.main.document_repository.soft_delete", new_callable=AsyncMock)
def test_document_delete(mock_soft_delete, mock_validate) -> None:
    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id=tenant_id,
        roles=["integrator"],
        scopes=["document:write"],
    )
    mock_soft_delete.return_value = "/path"

    headers = {"Authorization": "Bearer ret_live_validtoken.secret"}
    response = client.delete(f"/v1/tenants/{tenant_id}/documents/{doc_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
    mock_soft_delete.assert_awaited_once_with(tenant_id, doc_id)


@pytest.mark.asyncio
@patch("workers.src.tasks._publish_event")
@patch("workers.src.tasks.create_async_engine")
async def test_worker_processing_task(mock_create_engine, mock_publish_event) -> None:
    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    mock_create_engine.return_value = mock_engine

    # Configure engine.begin() context manager context explicitly
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_engine.begin.return_value = mock_ctx

    # Configuration fetch returns None (triggers 500 fallback sizes)
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_conn.execute.return_value = mock_result

    # Write a dummy parsing file
    test_file = "./sample_test.txt"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("Line 1 test content.\nLine 2 test content.")

    try:
        await process_document_async(doc_id, tenant_id, test_file)

        # Confirm database status updates were run
        assert mock_conn.execute.call_count >= 4
        
        # Verify that SET LOCAL app.bypass_rls was executed
        bypass_rls_called = False
        for call in mock_conn.execute.call_args_list:
            arg = call[0][0]
            if hasattr(arg, "text") and "SET LOCAL app.bypass_rls = 'true'" in arg.text:
                bypass_rls_called = True
                break
        assert bypass_rls_called, "SET LOCAL app.bypass_rls was not executed"
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)
