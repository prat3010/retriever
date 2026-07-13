"""Event Architecture Tests.

Verifies:
- EventEnvelope serialization and defaults
- DocumentEventPayload construction
- RabbitMQEventPublisher topology declaration
- RabbitMQEventPublisher publish
- Integration: upload endpoint publishes event
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.domain.abstractions.events import DocumentEventPayload, EventEnvelope

# ── 1. Event Envelope ────────────────────────────────────────────────────────


def test_event_envelope_generates_event_id() -> None:
    """Verify eventId is generated automatically."""
    envelope = EventEnvelope(
        eventType="DOCUMENT_UPLOADED",
        payload=DocumentEventPayload(documentId="doc_001", tenantId="t1"),
    )
    assert envelope.eventId.startswith("evt_")
    assert envelope.eventType == "DOCUMENT_UPLOADED"


def test_event_envelope_timestamp() -> None:
    """Verify timestamp is ISO format."""
    envelope = EventEnvelope(
        eventType="DOCUMENT_PARSED",
        payload=DocumentEventPayload(documentId="doc_001", tenantId="t1"),
    )
    assert "T" in envelope.timestamp
    assert envelope.timestamp.endswith("Z")


def test_event_envelope_serialization() -> None:
    """Verify envelope can be serialized to JSON."""
    envelope = EventEnvelope(
        eventType="DOCUMENT_INDEXED",
        payload=DocumentEventPayload(
            documentId="doc_001",
            tenantId="t1",
            chunksVectorized=5,
            vectorCollection="tenant_embeddings_v1",
        ),
    )
    data = envelope.model_dump()
    assert data["eventType"] == "DOCUMENT_INDEXED"
    assert data["payload"]["chunksVectorized"] == 5
    assert data["payload"]["vectorCollection"] == "tenant_embeddings_v1"


def test_document_event_payload_defaults() -> None:
    """Verify optional fields default to None or empty list."""
    payload = DocumentEventPayload(documentId="doc_001", tenantId="t1")
    assert payload.chunkIds == []
    assert payload.fileName is None
    assert payload.failurePhase is None


# ── 2. RabbitMQ Event Publisher ──────────────────────────────────────────────


@patch("pika.BlockingConnection")
def test_publisher_declare_topology(mock_connection) -> None:
    """Verify declare_topology creates exchange, DLX, queues, and bindings."""
    from src.adapters.broker.rabbitmq_event_publisher import RabbitMQEventPublisher

    mock_channel = MagicMock()
    mock_connection.return_value.channel.return_value = mock_channel

    publisher = RabbitMQEventPublisher(amqp_url="amqp://localhost")
    asyncio.run(publisher.declare_topology())

    # Exchange declarations
    exchange_calls = list(mock_channel.exchange_declare.call_args_list)
    assert any("document.processing" in str(c) for c in exchange_calls)
    assert any("dead.letter.exchange" in str(c) for c in exchange_calls)

    # Queue declarations
    queue_calls = [c[1]["queue"] for c in mock_channel.queue_declare.call_args_list]
    assert "ingestion.parse" in queue_calls
    assert "knowledge.embed" in queue_calls
    assert "dead.letter" in queue_calls

    # Bindings
    bind_calls = [c[1] for c in mock_channel.queue_bind.call_args_list]
    routing_keys = [c.get("routing_key", "") for c in bind_calls]
    assert "document.event.uploaded" in routing_keys
    assert "document.event.parsed" in routing_keys


@patch("pika.BlockingConnection")
def test_publisher_publish(mock_connection) -> None:
    """Verify publish sends JSON to the exchange with correct routing key."""
    from src.adapters.broker.rabbitmq_event_publisher import (
        ROUTING_UPLOADED,
        RabbitMQEventPublisher,
    )

    mock_channel = MagicMock()
    mock_connection.return_value.channel.return_value = mock_channel

    envelope = EventEnvelope(
        eventType="DOCUMENT_UPLOADED",
        payload=DocumentEventPayload(documentId="doc_001", tenantId="t1"),
    )

    publisher = RabbitMQEventPublisher(amqp_url="amqp://localhost")
    asyncio.run(publisher.publish(envelope, ROUTING_UPLOADED))

    mock_channel.basic_publish.assert_called_once()
    call_kwargs = mock_channel.basic_publish.call_args[1]
    assert call_kwargs["exchange"] == "document.processing"
    assert call_kwargs["routing_key"] == "document.event.uploaded"
    assert "DOCUMENT_UPLOADED" in call_kwargs["body"].decode("utf-8")


# ── 3. Integration: Upload endpoint publishes event ──────────────────────────


@patch("src.adapters.broker.celery_publisher.celery_app.send_task")
@patch(
    "src.adapters.api.security.identity_provider.validate_token",
    new_callable=AsyncMock,
)
@patch("src.main.tenant_session")
def test_upload_publishes_event(
    mock_session_ctx, mock_validate, mock_send_task
) -> None:
    """Verify document upload submits a Celery processing task."""
    from fastapi.testclient import TestClient

    from src.main import app

    client = TestClient(app)
    tenant_id = "00000000-0000-0000-0000-000000000001"
    mock_validate.return_value = MagicMock(
        user_id="user_123",
        tenant_id=tenant_id,
        roles=["integrator"],
        scopes=["document:write"],
    )

    mock_db_session = MagicMock()
    mock_db_session.execute = AsyncMock()
    mock_db_session.commit = AsyncMock()
    mock_db_session.add = MagicMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_db_session

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    headers = {"Authorization": "Bearer ret_live_validtoken.secret"}
    response = client.post(
        f"/v1/tenants/{tenant_id}/documents",
        files={"file": ("test.txt", b"Hello world.", "text/plain")},
        headers=headers,
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert "documentId" in body
    assert "fileHash" in body

    # Verify Celery task was submitted
    mock_send_task.assert_called_once()
    call_args = mock_send_task.call_args
    assert call_args[0][0] == "process_document"
    assert call_args[1]["args"][0] == body["documentId"]


