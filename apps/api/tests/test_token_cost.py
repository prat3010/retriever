"""Tests for M20: Token Cost Optimization."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.abstractions.inference import (
    ChatMessage,
    InferenceRequest,
    InferenceResponse,
    Usage,
)

# ── Step 1: ModelPricing config ─────────────────────────────────────────────


def test_model_pricing_default() -> None:
    from src.domain.abstractions.config import ModelPricing

    p = ModelPricing()
    assert p.input_cost_per_1k == 0.0
    assert p.output_cost_per_1k == 0.0
    assert p.currency == "USD"


def test_default_pricing_has_expected_models() -> None:
    from src.domain.abstractions.config import DEFAULT_PRICING

    assert "gemini-1.5-flash" in DEFAULT_PRICING
    assert "gpt-4o" in DEFAULT_PRICING
    assert "claude-3-5-sonnet-20240620" in DEFAULT_PRICING
    assert DEFAULT_PRICING["gemini-1.5-flash"].input_cost_per_1k == 0.075


def test_ai_provider_config_has_pricing() -> None:
    from src.domain.abstractions.config import AIProviderConfig

    cfg = AIProviderConfig()
    assert "gemini-1.5-flash" in cfg.pricing


def test_retrieval_settings_has_summarize_after_turns() -> None:
    from src.domain.abstractions.config import RetrievalSettings

    s = RetrievalSettings()
    assert s.summarize_after_turns == 15


# ── Step 2: cost_usd fields ─────────────────────────────────────────────────


def test_usage_has_cost_usd() -> None:
    u = Usage(input_tokens=100, output_tokens=50, total_tokens=150)
    assert u.cost_usd == 0.0
    u.cost_usd = 0.015
    assert u.cost_usd == 0.015


def test_inference_log_has_cost_usd() -> None:
    from src.domain.abstractions.inference import InferenceLog

    log = InferenceLog(tenant_id="t1", cost_usd=0.042)
    assert log.cost_usd == 0.042


# ── Cost calculator ─────────────────────────────────────────────────────────


def test_calculate_cost_with_pricing() -> None:
    from src.domain.abstractions.config import ModelPricing
    from src.domain.inference.cost_calculator import calculate_cost

    pricing = {"my-model": ModelPricing(input_cost_per_1k=1.0, output_cost_per_1k=2.0)}
    usage = Usage(input_tokens=1000, output_tokens=500, total_tokens=1500)

    cost = calculate_cost(usage, "my-model", pricing)
    # 1000 * 1.0 / 1000 + 500 * 2.0 / 1000 = 1.0 + 1.0 = 2.0
    assert cost == 2.0


def test_calculate_cost_unknown_model() -> None:
    from src.domain.inference.cost_calculator import calculate_cost

    usage = Usage(input_tokens=1000, output_tokens=500, total_tokens=1500)
    cost = calculate_cost(usage, "unknown-model", {})
    assert cost == 0.0


def test_calculate_cost_zero_pricing() -> None:
    from src.domain.abstractions.config import ModelPricing
    from src.domain.inference.cost_calculator import calculate_cost

    pricing = {"my-model": ModelPricing()}
    usage = Usage(input_tokens=1000, output_tokens=500, total_tokens=1500)
    cost = calculate_cost(usage, "my-model", pricing)
    assert cost == 0.0


# ── Orchestrator cost tracking ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_orchestrator_logs_cost_usd() -> None:
    from src.domain.abstractions.config import TenantConfiguration
    from src.domain.abstractions.inference import InferenceLog
    from src.domain.abstractions.retrieval import SearchResult
    from src.domain.inference.citation_validator import CitationValidator
    from src.domain.inference.orchestrator import InferenceOrchestrator
    from src.domain.inference.prompt_builder import PromptBuilder

    mock_llm = AsyncMock()
    mock_llm.generate.return_value = InferenceResponse(
        content="Hello",
        usage=Usage(input_tokens=100, output_tokens=50, total_tokens=150),
    )

    mock_registry = AsyncMock()
    mock_registry.get_template.return_value = MagicMock(content="You are helpful.")

    mock_session_repo = AsyncMock()
    mock_session_repo.get_messages.return_value = []
    mock_session_repo.add_message.return_value = None

    mock_log_writer = AsyncMock()
    mock_metrics = MagicMock()

    orchestrator = InferenceOrchestrator(
        llm_provider=mock_llm,
        prompt_builder=PromptBuilder(template_registry=mock_registry),
        citation_validator=CitationValidator(),
        session_repo=mock_session_repo,
        log_writer=mock_log_writer,
        metrics_registry=mock_metrics,
    )

    config = TenantConfiguration(tenant_id="t1")
    # gemini-1.5-flash: input=0.075/1k, output=0.30/1k
    # cost = 100 * 0.075/1000 + 50 * 0.30/1000 = 0.0075 + 0.015 = 0.0225

    await orchestrator.generate(
        tenant_id="t1",
        session_id="ses_001",
        query="hi",
        context_chunks=[
            SearchResult(chunk_id="c1", document_id="d1", content="Hello", score=0.9)
        ],
        tenant_config=config,
    )

    log_call = mock_log_writer.write_log.call_args[0][0]
    assert isinstance(log_call, InferenceLog)
    assert log_call.cost_usd == 0.0225
    assert log_call.input_tokens == 100
    assert log_call.output_tokens == 50


@pytest.mark.asyncio
async def test_orchestrator_emits_metrics() -> None:
    from src.domain.abstractions.config import TenantConfiguration
    from src.domain.abstractions.retrieval import SearchResult
    from src.domain.inference.citation_validator import CitationValidator
    from src.domain.inference.orchestrator import InferenceOrchestrator
    from src.domain.inference.prompt_builder import PromptBuilder

    mock_llm = AsyncMock()
    mock_llm.generate.return_value = InferenceResponse(
        content="Hello",
        usage=Usage(input_tokens=100, output_tokens=50, total_tokens=150),
    )

    mock_registry = AsyncMock()
    mock_registry.get_template.return_value = MagicMock(content="You are helpful.")

    mock_session_repo = AsyncMock()
    mock_session_repo.get_messages.return_value = []
    mock_session_repo.add_message.return_value = None

    mock_log_writer = AsyncMock()
    mock_metrics = MagicMock()

    orchestrator = InferenceOrchestrator(
        llm_provider=mock_llm,
        prompt_builder=PromptBuilder(template_registry=mock_registry),
        citation_validator=CitationValidator(),
        session_repo=mock_session_repo,
        log_writer=mock_log_writer,
        metrics_registry=mock_metrics,
    )

    config = TenantConfiguration(tenant_id="t1")

    await orchestrator.generate(
        tenant_id="t1",
        session_id="ses_001",
        query="hi",
        context_chunks=[
            SearchResult(chunk_id="c1", document_id="d1", content="Hello", score=0.9)
        ],
        tenant_config=config,
    )

    assert mock_metrics.increment.call_count >= 3
    # Check that TOKEN_CONSUMPTION was called for input
    input_calls = [
        c for c in mock_metrics.increment.call_args_list
        if c.args[0] == "TOKEN_CONSUMPTION" and c.kwargs.get("labels", {}).get("type") == "input"
    ]
    assert len(input_calls) == 1
    assert input_calls[0].kwargs["value"] == 100

    # Check that COST_SPEND was called
    cost_calls = [
        c for c in mock_metrics.increment.call_args_list
        if c.args[0] == "COST_SPEND"
    ]
    assert len(cost_calls) == 1


# ── Conversation summarization ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_summarize_history_triggers_on_long_conversation() -> None:
    from src.domain.abstractions.config import TenantConfiguration
    from src.domain.inference.citation_validator import CitationValidator
    from src.domain.inference.orchestrator import InferenceOrchestrator
    from src.domain.inference.prompt_builder import PromptBuilder

    mock_llm = AsyncMock()
    mock_llm.generate.return_value = InferenceResponse(
        content="This is a conversation summary.",
        usage=Usage(input_tokens=50, output_tokens=10, total_tokens=60),
    )

    mock_registry = AsyncMock()
    mock_registry.get_template.return_value = MagicMock(content="You are helpful.")

    mock_session_repo = AsyncMock()
    mock_session_repo.add_message.return_value = None

    mock_log_writer = AsyncMock()

    orchestrator = InferenceOrchestrator(
        llm_provider=mock_llm,
        prompt_builder=PromptBuilder(template_registry=mock_registry),
        citation_validator=CitationValidator(),
        session_repo=mock_session_repo,
        log_writer=mock_log_writer,
    )

    # 17 user/assistant pairs = 34 messages (summarize_after_turns=15)
    history = []
    for i in range(17):
        history.append(ChatMessage(role="user", content=f"Question {i}"))
        history.append(ChatMessage(role="assistant", content=f"Answer {i}"))
    mock_session_repo.get_messages.return_value = history

    config = TenantConfiguration(tenant_id="t1")

    await orchestrator.generate(
        tenant_id="t1",
        session_id="ses_001",
        query="What's next?",
        context_chunks=[],
        tenant_config=config,
    )

    # Should have called llm.generate for summarization AND for the main answer
    assert mock_llm.generate.call_count >= 2


@pytest.mark.asyncio
async def test_summarize_history_skips_short_conversation() -> None:
    from src.domain.abstractions.config import TenantConfiguration
    from src.domain.inference.citation_validator import CitationValidator
    from src.domain.inference.orchestrator import InferenceOrchestrator
    from src.domain.inference.prompt_builder import PromptBuilder

    mock_llm = AsyncMock()
    mock_llm.generate.return_value = InferenceResponse(
        content="OK",
        usage=Usage(input_tokens=10, output_tokens=5, total_tokens=15),
    )

    mock_registry = AsyncMock()
    mock_registry.get_template.return_value = MagicMock(content="You are helpful.")

    mock_session_repo = AsyncMock()
    mock_session_repo.get_messages.return_value = [
        ChatMessage(role="user", content="hi"),
        ChatMessage(role="assistant", content="hello"),
    ]
    mock_session_repo.add_message.return_value = None

    mock_log_writer = AsyncMock()

    orchestrator = InferenceOrchestrator(
        llm_provider=mock_llm,
        prompt_builder=PromptBuilder(template_registry=mock_registry),
        citation_validator=CitationValidator(),
        session_repo=mock_session_repo,
        log_writer=mock_log_writer,
    )

    config = TenantConfiguration(tenant_id="t1")

    await orchestrator.generate(
        tenant_id="t1",
        session_id="ses_001",
        query="What's up?",
        context_chunks=[],
        tenant_config=config,
    )

    # Should only have called llm.generate once (main answer, no summarization)
    assert mock_llm.generate.call_count == 1


# ── Anthropic streaming usage ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_anthropic_stream_yields_usage() -> None:
    from src.adapters.cognitive.anthropic_adapter import AnthropicLLMAdapter

    adapter = AnthropicLLMAdapter(api_key="sk-ant-test")
    req = InferenceRequest(messages=[ChatMessage(role="user", content="hi")])
    config = {"model": "claude-3-haiku"}

    async def _mock_stream():
        # Simulate two content blocks followed by message_delta with usage
        ev1 = MagicMock()
        ev1.type = "content_block_delta"
        ev1.delta.text = "Hello"
        yield ev1

        ev2 = MagicMock()
        ev2.type = "message_delta"
        ev2.delta.stop_reason = "end_turn"
        ev2.usage.input_tokens = 10
        ev2.usage.output_tokens = 25
        yield ev2

    mock_client = AsyncMock()
    mock_client.messages.create.return_value = _mock_stream()

    chunks = []
    with patch.object(adapter, "_client_for_key", return_value=mock_client):
        async for chunk in adapter.generate_stream(req, config):
            chunks.append(chunk)

    usage_chunks = [c for c in chunks if "usage" in c]
    assert len(usage_chunks) == 1
    assert usage_chunks[0]["usage"]["input_tokens"] == 10
    assert usage_chunks[0]["usage"]["output_tokens"] == 25

    # finish chunk should also be present
    finish_chunks = [c for c in chunks if c.get("finish_reason") == "end_turn"]
    assert len(finish_chunks) == 1
