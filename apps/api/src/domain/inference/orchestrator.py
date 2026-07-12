"""Inference Orchestrator Service.

Coordinates the end-to-end inference pipeline: prompt compilation,
LLM dispatch (with fallback), citation validation, and telemetry
logging. Depends only on domain abstractions.
"""

import time
from typing import AsyncIterator, Optional
from src.domain.abstractions.inference import (
    ChatMessage,
    ChatSessionInfo,
    InferenceRequest,
    InferenceResponse,
    InferenceLog,
    LlmProvider,
    ChatSessionRepository,
    InferenceLogWriter,
)
from src.domain.abstractions.retrieval import SearchResult
from src.domain.abstractions.config import TenantConfiguration
from src.domain.inference.prompt_builder import PromptBuilder
from src.domain.inference.citation_validator import CitationValidator


class InferenceOrchestrator:
    """Orchestrates the complete generative inference pipeline."""

    def __init__(
        self,
        llm_provider: LlmProvider,
        prompt_builder: PromptBuilder,
        citation_validator: CitationValidator,
        session_repo: ChatSessionRepository,
        log_writer: InferenceLogWriter,
    ) -> None:
        self.llm = llm_provider
        self.prompt_builder = prompt_builder
        self.citation_validator = citation_validator
        self.session_repo = session_repo
        self.log_writer = log_writer

    async def create_session(
        self, tenant_id: str
    ) -> ChatSessionInfo:
        """Create a new chat session."""
        return await self.session_repo.create_session(tenant_id)

    async def get_session(
        self, session_id: str, tenant_id: str
    ) -> Optional[ChatSessionInfo]:
        """Get a chat session, scoped to tenant."""
        return await self.session_repo.get_session(session_id, tenant_id)

    async def add_message(
        self, session_id: str, message: ChatMessage
    ) -> None:
        """Persist a message to session history."""
        await self.session_repo.add_message(session_id, message)

    async def get_history(
        self, session_id: str
    ) -> list[ChatMessage]:
        """Retrieve session message history."""
        return await self.session_repo.get_messages(session_id)

    async def generate(
        self,
        tenant_id: str,
        session_id: str,
        query: str,
        context_chunks: list[SearchResult],
        tenant_config: TenantConfiguration,
    ) -> InferenceResponse:
        """Execute a complete non-streaming inference pipeline.

        1. Fetch history
        2. Build prompt (system + context + history)
        3. Dispatch to LLM
        4. Validate citations
        5. Log telemetry
        """
        start = time.monotonic()

        history = await self.session_repo.get_messages(session_id)

        chunks_dict = [
            {"chunk_id": c.chunk_id, "content": c.content, "score": c.score}
            for c in context_chunks
        ]

        self.citation_validator.set_valid_ids(
            [c.chunk_id for c in context_chunks]
        )

        model_config = tenant_config.ai_provider
        prompt_messages = await self.prompt_builder.build_messages(
            tenant_id=tenant_id,
            query=query,
            history=history,
            context_chunks=chunks_dict,
            max_tokens=tenant_config.retrieval_settings.top_k * 500 or 4096,
            system_prompt_name="default",
        )

        request = InferenceRequest(
            messages=prompt_messages,
            temperature=model_config.temperature
            if hasattr(model_config, "temperature") else 0.7,
        )

        response = await self.llm.generate(
            request, {"model": model_config.default_model}
        )

        # Validate citations
        invalid = self.citation_validator.get_invalid_citations(response.content)
        if invalid:
            response.content += (
                "\n\n[WARNING: The following citations could not be verified: "
                + ", ".join(invalid)
                + "]"
            )

        elapsed = int((time.monotonic() - start) * 1000)

        await self.log_writer.write_log(
            InferenceLog(
                tenant_id=tenant_id,
                session_id=session_id,
                model_used=model_config.default_model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                latency_ms=elapsed,
            )
        )

        # Persist user message and assistant response
        await self.session_repo.add_message(
            session_id, ChatMessage(role="user", content=query)
        )
        await self.session_repo.add_message(
            session_id, ChatMessage(role="assistant", content=response.content)
        )

        return response

    async def generate_stream(
        self,
        tenant_id: str,
        session_id: str,
        query: str,
        context_chunks: list[SearchResult],
        tenant_config: TenantConfiguration,
    ) -> AsyncIterator[dict]:
        """Execute streaming inference, yielding token delta events.

        Yields dicts with keys:
          - ``event``: "token", "citation_error", or "done"
          - ``delta``: str (for "token" events)
          - ``usage``: dict (for "done" events)
        """
        start = time.monotonic()

        history = await self.session_repo.get_messages(session_id)

        chunks_dict = [
            {"chunk_id": c.chunk_id, "content": c.content, "score": c.score}
            for c in context_chunks
        ]

        self.citation_validator.set_valid_ids(
            [c.chunk_id for c in context_chunks]
        )

        model_config = tenant_config.ai_provider
        prompt_messages = await self.prompt_builder.build_messages(
            tenant_id=tenant_id,
            query=query,
            history=history,
            context_chunks=chunks_dict,
            max_tokens=tenant_config.retrieval_settings.top_k * 500 or 4096,
            system_prompt_name="default",
        )

        request = InferenceRequest(
            messages=prompt_messages,
            temperature=getattr(model_config, "temperature", 0.7),
        )

        full_content: list[str] = []
        citations_checked = False

        async for chunk in self.llm.generate_stream(
            request, {"model": model_config.default_model}
        ):
            delta = chunk.get("delta", chunk if isinstance(chunk, str) else "")
            if delta:
                full_content.append(delta)
                yield {"event": "token", "delta": delta}

            finish = chunk.get("finish_reason")
            if finish:
                break

        # Final response for citation check
        final_text = "".join(full_content)
        invalid = self.citation_validator.get_invalid_citations(final_text)
        if invalid:
            yield {
                "event": "citation_error",
                "invalid_citations": invalid,
            }

        elapsed = int((time.monotonic() - start) * 1000)

        # Persist messages
        await self.session_repo.add_message(
            session_id, ChatMessage(role="user", content=query)
        )
        await self.session_repo.add_message(
            session_id, ChatMessage(role="assistant", content=final_text)
        )

        usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        yield {
            "event": "done",
            "usage": usage,
            "latency_ms": elapsed,
        }
