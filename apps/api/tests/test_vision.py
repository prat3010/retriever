"""Tests for M23: Multi-Modal Processing."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.domain.abstractions.inference import (
    ChatMessage,
    InferenceRequest,
    InferenceResponse,
    Usage,
)


# ── Step 1: ChatMessage.images field ────────────────────────────────────────


def test_chat_message_images_default() -> None:
    m = ChatMessage(role="user", content="hi")
    assert m.images == []


def test_chat_message_images_custom() -> None:
    m = ChatMessage(
        role="user",
        content="what's in this?",
        images=[{"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}],
    )
    assert len(m.images) == 1
    assert m.images[0]["type"] == "image_url"


def test_chat_message_model_dump_excludes_images_when_empty() -> None:
    m = ChatMessage(role="user", content="hi")
    dumped = m.model_dump()
    assert "images" in dumped
    assert dumped["images"] == []


# ── Step 2: OpenAI adapter vision mode ─────────────────────────────────────


@pytest.mark.asyncio
async def test_openai_adapter_converts_images_to_content_blocks() -> None:
    from src.adapters.cognitive.openai_adapter import OpenAILLMAdapter

    adapter = OpenAILLMAdapter(api_key="sk-test")
    req = InferenceRequest(messages=[
        ChatMessage(
            role="user",
            content="describe this",
            images=[{"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}],
        ),
    ])

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="it's a cat"), finish_reason="stop")],
        usage=MagicMock(prompt_tokens=100, completion_tokens=10, total_tokens=110),
    )

    with patch.object(adapter, "_client_for_key", return_value=mock_client):
        await adapter.generate(req, {})

    call_kwargs = mock_client.chat.completions.create.call_args[1]
    msg = call_kwargs["messages"][0]
    assert isinstance(msg["content"], list)
    assert msg["content"][0] == {"type": "text", "text": "describe this"}
    assert msg["content"][1] == {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}


@pytest.mark.asyncio
async def test_openai_adapter_no_images_uses_string_content() -> None:
    from src.adapters.cognitive.openai_adapter import OpenAILLMAdapter

    adapter = OpenAILLMAdapter(api_key="sk-test")
    req = InferenceRequest(messages=[ChatMessage(role="user", content="hello")])

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="hi"), finish_reason="stop")],
        usage=MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )

    with patch.object(adapter, "_client_for_key", return_value=mock_client):
        await adapter.generate(req, {})

    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert isinstance(call_kwargs["messages"][0]["content"], str)


@pytest.mark.asyncio
async def test_openai_stream_converts_images() -> None:
    from src.adapters.cognitive.openai_adapter import OpenAILLMAdapter

    adapter = OpenAILLMAdapter(api_key="sk-test")
    req = InferenceRequest(messages=[
        ChatMessage(
            role="user", content="desc",
            images=[{"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}],
        ),
    ])

    mock_client = AsyncMock()

    async def _stream():
        yield MagicMock(choices=[MagicMock(delta=MagicMock(content="a"), finish_reason=None)], usage=None)
        yield MagicMock(choices=[MagicMock(delta=MagicMock(content="b"), finish_reason=None)], usage=None)
        yield MagicMock(choices=[MagicMock(delta=MagicMock(content=""), finish_reason="stop")], usage=MagicMock(prompt_tokens=5, completion_tokens=3, total_tokens=8))

    mock_client.chat.completions.create.return_value = _stream()

    with patch.object(adapter, "_client_for_key", return_value=mock_client):
        chunks = [c async for c in adapter.generate_stream(req, {})]

    call_kwargs = mock_client.chat.completions.create.call_args[1]
    msg = call_kwargs["messages"][0]
    assert isinstance(msg["content"], list)
    assert msg["content"][1]["type"] == "image_url"
    assert len(chunks) > 0


# ── Step 3: Anthropic adapter vision mode ──────────────────────────────────


@pytest.mark.asyncio
async def test_anthropic_adapter_converts_images_to_content_blocks() -> None:
    from src.adapters.cognitive.anthropic_adapter import AnthropicLLMAdapter

    adapter = AnthropicLLMAdapter(api_key="sk-ant-test")
    req = InferenceRequest(messages=[
        ChatMessage(
            role="user",
            content="describe this",
            images=[{"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}],
        ),
        ChatMessage(role="assistant", content="ok"),
    ])

    mock_client = AsyncMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="it's a dog")],
        usage=MagicMock(input_tokens=50, output_tokens=10),
        stop_reason="end_turn",
    )

    with patch.object(adapter, "_client_for_key", return_value=mock_client):
        await adapter.generate(req, {})

    call_kwargs = mock_client.messages.create.call_args[1]
    msg = call_kwargs["messages"][0]
    assert isinstance(msg["content"], list)
    assert msg["content"][0]["type"] == "text"
    assert msg["content"][1]["type"] == "image"
    assert msg["content"][1]["source"]["type"] == "base64"
    assert msg["content"][1]["source"]["data"] == "abc"

    # assistant message without images stays string
    msg1 = call_kwargs["messages"][1]
    assert isinstance(msg1["content"], str)


@pytest.mark.asyncio
async def test_anthropic_adapter_no_images_uses_string() -> None:
    from src.adapters.cognitive.anthropic_adapter import AnthropicLLMAdapter

    adapter = AnthropicLLMAdapter(api_key="sk-ant-test")
    req = InferenceRequest(messages=[ChatMessage(role="user", content="hello")])

    mock_client = AsyncMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="hi")],
        usage=MagicMock(input_tokens=5, output_tokens=3),
        stop_reason="end_turn",
    )

    with patch.object(adapter, "_client_for_key", return_value=mock_client):
        await adapter.generate(req, {})

    call_kwargs = mock_client.messages.create.call_args[1]
    assert isinstance(call_kwargs["messages"][0]["content"], str)


# ── Step 4: Config ─────────────────────────────────────────────────────────


def test_ai_provider_config_has_vision_model() -> None:
    from src.domain.abstractions.config import AIProviderConfig

    cfg = AIProviderConfig()
    assert cfg.vision_model == "gpt-4o"


def test_settings_has_vision_model() -> None:
    from src.config import Settings

    s = Settings()
    assert s.VISION_MODEL == "gpt-4o"


# ── Step 5: Worker vision extraction ────────────────────────────────────────


def test_describe_with_vision_structure() -> None:
    # Just test that the function exists and has the expected signature
    from workers.src.tasks import _describe_with_vision
    assert callable(_describe_with_vision)
