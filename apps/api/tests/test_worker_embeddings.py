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
@patch("workers.src.tasks.embed_with_retry", new_callable=AsyncMock)
async def test_generate_embeddings_happy_path(
    mock_embed_with_retry, mock_create_engine, mock_publish_event
) -> None:
    from workers.src.tasks import _run_generate_embeddings

    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    chunk_id_1 = str(uuid.uuid4())
    chunk_id_2 = str(uuid.uuid4())

    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    mock_create_engine.return_value = mock_engine

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_engine.connect.return_value = mock_ctx
    mock_engine.begin.return_value = mock_ctx

    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_result.fetchall.return_value = [
        (chunk_id_1, "content 1"),
        (chunk_id_2, "content 2"),
    ]
    mock_conn.execute = AsyncMock(return_value=mock_result)

    mock_embed_with_retry.return_value = [[0.1, 0.2], [0.3, 0.4]]

    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        await _run_generate_embeddings(doc_id, tenant_id)

    bypass_rls_count = sum(
        1 for call in mock_conn.execute.call_args_list
        if hasattr(call[0][0], "text") and "SET LOCAL app.bypass_rls" in call[0][0].text
    )
    assert bypass_rls_count >= 2

    upsert_calls = [
        call for call in mock_conn.execute.call_args_list
        if hasattr(call[0][0], "text") and "INSERT INTO vector_records" in call[0][0].text
    ]
    assert len(upsert_calls) == 2

    status_update = any(
        hasattr(call[0][0], "text") and "UPDATE documents SET status = 'INDEXED'" in call[0][0].text
        for call in mock_conn.execute.call_args_list
    )
    assert status_update

    cache_delete = any(
        hasattr(call[0][0], "text") and "DELETE FROM semantic_cache" in call[0][0].text
        for call in mock_conn.execute.call_args_list
    )
    assert cache_delete

    mock_publish_event.assert_called_once()
    envelope = mock_publish_event.call_args[0][0]
    assert envelope["eventType"] == "DOCUMENT_INDEXED"
    assert envelope["payload"]["documentId"] == doc_id
    assert envelope["payload"]["chunksVectorized"] == 2


@pytest.mark.asyncio
@patch("workers.src.tasks.create_async_engine", autospec=True)
async def test_generate_embeddings_empty_chunks(mock_create_engine) -> None:
    from workers.src.tasks import _run_generate_embeddings

    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    mock_create_engine.return_value = mock_engine

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_engine.connect.return_value = mock_ctx

    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_result.fetchall.return_value = []
    mock_conn.execute = AsyncMock(return_value=mock_result)

    await _run_generate_embeddings(doc_id, tenant_id)

    no_upsert = not any(
        hasattr(call[0][0], "text") and "INSERT INTO vector_records" in call[0][0].text
        for call in mock_conn.execute.call_args_list
    )
    assert no_upsert


@pytest.mark.asyncio
@patch("workers.src.tasks.create_async_engine", autospec=True)
async def test_generate_embeddings_no_api_key(mock_create_engine) -> None:
    from workers.src.tasks import _run_generate_embeddings

    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    mock_create_engine.return_value = mock_engine

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_engine.connect.return_value = mock_ctx

    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_result.fetchall.return_value = [("chunk-1", "content")]
    mock_conn.execute = AsyncMock(return_value=mock_result)

    with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
        await _run_generate_embeddings(doc_id, tenant_id)

    no_upsert = not any(
        hasattr(call[0][0], "text") and "INSERT INTO vector_records" in call[0][0].text
        for call in mock_conn.execute.call_args_list
    )
    assert no_upsert


@pytest.mark.asyncio
@patch("workers.src.tasks._publish_event", autospec=True)
@patch("workers.src.tasks.create_async_engine", autospec=True)
async def test_generate_embeddings_config_overrides_model(
    mock_create_engine, mock_publish_event
) -> None:
    from workers.src.tasks import _run_generate_embeddings

    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    mock_create_engine.return_value = mock_engine

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_engine.connect.return_value = mock_ctx
    mock_engine.begin.return_value = mock_ctx

    config_dict = {
        "embedding_provider": {
            "model_name": "custom-embed-model",
            "api_key": "custom-key",
        }
    }
    mock_result = MagicMock()
    mock_result.fetchone.return_value = [json.dumps(config_dict)]
    mock_result.fetchall.return_value = [("chunk-1", "content")]
    mock_conn.execute = AsyncMock(return_value=mock_result)

    with patch("workers.src.tasks.embed_with_retry", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [[0.5]]
        await _run_generate_embeddings(doc_id, tenant_id)

    mock_embed.assert_called_once()
    model_arg = mock_embed.call_args[0][2]
    assert model_arg == "custom-embed-model"


@pytest.mark.asyncio
@patch("workers.src.tasks._publish_event", autospec=True)
@patch("workers.src.tasks.create_async_engine", autospec=True)
@patch("workers.src.tasks.embed_with_retry", new_callable=AsyncMock)
async def test_generate_embeddings_failure_sets_failed(
    mock_embed_with_retry, mock_create_engine, mock_publish_event
) -> None:
    from workers.src.tasks import _run_generate_embeddings

    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    mock_create_engine.return_value = mock_engine

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_engine.connect.return_value = mock_ctx
    mock_engine.begin.return_value = mock_ctx

    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_result.fetchall.return_value = [("chunk-1", "content")]
    mock_conn.execute = AsyncMock(return_value=mock_result)

    mock_embed_with_retry.side_effect = RuntimeError("OpenAI API error")

    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        with pytest.raises(RuntimeError):
            await _run_generate_embeddings(doc_id, tenant_id)

    failed_update = any(
        hasattr(call[0][0], "text") and "UPDATE documents SET status = 'FAILED'" in call[0][0].text
        for call in mock_conn.execute.call_args_list
    )
    assert failed_update

    failed_events = [
        call for call in mock_publish_event.call_args_list
        if call[0][0]["eventType"] == "DOCUMENT_FAILED"
    ]
    assert len(failed_events) == 1
    assert failed_events[0][0][0]["payload"]["failurePhase"] == "EMBEDDING"
