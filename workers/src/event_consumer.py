"""DEPRECATED — pika-based listener replaced by Celery worker.

Kept as a local-development fallback. For production use
``celery -A workers.src.celery_app worker`` instead.
"""

import asyncio
import json
import os
import threading
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


class AsyncLoopManager:
    """Holds a single long-lived asyncio event loop on a daemon thread."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> asyncio.AbstractEventLoop:
        loop = asyncio.new_event_loop()
        self._loop = loop
        self._thread = threading.Thread(
            target=loop.run_forever, daemon=True, name="async-loop"
        )
        self._thread.start()
        return loop

    def stop(self) -> None:
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=5)

    def run_async(self, coro) -> None:
        if self._loop is None:
            raise RuntimeError("AsyncLoopManager not started")
        asyncio.run_coroutine_threadsafe(coro, self._loop)

    def ensure_ack(self, channel, delivery_tag) -> None:
        """Schedule an ack on the async loop thread to be safe."""
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(
            channel.basic_ack, delivery_tag=delivery_tag
        )


_loop_manager = AsyncLoopManager()


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
    envelope = json.loads(body)
    payload = envelope["payload"]
    doc_id = payload["documentId"]
    tenant_id = payload["tenantId"]
    storage_path = payload.get("storagePath", "")

    _loop_manager.run_async(_process(doc_id, tenant_id, storage_path, channel, method))


def _handle_parsed(channel, method, properties, body) -> None:
    envelope = json.loads(body)
    payload = envelope["payload"]
    doc_id = payload["documentId"]
    tenant_id = payload["tenantId"]

    _loop_manager.run_async(_embed(doc_id, tenant_id, channel, method))


async def _process(doc_id, tenant_id, storage_path, channel, method) -> None:
    try:
        await process_document_async(doc_id, tenant_id, storage_path)
    except Exception:
        # already handled inside process_document_async
        pass
    finally:
        _loop_manager.ensure_ack(channel, method.delivery_tag)


async def _embed(doc_id, tenant_id, channel, method) -> None:
    try:
        await _generate_embeddings_async(doc_id, tenant_id)
    except Exception:
        pass
    finally:
        _loop_manager.ensure_ack(channel, method.delivery_tag)


def start_consumer() -> None:
    """Start the event consumer, listening on all processing queues."""
    _loop_manager.start()
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
        _loop_manager.stop()


if __name__ == "__main__":
    start_consumer()
