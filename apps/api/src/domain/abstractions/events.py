"""Event Domain Abstractions (Ports).

Defines the event envelope format and publishing port for the
event-driven document processing pipeline. Contains zero infrastructure imports.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime

from pydantic import BaseModel, Field


def _generate_event_id() -> str:
    return f"evt_{uuid.uuid4().hex}"


class DocumentEventPayload(BaseModel):
    documentId: str
    tenantId: str
    fileName: str | None = None
    storagePath: str | None = None
    mimeType: str | None = None
    chunkIds: list[str] = Field(default_factory=list)
    chunksVectorized: int | None = None
    vectorCollection: str | None = None
    failurePhase: str | None = None
    errorMessage: str | None = None


class EventEnvelope(BaseModel):
    eventId: str = Field(default_factory=_generate_event_id)
    eventType: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    traceId: str = ""
    payload: DocumentEventPayload


class EventPublisher(ABC):
    @abstractmethod
    async def publish(self, envelope: EventEnvelope, routing_key: str) -> None:
        pass

    @abstractmethod
    async def declare_topology(self) -> None:
        pass
