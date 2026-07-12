import os
import shutil
import uuid
import pytest
import json
import sqlalchemy as sa
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from src.main import app
from src.domain.abstractions.identity import UserContext
from src.adapters.database.models import DocumentDb
from workers.src.tasks import process_document_async, parse_document

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
@patch("src.main.celery_client.send_task")
@patch("src.main.tenant_session")
def test_document_upload_success(mock_session_ctx, mock_send_task, mock_validate) -> None:
    tenant_id = str(uuid.uuid4())
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id=tenant_id,
        roles=["integrator"],
        scopes=["document:write"],
    )

    # Setup session mocks explicitly
    mock_db_session = MagicMock()
    mock_db_session.execute = AsyncMock()
    mock_db_session.commit = AsyncMock()
    mock_db_session.add = MagicMock()
    mock_db_session.refresh = AsyncMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_db_session

    # Deduplication query returns None (no existing document)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    headers = {"Authorization": "Bearer ret_live_validtoken.secret"}
    file_content = b"Sample text contents to parse and chunk."

    response = client.post(
        f"/v1/tenants/{tenant_id}/documents",
        files={"file": ("sample.txt", file_content, "text/plain")},
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["filename"] == "sample.txt"
    assert response.json()["status"] == "uploaded"
    doc_id = response.json()["documentId"]

    # Verify db save called
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

    # Verify celery dispatch
    mock_send_task.assert_called_once_with(
        "tasks.parse_document",
        args=[doc_id, tenant_id, os.path.join("./storage", tenant_id, "sample.txt")],
    )


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.main.tenant_session")
def test_document_upload_deduplication(mock_session_ctx, mock_validate) -> None:
    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id=tenant_id,
        roles=["integrator"],
        scopes=["document:write"],
    )

    mock_db_session = MagicMock()
    mock_db_session.execute = AsyncMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_db_session

    import datetime
    # Mock return of an existing document matching file hash
    existing_doc = DocumentDb(
        document_id=uuid.UUID(doc_id),
        tenant_id=uuid.UUID(tenant_id),
        filename="existing.txt",
        file_hash="mockedhash",
        storage_path="/path/to/existing",
        file_size=100,
        mime_type="text/plain",
        status="processed",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_doc
    mock_db_session.execute.return_value = mock_result

    headers = {"Authorization": "Bearer ret_live_validtoken.secret"}
    response = client.post(
        f"/v1/tenants/{tenant_id}/documents",
        files={"file": ("sample.txt", b"Existing text.", "text/plain")},
        headers=headers,
    )

    # Status must be 201 and return the existing document metadata immediately
    assert response.status_code == 201
    assert response.json()["documentId"] == doc_id
    assert response.json()["filename"] == "existing.txt"
    assert response.json()["status"] == "processed"


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.main.tenant_session")
def test_document_list_and_get(mock_session_ctx, mock_validate) -> None:
    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id=tenant_id,
        roles=["integrator"],
        scopes=["document:read"],
    )

    mock_db_session = MagicMock()
    mock_db_session.execute = AsyncMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_db_session

    import datetime
    mock_doc = DocumentDb(
        document_id=uuid.UUID(doc_id),
        tenant_id=uuid.UUID(tenant_id),
        filename="doc1.txt",
        file_hash="hash1",
        storage_path="/path",
        file_size=200,
        mime_type="text/plain",
        status="processed",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )
    # Mock list query return values
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_doc]
    mock_result.scalar_one_or_none.return_value = mock_doc
    mock_db_session.execute.return_value = mock_result

    headers = {"Authorization": "Bearer ret_live_validtoken.secret"}
    
    # Test List
    response = client.get(f"/v1/tenants/{tenant_id}/documents", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["documentId"] == doc_id

    # Test GET status
    response = client.get(f"/v1/tenants/{tenant_id}/documents/{doc_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "processed"


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.main.tenant_session")
def test_document_delete(mock_session_ctx, mock_validate) -> None:
    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id=tenant_id,
        roles=["integrator"],
        scopes=["document:write"],
    )

    mock_db_session = MagicMock()
    mock_db_session.execute = AsyncMock()
    mock_db_session.commit = AsyncMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_db_session

    import datetime
    mock_doc = DocumentDb(
        document_id=uuid.UUID(doc_id),
        tenant_id=uuid.UUID(tenant_id),
        filename="doc.txt",
        file_hash="hash",
        storage_path="/path",
        file_size=10,
        mime_type="text/plain",
        status="processed",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_doc
    mock_db_session.execute.return_value = mock_result

    headers = {"Authorization": "Bearer ret_live_validtoken.secret"}
    response = client.delete(f"/v1/tenants/{tenant_id}/documents/{doc_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
    assert mock_doc.is_deleted is True
    mock_db_session.commit.assert_called()


@pytest.mark.asyncio
@patch("workers.src.tasks.create_async_engine")
async def test_worker_processing_task(mock_create_engine) -> None:
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
