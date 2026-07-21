"""Inference Domain Abstractions (Ports).

Defines pure domain entities and abstract interfaces for the generative
inference pipeline — LLM interaction, prompt construction, citation
validation, and session tracking. Contains zero infrastructure imports.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

# ── Domain Models ──────────────────────────────────────────────────────────


class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    role: str
    content: str
    name: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    images: list[dict] = Field(default_factory=list)


class InferenceRequest(BaseModel):
    messages: list[ChatMessage]
    temperature: float = 0.7
    max_tokens: int | None = None
    json_schema: dict[str, Any] | None = None
    tools: list[dict[str, Any]] = Field(default_factory=list)


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


class InferenceResponse(BaseModel):
    content: str
    usage: Usage = Field(default_factory=Usage)
    finish_reason: str = "stop"


class PromptTemplate(BaseModel):
    prompt_id: str | None = None
    tenant_id: str | None = None
    name: str = "default"
    content: str = ""
    is_system_prompt: bool = False


class ChatSessionInfo(BaseModel):
    session_id: str
    tenant_id: str
    user_id: str | None = None
    created_at: str = ""


class InferenceLog(BaseModel):
    log_id: str | None = None
    tenant_id: str
    session_id: str | None = None
    user_id: str | None = None
    role: str | None = None
    key_id: str | None = None
    model_used: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    notes: str | None = None


# ── Ports (Abstract Interfaces) ────────────────────────────────────────────


class LlmProvider(ABC):
    """Port for external LLM / cognitive model providers."""

    @abstractmethod
    async def generate(
        self, request: InferenceRequest, configuration: dict[str, Any]
    ) -> InferenceResponse:
        """Execute a synchronous generation and return the full response."""
        pass

    @abstractmethod
    async def generate_stream(
        self, request: InferenceRequest, configuration: dict[str, Any]
    ) -> Any:
        """Execute a streaming generation, yielding delta strings.

        Returns an async iterable that yields JSON-serialisable dicts
        with keys ``delta`` (str) and optionally ``finish_reason`` (str).
        """
        pass


class PromptTemplateRegistry(ABC):
    """Port for resolving prompt templates from storage."""

    @abstractmethod
    async def get_template(
        self, tenant_id: str, name: str, bypass_rls: bool = False
    ) -> PromptTemplate | None:
        """Retrieve a named prompt template for a tenant."""
        pass

    @abstractmethod
    async def save_template(
        self, tenant_id: str, template: PromptTemplate, bypass_rls: bool = False
    ) -> None:
        """Persist a prompt template."""
        pass

    @abstractmethod
    async def list_templates(self, tenant_id: str, bypass_rls: bool = False) -> list[PromptTemplate]:
        """List all prompt templates for a tenant."""
        pass

    @abstractmethod
    async def delete_template(self, tenant_id: str, name: str, bypass_rls: bool = False) -> bool:
        """Delete a named prompt template. Returns True if found and deleted."""
        pass


class ChatMessageInfo(BaseModel):
    message_id: str
    session_id: str
    tenant_id: str
    role: str
    content: str
    name: str | None = None
    created_at: str


class ChatSessionRepository(ABC):
    """Port for chat session and message persistence."""

    @abstractmethod
    async def create_session(
        self, tenant_id: str, user_id: str | None = None
    ) -> ChatSessionInfo:
        """Create a new chat session and return its metadata."""
        pass

    @abstractmethod
    async def get_session(
        self, session_id: str, tenant_id: str
    ) -> ChatSessionInfo | None:
        """Retrieve a chat session by ID, scoped to tenant."""
        pass

    @abstractmethod
    async def add_message(
        self, tenant_id: str, session_id: str, message: ChatMessage, user_id: str | None = None
    ) -> None:
        """Append a message to a tenant-scoped session's history."""
        pass

    @abstractmethod
    async def get_messages(
        self, tenant_id: str, session_id: str
    ) -> list[ChatMessage]:
        """Retrieve all messages for a tenant-scoped session in chronological order."""
        pass

    @abstractmethod
    async def get_messages_cursor(
        self, tenant_id: str, session_id: str, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[ChatMessageInfo], str | None, bool]:
        """Retrieve messages for a session using cursor-based pagination."""
        pass

    @abstractmethod
    async def get_message(
        self, tenant_id: str, session_id: str, message_id: str
    ) -> ChatMessageInfo | None:
        """Retrieve a single message by ID within a tenant-scoped session."""
        pass


class InferenceLogWriter(ABC):
    """Port for persisting inference telemetry records."""

    @abstractmethod
    async def write_log(self, log: InferenceLog) -> None:
        """Persist an inference log entry."""
        pass


class ChatMessageFeedback(BaseModel):
    feedback_id: str | None = None
    tenant_id: str
    message_id: str
    user_id: str | None = None
    rating: int = 0
    feedback_text: str | None = None
    scores: dict[str, int] | None = None
    created_at: str = ""


class FeedbackRepository(ABC):
    """Port for message feedback loops."""

    @abstractmethod
    async def submit_feedback(self, feedback: ChatMessageFeedback) -> None:
        """Submit or update feedback for a message."""
        pass

    @abstractmethod
    async def get_feedback_analytics(self, tenant_id: str) -> dict[str, Any]:
        """Aggregate feedback analytics for a tenant."""
        pass

