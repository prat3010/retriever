"""RabbitMQ Event Publisher Adapter.

Implements the EventPublisher port using pika with the documented
exchange/queue topology and structured event envelopes.
"""

import pika

from src.domain.abstractions.events import EventEnvelope, EventPublisher

EXCHANGE_NAME = "document.processing"
EXCHANGE_TYPE = "topic"
DLX_NAME = "dead.letter.exchange"

QUEUES_AND_ROUTING: dict[str, list[str]] = {
    "ingestion.parse": ["document.event.uploaded"],
    "knowledge.embed": ["document.event.parsed"],
    "dead.letter": ["document.event.failed"],
}

ROUTING_UPLOADED = "document.event.uploaded"
ROUTING_PARSED = "document.event.parsed"
ROUTING_INDEXED = "document.event.indexed"
ROUTING_FAILED = "document.event.failed"


class RabbitMQEventPublisher(EventPublisher):
    def __init__(self, amqp_url: str = "amqp://guest:guest@localhost:5672//") -> None:
        self._amqp_url = amqp_url
        self._connection: pika.BlockingConnection | None = None
        self._channel: pika.channel.Channel | None = None

    def _ensure_channel(self) -> pika.channel.Channel:
        if not self._connection or self._connection.is_closed:
            params = pika.URLParameters(self._amqp_url)
            self._connection = pika.BlockingConnection(params)
        if not self._channel or self._channel.is_closed:
            self._channel = self._connection.channel()
        return self._channel

    async def declare_topology(self) -> None:
        ch = self._ensure_channel()

        ch.exchange_declare(
            exchange=EXCHANGE_NAME, exchange_type=EXCHANGE_TYPE, durable=True
        )
        ch.exchange_declare(
            exchange=DLX_NAME, exchange_type="fanout", durable=True
        )

        for queue_name, routing_keys in QUEUES_AND_ROUTING.items():
            ch.queue_declare(
                queue=queue_name,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": DLX_NAME,
                    "x-dead-letter-routing-key": queue_name,
                },
            )
            for rk in routing_keys:
                ch.queue_bind(queue=queue_name, exchange=EXCHANGE_NAME, routing_key=rk)

    async def publish(self, envelope: EventEnvelope, routing_key: str) -> None:
        ch = self._ensure_channel()
        body = envelope.model_dump_json().encode("utf-8")
        ch.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=routing_key,
            body=body,
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
                message_id=envelope.eventId,
            ),
        )

    async def close(self) -> None:
        if self._channel and not self._channel.is_closed:
            self._channel.close()
        if self._connection and not self._connection.is_closed:
            self._connection.close()
