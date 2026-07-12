"""Event Consumer — pika-based listener for the document processing queues.

Listens on ``ingestion.parse`` and ``knowledge.embed`` queues, dispatches
to the appropriate handler, and publishes follow-up events.
"""

import json
import os
import pika

from workers.src.tasks import process_document_async, _generate_embeddings_async

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//")
EXCHANGE_NAME = "document.processing"
DLX_NAME = "dead.letter.exchange"

QUEUE_INGESTION = "ingestion.parse"
QUEUE_EMBED = "knowledge.embed"

ROUTING_UPLOADED = "document.event.uploaded"
ROUTING_PARSED = "document.event.parsed"
ROUTING_FAILED = "document.event.failed"


def _declare_topology(channel: pika.channel.Channel) -> None:
    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="topic", durable=True)
    channel.exchange_declare(exchange=DLX_NAME, exchange_type="fanout", durable=True)

    channel.queue_declare(
        queue=QUEUE_INGESTION,
        durable=True,
        arguments={
            "x-dead-letter-exchange": DLX_NAME,
            "x-dead-letter-routing-key": QUEUE_INGESTION,
        },
    )
    channel.queue_bind(queue=QUEUE_INGESTION, exchange=EXCHANGE_NAME, routing_key=ROUTING_UPLOADED)

    channel.queue_declare(
        queue=QUEUE_EMBED,
        durable=True,
        arguments={
            "x-dead-letter-exchange": DLX_NAME,
            "x-dead-letter-routing-key": QUEUE_EMBED,
        },
    )
    channel.queue_bind(queue=QUEUE_EMBED, exchange=EXCHANGE_NAME, routing_key=ROUTING_PARSED)

    channel.queue_declare(
        queue="dead.letter",
        durable=True,
    )
    channel.queue_bind(queue="dead.letter", exchange=DLX_NAME, routing_key="")


def _handle_uploaded(channel, method, properties, body) -> None:
    """Handle DocumentUploadedEvent — trigger document parsing."""
    import asyncio
    envelope = json.loads(body)
    payload = envelope["payload"]
    doc_id = payload["documentId"]
    tenant_id = payload["tenantId"]
    storage_path = payload.get("storagePath", "")

    asyncio.run(process_document_async(doc_id, tenant_id, storage_path))
    channel.basic_ack(delivery_tag=method.delivery_tag)


def _handle_parsed(channel, method, properties, body) -> None:
    """Handle DocumentParsedEvent — trigger embedding generation."""
    import asyncio
    envelope = json.loads(body)
    payload = envelope["payload"]
    doc_id = payload["documentId"]
    tenant_id = payload["tenantId"]

    asyncio.run(_generate_embeddings_async(doc_id, tenant_id))
    channel.basic_ack(delivery_tag=method.delivery_tag)


def start_consumer() -> None:
    """Start the event consumer, listening on all processing queues.

    This replaces the Celery-only worker for event-driven task dispatch.
    """
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    _declare_topology(channel)

    channel.basic_consume(queue=QUEUE_INGESTION, on_message_callback=_handle_uploaded)
    channel.basic_consume(queue=QUEUE_EMBED, on_message_callback=_handle_parsed)

    print(" [*] Event consumer waiting on queues: ingestion.parse, knowledge.embed")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == "__main__":
    start_consumer()
