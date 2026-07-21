import logging

from src.domain.abstractions.events import EventEnvelope, EventPublisher

logger = logging.getLogger(__name__)


class NoOpEventPublisher(EventPublisher):
    async def publish(self, envelope: EventEnvelope, routing_key: str) -> None:
        logger.info(
            "Event %s (%s) — no broker configured, event discarded",
            envelope.eventId,
            envelope.eventType,
        )

    async def declare_topology(self) -> None:
        logger.info("No broker configured — skipping topology declaration")
