"""Inference Orchestrator Service.

Coordinates the end-to-end inference pipeline: prompt compilation,
LLM dispatch (with fallback), citation validation, cost calculation,
and telemetry logging. Depends only on domain abstractions.
"""

import time
from collections.abc import AsyncIterator

from src.domain.abstractions.config import ModelPricing, TenantConfiguration
from src.domain.abstractions.inference import (
    ChatMessage,
    ChatSessionInfo,
    ChatSessionRepository,
    InferenceLog,
    InferenceLogWriter,
    InferenceRequest,
    InferenceResponse,
    LlmProvider,
    Usage,
)
from src.domain.abstractions.retrieval import SearchResult
from src.domain.abstractions.telemetry import MetricsRegistry
from src.domain.inference.citation_validator import CitationValidator
from src.domain.inference.cost_calculator import calculate_cost
from src.domain.inference.prompt_builder import PromptBuilder


SUMMARIZE_PROMPT = (
    "Summarize the following conversation concisely, preserving key facts, "
    "decisions, user preferences, and any information needed to continue "
    "coherently. Focus on factual content over conversational flow."
)


def _lookup_pricing(model: str, pricing: dict[str, ModelPricing]) -> ModelPricing | None:
    return pricing.get(model)


class InferenceOrchestrator:
    """Orchestrates the complete generative inference pipeline."""

    def __init__(
        self,
        llm_provider: LlmProvider,
        prompt_builder: PromptBuilder,
        citation_validator: CitationValidator,
        session_repo: ChatSessionRepository,
        log_writer: InferenceLogWriter,
        metrics_registry: MetricsRegistry | None = None,
    ) -> None:
        self.llm = llm_provider
        self.prompt_builder = prompt_builder
        self.citation_validator = citation_validator
        self.session_repo = session_repo
        self.log_writer = log_writer
        self.metrics = metrics_registry

    async def create_session(
        self, tenant_id: str, user_id: str | None = None
    ) -> ChatSessionInfo:
        """Create a new chat session."""
        return await self.session_repo.create_session(tenant_id, user_id)

    async def get_session(
        self, session_id: str, tenant_id: str
    ) -> ChatSessionInfo | None:
        """Get a chat session, scoped to tenant."""
        return await self.session_repo.get_session(session_id, tenant_id)

    async def add_message(
        self, tenant_id: str, session_id: str, message: ChatMessage, user_id: str | None = None
    ) -> None:
        """Persist a message to session history."""
        await self.session_repo.add_message(tenant_id, session_id, message, user_id)

    async def get_history(
        self, tenant_id: str, session_id: str
    ) -> list[ChatMessage]:
        """Retrieve session message history."""
        return await self.session_repo.get_messages(tenant_id, session_id)

    async def _summarize_history(
        self,
        history: list[ChatMessage],
        summarize_after: int,
        config_dict: dict,
    ) -> list[ChatMessage]:
        if len(history) <= summarize_after:
            return history
        # messages alternate user/assistant — count turns as pairs
        turns = len(history) // 2
        if turns <= summarize_after:
            return history
        num_to_summarize = (turns - summarize_after + 1) * 2
        old = history[:num_to_summarize]
        rest = history[num_to_summarize:]
        conversation_text = "\n".join(f"{m.role}: {m.content}" for m in old)
        try:
            summary_resp = await self.llm.generate(
                InferenceRequest(messages=[
                    ChatMessage(role="system", content=SUMMARIZE_PROMPT),
                    ChatMessage(role="user", content=conversation_text),
                ]),
                config_dict,
            )
            summary_msg = ChatMessage(
                role="system",
                content=f"[Summary of previous conversation]: {summary_resp.content}"
            )
            return [summary_msg] + rest
        except Exception:
            return history

    async def generate(
        self,
        tenant_id: str,
        session_id: str,
        query: str,
        context_chunks: list[SearchResult],
        tenant_config: TenantConfiguration,
        user_id: str | None = None,
        system_prompt_name: str = "default",
    ) -> InferenceResponse:
        """Execute a complete non-streaming inference pipeline.

        1. Fetch history
        2. Summarize long histories (>15 turns)
        3. Build prompt (system + context + history)
        4. Dispatch to LLM
        5. Validate citations
        6. Log telemetry
        """
        start = time.monotonic()

        history = await self.session_repo.get_messages(tenant_id, session_id)
        model_config = tenant_config.ai_provider
        summarize_after = tenant_config.retrieval_settings.summarize_after_turns
        if summarize_after > 0 and len(history) > summarize_after * 2:
            config_dict = model_config.model_dump()
            config_dict["model"] = model_config.default_model
            history = await self._summarize_history(history, summarize_after, config_dict)

        chunks_dict = [
            {"chunk_id": c.chunk_id, "content": c.content, "score": c.score}
            for c in context_chunks
        ]

        self.citation_validator.set_valid_ids(
            [c.chunk_id for c in context_chunks]
        )

        prompt_messages = await self.prompt_builder.build_messages(
            tenant_id=tenant_id,
            query=query,
            history=history,
            context_chunks=chunks_dict,
            max_tokens=tenant_config.retrieval_settings.top_k * 500 or 4096,
            system_prompt_name=system_prompt_name,
        )

        request = InferenceRequest(
            messages=prompt_messages,
            temperature=model_config.temperature
            if hasattr(model_config, "temperature") else 0.7,
        )

        config_dict = model_config.model_dump()
        config_dict["model"] = model_config.default_model
        response = await self.llm.generate(
            request, config_dict
        )
        actual_provider = config_dict.get("_actual_provider")

        # Calculate cost
        model_used = model_config.default_model
        pricing = model_config.pricing
        cost = calculate_cost(response.usage, model_used, pricing)

        # Validate citations
        invalid = self.citation_validator.get_invalid_citations(response.content)
        if invalid:
            response.content += (
                "\n\n[WARNING: The following citations could not be verified: "
                + ", ".join(invalid)
                + "]"
            )

        elapsed = int((time.monotonic() - start) * 1000)

        notes = None
        if actual_provider:
            notes = f"actual_provider={actual_provider}"

        if self.metrics:
            self.metrics.increment("TOKEN_CONSUMPTION", value=response.usage.input_tokens, labels={
                "tenant_id": tenant_id, "model": model_used, "type": "input"
            })
            self.metrics.increment("TOKEN_CONSUMPTION", value=response.usage.output_tokens, labels={
                "tenant_id": tenant_id, "model": model_used, "type": "output"
            })
            self.metrics.increment("COST_SPEND", value=cost, labels={
                "tenant_id": tenant_id, "model": model_used
            })

        await self.log_writer.write_log(
            InferenceLog(
                tenant_id=tenant_id,
                session_id=session_id,
                user_id=user_id,
                model_used=model_used,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                latency_ms=elapsed,
                cost_usd=cost,
                notes=notes,
            )
        )

        # Persist user message and assistant response
        await self.session_repo.add_message(
            tenant_id, session_id, ChatMessage(role="user", content=query), user_id
        )
        await self.session_repo.add_message(
            tenant_id,
            session_id,
            ChatMessage(role="assistant", content=response.content),
            user_id,
        )

        return response

    async def generate_stream(
        self,
        tenant_id: str,
        session_id: str,
        query: str,
        context_chunks: list[SearchResult],
        tenant_config: TenantConfiguration,
        user_id: str | None = None,
        system_prompt_name: str = "default",
    ) -> AsyncIterator[dict]:
        """Execute streaming inference, yielding token delta events.

        Yields dicts with keys:
          - ``event``: "token", "citation_error", or "done"
          - ``delta``: str (for "token" events)
          - ``usage``: dict (for "done" events)
        """
        start = time.monotonic()

        history = await self.session_repo.get_messages(tenant_id, session_id)
        model_config = tenant_config.ai_provider
        summarize_after = tenant_config.retrieval_settings.summarize_after_turns
        if summarize_after > 0 and len(history) > summarize_after * 2:
            config_dict = model_config.model_dump()
            config_dict["model"] = model_config.default_model
            history = await self._summarize_history(history, summarize_after, config_dict)

        chunks_dict = [
            {"chunk_id": c.chunk_id, "content": c.content, "score": c.score}
            for c in context_chunks
        ]

        self.citation_validator.set_valid_ids(
            [c.chunk_id for c in context_chunks]
        )

        prompt_messages = await self.prompt_builder.build_messages(
            tenant_id=tenant_id,
            query=query,
            history=history,
            context_chunks=chunks_dict,
            max_tokens=tenant_config.retrieval_settings.top_k * 500 or 4096,
            system_prompt_name=system_prompt_name,
        )

        request = InferenceRequest(
            messages=prompt_messages,
            temperature=getattr(model_config, "temperature", 0.7),
        )

        full_content: list[str] = []
        input_tokens = 0
        output_tokens = 0

        config_dict = model_config.model_dump()
        config_dict["model"] = model_config.default_model
        async for chunk in self.llm.generate_stream(
            request, config_dict
        ):
            if chunk.get("event") == "info":
                yield chunk
                continue
            delta = chunk.get("delta", chunk if isinstance(chunk, str) else "")
            if delta:
                full_content.append(delta)
                yield {"event": "token", "delta": delta}

            finish = chunk.get("finish_reason")
            if finish:
                break

            usage = chunk.get("usage")
            if usage:
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)

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
            tenant_id, session_id, ChatMessage(role="user", content=query), user_id
        )
        await self.session_repo.add_message(
            tenant_id, session_id, ChatMessage(role="assistant", content=final_text), user_id
        )

        actual_provider = config_dict.get("_actual_provider")
        notes = None
        if actual_provider:
            notes = f"actual_provider={actual_provider}"

        model_used = model_config.default_model
        usage = Usage(input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=input_tokens + output_tokens)
        cost = calculate_cost(usage, model_used, model_config.pricing)

        if self.metrics:
            self.metrics.increment("TOKEN_CONSUMPTION", value=input_tokens, labels={
                "tenant_id": tenant_id, "model": model_used, "type": "input"
            })
            self.metrics.increment("TOKEN_CONSUMPTION", value=output_tokens, labels={
                "tenant_id": tenant_id, "model": model_used, "type": "output"
            })
            self.metrics.increment("COST_SPEND", value=cost, labels={
                "tenant_id": tenant_id, "model": model_used
            })

        await self.log_writer.write_log(
            InferenceLog(
                tenant_id=tenant_id,
                session_id=session_id,
                user_id=user_id,
                model_used=model_used,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=elapsed,
                cost_usd=cost,
                notes=notes,
            )
        )

        total = input_tokens + output_tokens
        yield {
            "event": "done",
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": total},
            "latency_ms": elapsed,
        }
