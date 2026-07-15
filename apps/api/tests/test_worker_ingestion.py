import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def reset_engine():
    import workers.src.tasks
    workers.src.tasks._engine = None


@pytest.mark.asyncio
@patch("workers.src.tasks._publish_event", autospec=True)
@patch("workers.src.tasks.create_async_engine", autospec=True)
@patch("boto3.client")
@patch("workers.src.tasks.extract_text_from_file", return_value="")
async def test_worker_processing_task_s3_path(
    mock_extract, mock_boto3_client, mock_create_engine, mock_publish_event
) -> None:
    from workers.src.tasks import process_document_async

    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    mock_create_engine.return_value = mock_engine

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_engine.begin.return_value = mock_ctx

    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_conn.execute = AsyncMock(return_value=mock_result)

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    with patch("tempfile.NamedTemporaryFile") as mock_tmp:
        mock_tmp.return_value.__enter__.return_value.name = "/tmp/test_download.txt"
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = ""
            await process_document_async(doc_id, tenant_id, "s3://bucket/key/file.txt")

    mock_s3.download_file.assert_called_once_with("bucket", "key/file.txt", "/tmp/test_download.txt")

    s3_client_kwargs = mock_boto3_client.call_args[1]
    assert s3_client_kwargs.get("endpoint_url") is None


@pytest.mark.asyncio
@patch("workers.src.tasks._publish_event", autospec=True)
@patch("workers.src.tasks.create_async_engine", autospec=True)
@patch("boto3.client")
@patch("workers.src.tasks.extract_text_from_file", return_value="")
async def test_worker_processing_task_s3_path_cleanup(
    mock_extract, mock_boto3_client, mock_create_engine, mock_publish_event
) -> None:
    from workers.src.tasks import process_document_async

    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    mock_create_engine.return_value = mock_engine

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_engine.begin.return_value = mock_ctx

    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_conn.execute = AsyncMock(return_value=mock_result)

    mock_s3 = MagicMock()
    mock_boto3_client.return_value = mock_s3

    with patch("tempfile.NamedTemporaryFile") as mock_tmp:
        mock_tmp.return_value.__enter__.return_value.name = "/tmp/cleanup_test.txt"

        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("os.remove") as mock_remove:
                await process_document_async(doc_id, tenant_id, "s3://bucket/k/f.txt")

                mock_remove.assert_called_once_with("/tmp/cleanup_test.txt")


@pytest.mark.asyncio
@patch("workers.src.tasks._publish_event", autospec=True)
@patch("workers.src.tasks.create_async_engine", autospec=True)
async def test_worker_processing_task_empty_text_triggers_ocr(
    mock_create_engine, mock_publish_event
) -> None:
    from workers.src.tasks import process_document_async

    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    mock_create_engine.return_value = mock_engine

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_engine.begin.return_value = mock_ctx

    config_result = MagicMock()
    config_result.fetchone.return_value = [json.dumps({})]
    mock_conn.execute.return_value = config_result

    test_file = "./test_empty_ocr.txt"
    try:
        with open(test_file, "w") as f:
            f.write("")

        with patch("workers.src.tasks._ocr_with_tesseract", return_value="") as mock_ocr:
            with patch("workers.src.tasks._describe_with_vision", return_value="") as mock_vision:
                await process_document_async(doc_id, tenant_id, test_file, "text/plain")

                mock_ocr.assert_called_once()
                mock_vision.assert_called_once()
    finally:
        import os
        if os.path.exists(test_file):
            os.remove(test_file)


@pytest.mark.asyncio
@patch("workers.src.tasks._publish_event", autospec=True)
@patch("workers.src.tasks.create_async_engine", autospec=True)
@patch("workers.src.tasks.extract_text_from_file", return_value="Some text content")
async def test_worker_processing_task_extract_tables(
    mock_extract_text, mock_create_engine, mock_publish_event
) -> None:
    from workers.src.tasks import process_document_async

    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    mock_create_engine.return_value = mock_engine

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_engine.begin.return_value = mock_ctx

    mock_result = MagicMock()
    mock_result.fetchone.return_value = [json.dumps({})]
    mock_result.fetchall.return_value = []
    mock_conn.execute = AsyncMock(return_value=mock_result)

    with patch("processing_core.pdf_parser.extract_tables_from_pdf") as mock_tables:
        mock_tables.return_value = [{"headers": ["Col1"], "rows": [["val1"]]}]
        await process_document_async(doc_id, tenant_id, "/fake/path/test.pdf", "application/pdf")

        mock_tables.assert_called_once()

    insert_calls = [
        call for call in mock_conn.execute.call_args_list
        if hasattr(call[0][0], "text") and "INSERT INTO document_chunks" in call[0][0].text
    ]
    assert len(insert_calls) >= 1
