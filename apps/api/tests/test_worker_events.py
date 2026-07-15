"""Tests for event publishing helpers in worker tasks."""

import json
from unittest.mock import MagicMock, patch

import pytest


# ── _build_envelope ────────────────────────────────────────────────────────


def test_build_envelope_shape() -> None:
    from workers.src.tasks import _build_envelope

    envelope = _build_envelope("DOCUMENT_PARSED", {"documentId": "doc_1", "tenantId": "t1"}, trace_id="trace-abc")

    assert envelope["eventId"].startswith("evt_")
    assert envelope["eventType"] == "DOCUMENT_PARSED"
    assert envelope["payload"]["documentId"] == "doc_1"
    assert envelope["traceId"] == "trace-abc"
    assert "T" in envelope["timestamp"]
    assert envelope["timestamp"].endswith("Z")


def test_build_envelope_default_trace_id() -> None:
    from workers.src.tasks import _build_envelope

    envelope = _build_envelope("DOCUMENT_FAILED", {"documentId": "doc_1", "tenantId": "t1"})

    assert envelope["traceId"] == ""


# ── _publish_event ─────────────────────────────────────────────────────────


@patch("workers.src.tasks.pika.BlockingConnection", autospec=True)
def test_publish_event_opens_connection(mock_connection) -> None:
    from workers.src.tasks import _publish_event, EXCHANGE_NAME, ROUTING_PARSED

    mock_channel = MagicMock()
    mock_connection.return_value.channel.return_value = mock_channel

    envelope = {
        "eventId": "evt_123",
        "eventType": "DOCUMENT_PARSED",
        "payload": {"documentId": "doc_1"},
    }
    _publish_event(envelope, ROUTING_PARSED)

    mock_connection.assert_called_once()
    mock_channel.basic_publish.assert_called_once()
    call_kwargs = mock_channel.basic_publish.call_args[1]
    assert call_kwargs["exchange"] == EXCHANGE_NAME
    assert call_kwargs["routing_key"] == ROUTING_PARSED
    assert call_kwargs["properties"].delivery_mode == 2
    published_body = json.loads(call_kwargs["body"])
    assert published_body["eventType"] == "DOCUMENT_PARSED"


@patch("workers.src.tasks.pika.BlockingConnection", autospec=True)
def test_publish_event_connection_closed_on_exit(mock_connection) -> None:
    from workers.src.tasks import _publish_event, ROUTING_PARSED

    mock_channel = MagicMock()
    mock_conn_instance = MagicMock()
    mock_connection.return_value = mock_conn_instance
    mock_conn_instance.channel.return_value = mock_channel

    _publish_event({"eventId": "evt_1"}, ROUTING_PARSED)

    mock_conn_instance.close.assert_called_once()
