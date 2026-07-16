"""Tests for M19: Smart Model Failover."""

from unittest.mock import AsyncMock, patch

import pytest

from src.domain.abstractions.exceptions import ProviderUnavailableError
from src.domain.abstractions.inference import (
    ChatMessage,
    InferenceRequest,
    InferenceResponse,
    Usage,
)

# --- Step 1: ProviderUnavailableError ---


def test_provider_unavailable_error() -> None:
    err = ProviderUnavailableError("openai timeout")
    assert isinstance(err, ConnectionError)
    assert str(err) == "openai timeout"


# --- Step 2: AIProviderConfig has failover fields ---


def test_ai_provider_config_failover_defaults() -> None:
    from src.domain.abstractions.config import AIProviderConfig

    cfg = AIProviderConfig()
    assert cfg.fallback_provider == ""
    assert cfg.fallback_model == ""
    assert cfg.retry_attempts == 2
    assert cfg.retry_delay_ms == 500


def test_ai_provider_config_failover_custom() -> None:
    from src.domain.abstractions.config import AIProviderConfig

    cfg = AIProviderConfig(
        provider_name="openai",
        fallback_provider="anthropic",
        fallback_model="claude-3-haiku",
        retry_attempts=3,
        retry_delay_ms=1000,
    )
    assert cfg.fallback_provider == "anthropic"
    assert cfg.fallback_model == "claude-3-haiku"
    assert cfg.retry_attempts == 3
    assert cfg.retry_delay_ms == 1000


# --- Step 3: InferenceLog has notes field ---


def test_inference_log_notes() -> None:
    from src.domain.abstractions.inference import InferenceLog

    log = InferenceLog(tenant_id="t1", notes="actual_provider=anthropic")
    assert log.notes == "actual_provider=anthropic"


def test_inference_log_notes_default() -> None:
    from src.domain.abstractions.inference import InferenceLog

    log = InferenceLog(tenant_id="t1")
    assert log.notes is None


# --- Step 4: RoutingLLMProvider failover logic ---


def _make_request() -> InferenceRequest:
    return InferenceRequest(
        messages=[ChatMessage(role="user", content="hello")],
        temperature=0.5,
    )


@pytest.mark.asyncio
async def test_router_calls_primary() -> None:
    from src.adapters.cognitive.routing_provider import RoutingLLMProvider

    primary = AsyncMock()
    primary.generate.return_value = InferenceResponse(content="ok", usage=Usage())

    fallback = AsyncMock()

    router = RoutingLLMProvider(openai_adapter=primary, anthropic_adapter=fallback)
    config = {"provider_name": "openai", "fallback_provider": "anthropic"}

    result = await router.generate(_make_request(), config)

    assert result.content == "ok"
    primary.generate.assert_called_once()
    fallback.generate.assert_not_called()
    assert "_actual_provider" not in config


@pytest.mark.asyncio
async def test_router_fallback_on_provider_unavailable() -> None:
    from src.adapters.cognitive.routing_provider import RoutingLLMProvider

    primary = AsyncMock()
    primary.generate.side_effect = ProviderUnavailableError("timeout")

    fallback = AsyncMock()
    fallback.generate.return_value = InferenceResponse(content="fallback ok", usage=Usage())

    router = RoutingLLMProvider(openai_adapter=primary, anthropic_adapter=fallback)
    config = {"provider_name": "openai", "fallback_provider": "anthropic", "retry_attempts": 0}

    result = await router.generate(_make_request(), config)

    assert result.content == "fallback ok"
    assert config.get("_actual_provider") == "anthropic"


@pytest.mark.asyncio
async def test_router_retries_before_fallback() -> None:
    from src.adapters.cognitive.routing_provider import RoutingLLMProvider

    primary = AsyncMock()
    primary.generate.side_effect = ProviderUnavailableError("timeout")

    fallback = AsyncMock()
    fallback.generate.return_value = InferenceResponse(content="ok", usage=Usage())

    router = RoutingLLMProvider(openai_adapter=primary, anthropic_adapter=fallback)
    config = {"provider_name": "openai", "fallback_provider": "anthropic", "retry_attempts": 2, "retry_delay_ms": 1}

    result = await router.generate(_make_request(), config)

    assert result.content == "ok"
    # primary called 1 + retry_attempts times, then fallback
    assert primary.generate.call_count == 3
    fallback.generate.assert_called_once()


@pytest.mark.asyncio
async def test_router_all_providers_unavailable() -> None:
    from src.adapters.cognitive.routing_provider import RoutingLLMProvider

    primary = AsyncMock()
    primary.generate.side_effect = ProviderUnavailableError("timeout")

    fallback = AsyncMock()
    fallback.generate.side_effect = ProviderUnavailableError("also down")

    router = RoutingLLMProvider(openai_adapter=primary, anthropic_adapter=fallback)
    config = {"provider_name": "openai", "fallback_provider": "anthropic", "retry_attempts": 0, "retry_delay_ms": 1}

    with pytest.raises(ProviderUnavailableError, match="All providers unavailable"):
        await router.generate(_make_request(), config)


@pytest.mark.asyncio
async def test_router_no_fallback_configured_propagates() -> None:
    from src.adapters.cognitive.routing_provider import RoutingLLMProvider

    primary = AsyncMock()
    primary.generate.side_effect = ProviderUnavailableError("timeout")

    router = RoutingLLMProvider(openai_adapter=primary, anthropic_adapter=AsyncMock())
    config = {"provider_name": "openai", "retry_attempts": 0}

    with pytest.raises(ProviderUnavailableError):
        await router.generate(_make_request(), config)


@pytest.mark.asyncio
async def test_router_non_retryable_error_propagates() -> None:
    from src.adapters.cognitive.routing_provider import RoutingLLMProvider

    primary = AsyncMock()
    primary.generate.side_effect = ValueError("bad request")

    router = RoutingLLMProvider(openai_adapter=primary, anthropic_adapter=AsyncMock())
    config = {"provider_name": "openai", "fallback_provider": "anthropic"}

    with pytest.raises(ValueError, match="bad request"):
        await router.generate(_make_request(), config)


# --- Step 5: Streaming failover ---


@pytest.mark.asyncio
async def test_router_stream_fallback() -> None:
    from src.adapters.cognitive.routing_provider import RoutingLLMProvider

    async def _failing_stream(_req, _cfg):
        raise ProviderUnavailableError("timeout")
        yield  # unreachable — makes this an async gen

    primary = AsyncMock()
    primary.generate_stream = _failing_stream

    async def _fallback_stream(_req, _cfg):
        yield {"delta": "hello"}
        yield {"finish_reason": "stop"}

    fallback = AsyncMock()
    fallback.generate_stream = _fallback_stream

    router = RoutingLLMProvider(openai_adapter=primary, anthropic_adapter=fallback)
    config = {"provider_name": "openai", "fallback_provider": "anthropic", "retry_attempts": 0}

    events = [e async for e in router.generate_stream(_make_request(), config)]

    assert events[0]["event"] == "info"
    assert "anthropic" in events[0]["message"]
    assert events[1]["delta"] == "hello"


@pytest.mark.asyncio
async def test_router_stream_all_unavailable() -> None:
    from src.adapters.cognitive.routing_provider import RoutingLLMProvider

    async def _failing_stream(_req, _cfg):
        raise ProviderUnavailableError("timeout")
        yield  # unreachable — makes this an async gen

    primary = AsyncMock()
    primary.generate_stream = _failing_stream

    async def _failing_stream2(_req, _cfg):
        raise ProviderUnavailableError("down")
        yield  # unreachable — makes this an async gen

    fallback = AsyncMock()
    fallback.generate_stream = _failing_stream2

    router = RoutingLLMProvider(openai_adapter=primary, anthropic_adapter=fallback)
    config = {"provider_name": "openai", "fallback_provider": "anthropic", "retry_attempts": 0}

    with pytest.raises(ProviderUnavailableError):
        async for _ in router.generate_stream(_make_request(), config):
            pass


# --- Step 6: Adapter error wrapping ---


@pytest.mark.asyncio
async def test_openai_adapter_wraps_retryable_error() -> None:
    import openai

    from src.adapters.cognitive.openai_adapter import OpenAILLMAdapter

    adapter = OpenAILLMAdapter(api_key="sk-test")
    req = _make_request()
    config = {"model": "gpt-4"}

    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = openai.APITimeoutError("connection reset")

    with patch.object(adapter, "_client_for_key", return_value=mock_client):
        with pytest.raises(ProviderUnavailableError):
            await adapter.generate(req, config)


@pytest.mark.asyncio
async def test_openai_adapter_lets_auth_error_propagate() -> None:
    from src.adapters.cognitive.openai_adapter import OpenAILLMAdapter

    adapter = OpenAILLMAdapter(api_key="sk-test")
    req = _make_request()
    config = {"model": "gpt-4"}

    mock_client = AsyncMock()
    from openai import AuthenticationError
    mock_client.chat.completions.create.side_effect = AuthenticationError(
        "invalid key", response=AsyncMock(), body=None
    )

    with patch.object(adapter, "_client_for_key", return_value=mock_client):
        with pytest.raises(AuthenticationError):
            await adapter.generate(req, config)


@pytest.mark.asyncio
async def test_anthropic_adapter_wraps_retryable_error() -> None:
    import anthropic
    import httpx

    from src.adapters.cognitive.anthropic_adapter import AnthropicLLMAdapter

    adapter = AnthropicLLMAdapter(api_key="sk-ant-test")
    req = _make_request()
    config = {"model": "claude-3-haiku"}

    mock_client = AsyncMock()
    mock_client.messages.create.side_effect = anthropic.APITimeoutError(
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    )

    with patch.object(adapter, "_client_for_key", return_value=mock_client):
        with pytest.raises(ProviderUnavailableError):
            await adapter.generate(req, config)
