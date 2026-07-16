"""Inference Orchestrator Service.

Coordinates the end-to-end inference pipeline: prompt compilation,
LLM dispatch (with fallback), citation validation, cost calculation,
and telemetry logging. Depends only on domain abstractions.
"""

import time
from collections import defaultdict
from collections.abc import AsyncIterator
from datetime import date

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
from src.domain.abstractions.notifications import NotificationProvider
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
        notification_provider: NotificationProvider | None = None,
    ) -> None:
        self.llm = llm_provider
        self.prompt_builder = prompt_builder
        self.citation_validator = citation_validator
        self.session_repo = session_repo
        self.log_writer = log_writer
        self.metrics = metrics_registry
        self.notifier = notification_provider
        self._daily_costs: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._monthly_costs: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._notified: set[str] = set()

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

    async def _prepare_inference(
        self,
        tenant_id: str,
        session_id: str,
        query: str,
        context_chunks: list[SearchResult],
        tenant_config: TenantConfiguration,
        system_prompt_name: str,
    ) -> tuple[list[ChatMessage], TenantConfiguration, dict]:
        model_config = tenant_config.ai_provider
        history = await self.session_repo.get_messages(tenant_id, session_id)

        summarize_after = tenant_config.retrieval_settings.summarize_after_turns
        if summarize_after > 0 and len(history) > summarize_after * 2:
            config_dict = model_config.model_dump()
            config_dict["model"] = model_config.default_model
            history = await self._summarize_history(history, summarize_after, config_dict)

        chunks_dict = [
            {"chunk_id": c.chunk_id, "document_id": c.document_id, "content": c.content, "score": c.score, "metadata": c.metadata}
            for c in context_chunks
        ]

        self.citation_validator.set_valid_ids([c.chunk_id for c in context_chunks])

        prompt_messages = await self.prompt_builder.build_messages(
            tenant_id=tenant_id,
            query=query,
            history=history,
            context_chunks=chunks_dict,
            max_tokens=tenant_config.retrieval_settings.top_k * 500 or 4096,
            system_prompt_name=system_prompt_name,
        )

        return prompt_messages, model_config

    def _build_notes(self, actual_provider: str | None, experiment_id: str | None = None, experiment_variant: str | None = None) -> str | None:
        notes = f"actual_provider={actual_provider}" if actual_provider else None
        if experiment_id and experiment_variant:
            exp = f"experiment={experiment_id},variant={experiment_variant}"
            notes = f"{notes};{exp}" if notes else exp
        return notes

    async def _record_metrics(
        self,
        tenant_id: str,
        model_used: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
    ) -> None:
        if not self.metrics:
            return
        self.metrics.increment("TOKEN_CONSUMPTION", value=input_tokens, labels={
            "tenant_id": tenant_id, "model": model_used, "type": "input"
        })
        self.metrics.increment("TOKEN_CONSUMPTION", value=output_tokens, labels={
            "tenant_id": tenant_id, "model": model_used, "type": "output"
        })
        self.metrics.increment("COST_SPEND", value=cost, labels={
            "tenant_id": tenant_id, "model": model_used
        })

    async def _check_budget(
        self,
        tenant_id: str,
        cost: float,
        budget: object,
    ) -> None:
        if not self.notifier:
            return
        daily_budget = getattr(budget, "daily_cost_budget", None) if budget else None
        monthly_budget = getattr(budget, "monthly_cost_budget", None) if budget else None
        if not daily_budget and not monthly_budget:
            return

        today = date.today().isoformat()
        this_month = date.today().strftime("%Y-%m")
        self._daily_costs[tenant_id][today] += cost
        self._monthly_costs[tenant_id][this_month] += cost

        daily_total = self._daily_costs[tenant_id][today]
        monthly_total = self._monthly_costs[tenant_id][this_month]

        if daily_budget and daily_total >= daily_budget:
            key = f"{tenant_id}_daily_{this_month}"
            if key not in self._notified:
                self._notified.add(key)
                await self.notifier.send_alert(
                    tenant_id,
                    f"Daily cost ${daily_total:.2f} exceeds budget ${daily_budget:.2f}",
                    severity="warning",
                )

        if monthly_budget and monthly_total >= monthly_budget:
            key = f"{tenant_id}_monthly_{this_month}"
            if key not in self._notified:
                self._notified.add(key)
                await self.notifier.send_alert(
                    tenant_id,
                    f"Monthly cost ${monthly_total:.2f} exceeds budget ${monthly_budget:.2f}",
                    severity="critical",
                )

    async def _log_inference(
        self,
        tenant_id: str,
        session_id: str,
        user_id: str | None,
        model_used: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        cost: float,
        notes: str | None,
    ) -> None:
        await self.log_writer.write_log(
            InferenceLog(
                tenant_id=tenant_id,
                session_id=session_id,
                user_id=user_id,
                model_used=model_used,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                cost_usd=cost,
                notes=notes,
            )
        )

    async def _persist_messages(
        self,
        tenant_id: str,
        session_id: str,
        query: str,
        content: str,
        user_id: str | None,
    ) -> None:
        await self.session_repo.add_message(
            tenant_id, session_id, ChatMessage(role="user", content=query), user_id
        )
        await self.session_repo.add_message(
            tenant_id, session_id, ChatMessage(role="assistant", content=content), user_id
        )

    async def generate(
        self,
        tenant_id: str,
        session_id: str,
        query: str,
        context_chunks: list[SearchResult],
        tenant_config: TenantConfiguration,
        user_id: str | None = None,
        system_prompt_name: str = "default",
        experiment_id: str | None = None,
        experiment_variant: str | None = None,
    ) -> InferenceResponse:
        start = time.monotonic()

        prompt_messages, model_config = await self._prepare_inference(
            tenant_id, session_id, query, context_chunks, tenant_config, system_prompt_name
        )

        request = InferenceRequest(
            messages=prompt_messages,
            temperature=getattr(model_config, "temperature", 0.7),
            json_schema=tenant_config.retrieval_settings.json_schema,
        )

        config_dict = model_config.model_dump()
        config_dict["model"] = model_config.default_model
        response = await self.llm.generate(request, config_dict)

        model_used = model_config.default_model
        cost = calculate_cost(response.usage, model_used, model_config.pricing)

        if self.citation_validator.get_invalid_citations(response.content):
            response.content = self.citation_validator.strip_invalid_citations(response.content)

        self._emit_search_quality_metrics(tenant_id, context_chunks, response.content)

        elapsed = int((time.monotonic() - start) * 1000)
        notes = self._build_notes(config_dict.get("_actual_provider"), experiment_id, experiment_variant)

        await self._record_metrics(tenant_id, model_used, response.usage.input_tokens, response.usage.output_tokens, cost)
        await self._check_budget(tenant_id, cost, tenant_config.budget_settings)
        await self._log_inference(tenant_id, session_id, user_id, model_used, response.usage.input_tokens, response.usage.output_tokens, elapsed, cost, notes)
        await self._persist_messages(tenant_id, session_id, query, response.content, user_id)

        return response

    def _emit_search_quality_metrics(
        self,
        tenant_id: str,
        context_chunks: list[SearchResult],
        response_text: str,
    ) -> None:
        if self.metrics is None:
            return
        cited = self.citation_validator.extract_citations(response_text)
        if not cited:
            return
        from src.domain.evaluation.search_metrics import compute_search_metrics
        sq = compute_search_metrics(
            retrieved_chunk_ids=[c.chunk_id for c in context_chunks],
            relevant_chunk_ids=cited,
        )
        self.metrics.observe("search_ndcg_at_10", sq.ndcg_at_10, {"tenant_id": tenant_id})
        self.metrics.observe("search_mrr", sq.mrr, {"tenant_id": tenant_id})
        self.metrics.observe("search_hit_rate_at_10", sq.hit_rate_at_10, {"tenant_id": tenant_id})

    async def generate_stream(
        self,
        tenant_id: str,
        session_id: str,
        query: str,
        context_chunks: list[SearchResult],
        tenant_config: TenantConfiguration,
        user_id: str | None = None,
        system_prompt_name: str = "default",
        experiment_id: str | None = None,
        experiment_variant: str | None = None,
    ) -> AsyncIterator[dict]:
        start = time.monotonic()

        prompt_messages, model_config = await self._prepare_inference(
            tenant_id, session_id, query, context_chunks, tenant_config, system_prompt_name
        )

        request = InferenceRequest(
            messages=prompt_messages,
            temperature=getattr(model_config, "temperature", 0.7),
            json_schema=tenant_config.retrieval_settings.json_schema,
        )

        full_content: list[str] = []
        input_tokens = 0
        output_tokens = 0

        config_dict = model_config.model_dump()
        config_dict["model"] = model_config.default_model
        async for chunk in self.llm.generate_stream(request, config_dict):
            if chunk.get("event") == "info":
                yield chunk
                continue
            delta = chunk.get("delta", chunk if isinstance(chunk, str) else "")
            if delta:
                full_content.append(delta)
                yield {"event": "token", "delta": delta}

            # Do not break on finish_reason so trailing usage metadata can be processed
            usage = chunk.get("usage")
            if usage:
                if "input_tokens" in usage and usage["input_tokens"] > 0:
                    input_tokens = usage["input_tokens"]
                if "output_tokens" in usage and usage["output_tokens"] > 0:
                    output_tokens = usage["output_tokens"]

        final_text = "".join(full_content)
        invalid = self.citation_validator.get_invalid_citations(final_text)
        if invalid:
            yield {"event": "citation_error", "invalid_citations": invalid}
            final_text = self.citation_validator.strip_invalid_citations(final_text)

        self._emit_search_quality_metrics(tenant_id, context_chunks, final_text)

        elapsed = int((time.monotonic() - start) * 1000)
        await self._persist_messages(tenant_id, session_id, query, final_text, user_id)

        model_used = model_config.default_model
        usage = Usage(input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=input_tokens + output_tokens)
        cost = calculate_cost(usage, model_used, model_config.pricing)
        notes = self._build_notes(config_dict.get("_actual_provider"), experiment_id, experiment_variant)

        await self._record_metrics(tenant_id, model_used, input_tokens, output_tokens, cost)
        await self._check_budget(tenant_id, cost, tenant_config.budget_settings)
        await self._log_inference(tenant_id, session_id, user_id, model_used, input_tokens, output_tokens, elapsed, cost, notes)

        yield {
            "event": "done",
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": input_tokens + output_tokens},
            "latency_ms": elapsed,
        }
