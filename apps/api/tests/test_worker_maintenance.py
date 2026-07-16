import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

# ── reconcile_stalled ──────────────────────────────────────────────────────


@patch("workers.src.tasks.get_engine")
@patch("workers.src.tasks.process_document.delay", autospec=True)
@patch("workers.src.tasks.generate_embeddings.delay", autospec=True)
def test_reconcile_stalled_dispatches_pending(
    mock_emb_delay, mock_doc_delay, mock_get_engine
) -> None:
    from workers.src.tasks import reconcile_stalled

    doc_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())

    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_get_engine.return_value = mock_engine

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_engine.begin.return_value = mock_ctx

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        (doc_id, tenant_id, "/path/to/file", "PENDING")
    ]
    mock_conn.execute.return_value = mock_result

    reconcile_stalled()

    mock_doc_delay.assert_called_once_with(doc_id, tenant_id, "/path/to/file")
    mock_emb_delay.assert_not_called()


@patch("workers.src.tasks.get_engine")
@patch("workers.src.tasks.process_document.delay", autospec=True)
@patch("workers.src.tasks.generate_embeddings.delay", autospec=True)
def test_reconcile_stalled_dispatches_indexing(
    mock_emb_delay, mock_doc_delay, mock_get_engine
) -> None:
    from workers.src.tasks import reconcile_stalled

    doc_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())

    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_get_engine.return_value = mock_engine

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_engine.begin.return_value = mock_ctx

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        (doc_id, tenant_id, "/path", "INDEXING")
    ]
    mock_conn.execute.return_value = mock_result

    reconcile_stalled()

    mock_emb_delay.assert_called_once_with(doc_id, tenant_id)
    mock_doc_delay.assert_not_called()


@patch("workers.src.tasks.get_engine")
@patch("workers.src.tasks.process_document.delay", autospec=True)
@patch("workers.src.tasks.generate_embeddings.delay", autospec=True)
def test_reconcile_stalled_no_stalled(
    mock_emb_delay, mock_doc_delay, mock_get_engine
) -> None:
    from workers.src.tasks import reconcile_stalled

    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_get_engine.return_value = mock_engine

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_engine.begin.return_value = mock_ctx

    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_conn.execute.return_value = mock_result

    reconcile_stalled()

    mock_doc_delay.assert_not_called()
    mock_emb_delay.assert_not_called()


# ── cleanup_expired_data edge cases ────────────────────────────────────────


@patch("workers.src.tasks.get_engine")
def test_cleanup_expired_data_no_ttl_skips(mock_get_engine) -> None:
    from workers.src.tasks import cleanup_expired_data

    tenant_id = str(uuid.uuid4())
    config_dict = {
        "security_settings": {
            "data_retention_ttl_days": None
        }
    }

    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_get_engine.return_value = mock_engine

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_engine.begin.return_value = mock_ctx

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(tenant_id, json.dumps(config_dict))]
    mock_conn.execute.return_value = mock_result

    cleanup_expired_data()

    delete_calls = [
        call for call in mock_conn.execute.call_args_list
        if hasattr(call[0][0], "text") and "DELETE FROM" in call[0][0].text
    ]
    assert len(delete_calls) == 0


@patch("workers.src.tasks.get_engine")
def test_cleanup_expired_data_missing_security_settings(mock_get_engine) -> None:
    from workers.src.tasks import cleanup_expired_data

    tenant_id = str(uuid.uuid4())
    config_dict = {}

    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_get_engine.return_value = mock_engine

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_engine.begin.return_value = mock_ctx

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(tenant_id, json.dumps(config_dict))]
    mock_conn.execute.return_value = mock_result

    cleanup_expired_data()

    delete_calls = [
        call for call in mock_conn.execute.call_args_list
        if hasattr(call[0][0], "text") and "DELETE FROM" in call[0][0].text
    ]
    assert len(delete_calls) == 0


@patch("workers.src.tasks.get_engine")
def test_cleanup_expired_data_malformed_config(mock_get_engine) -> None:
    from workers.src.tasks import cleanup_expired_data

    tenant_id = str(uuid.uuid4())

    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_get_engine.return_value = mock_engine

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_engine.begin.return_value = mock_ctx

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(tenant_id, "not valid json{{{")]
    mock_conn.execute.return_value = mock_result

    cleanup_expired_data()

    delete_calls = [
        call for call in mock_conn.execute.call_args_list
        if hasattr(call[0][0], "text") and "DELETE FROM" in call[0][0].text
    ]
    assert len(delete_calls) == 0


@patch("workers.src.tasks.get_engine")
def test_cleanup_expired_data_continues_on_error(mock_get_engine) -> None:
    from workers.src.tasks import cleanup_expired_data

    good_tenant = str(uuid.uuid4())
    bad_tenant = str(uuid.uuid4())
    good_config = {
        "security_settings": {
            "data_retention_ttl_days": 10
        }
    }

    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_get_engine.return_value = mock_engine

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_engine.begin.return_value = mock_ctx

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        (bad_tenant, "invalid{json"),
        (good_tenant, json.dumps(good_config)),
    ]
    mock_conn.execute.return_value = mock_result

    cleanup_expired_data()

    delete_calls = [
        call for call in mock_conn.execute.call_args_list
        if hasattr(call[0][0], "text") and "DELETE FROM" in call[0][0].text
    ]
    assert len(delete_calls) == 2
