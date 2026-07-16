"""Anthropic Adapter & Routing LLM Provider Tests.

Verifies:
- AnthropicLLMAdapter compiles system messages separately from conversational history.
- generate returns mapped responses and token usage counters.
- generate_stream yields streamed token delta responses.
- RoutingLLMProvider routes requests to selected provider based on config.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.cognitive.anthropic_adapter import AnthropicLLMAdapter
from src.adapters.cognitive.openai_adapter import OpenAILLMAdapter
from src.adapters.cognitive.routing_provider import RoutingLLMProvider
from src.domain.abstractions.inference import ChatMessage, InferenceRequest


def test_anthropic_adapter_message_compilation() -> None:
    """Verify system messages are extracted from messages list."""
    adapter = AnthropicLLMAdapter(api_key="test-key")
    messages = [
        ChatMessage(role="system", content="System instruction 1"),
        ChatMessage(role="user", content="Hello case"),
        ChatMessage(role="system", content="System instruction 2"),
        ChatMessage(role="assistant", content="Hi user"),
    ]

    system, history = adapter._compile_messages(messages)
    assert system == "System instruction 1\n\nSystem instruction 2"
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Hello case"}
    assert history[1] == {"role": "assistant", "content": "Hi user"}


@pytest.mark.asyncio
async def test_anthropic_generate_response() -> None:
    """Verify generate handles synchronous response and token counts."""
    adapter = AnthropicLLMAdapter(api_key="test-key")
    adapter._client = MagicMock()
    
    mock_msg_response = MagicMock()
    mock_msg_response.content = [MagicMock(text="Claude answer")]
    mock_msg_response.usage = MagicMock(input_tokens=10, output_tokens=20)
    mock_msg_response.stop_reason = "end_turn"
    
    adapter._client.messages.create = AsyncMock(return_value=mock_msg_response)

    request = InferenceRequest(
        messages=[
            ChatMessage(role="system", content="sys"),
            ChatMessage(role="user", content="hello"),
        ],
        temperature=0.5,
    )

    response = await adapter.generate(request, {"model": "claude-3-5-sonnet", "api_key": "test-key"})
    
    assert response.content == "Claude answer"
    assert response.usage.input_tokens == 10
    assert response.usage.output_tokens == 20
    assert response.usage.total_tokens == 30
    assert response.finish_reason == "end_turn"
    
    # Assert client call params
    adapter._client.messages.create.assert_called_once_with(
        model="claude-3-5-sonnet",
        messages=[{"role": "user", "content": "hello"}],
        temperature=0.5,
        max_tokens=4096,
        system="sys",
        stream=False,
    )


@pytest.mark.asyncio
async def test_anthropic_generate_stream() -> None:
    """Verify generate_stream yields token chunks."""
    adapter = AnthropicLLMAdapter(api_key="test-key")
    adapter._client = MagicMock()

    class MockEvent:
        def __init__(self, event_type, text=None, stop_reason=None):
            self.type = event_type
            if text:
                self.delta = MagicMock()
                self.delta.text = text
            if stop_reason:
                self.delta = MagicMock()
                self.delta.stop_reason = stop_reason

    mock_stream = AsyncMock()
    mock_stream.__aiter__.return_value = [
        MockEvent("content_block_delta", text="Hello"),
        MockEvent("content_block_delta", text=" World"),
        MockEvent("message_delta", stop_reason="end_turn"),
    ]
    adapter._client.messages.create = AsyncMock(return_value=mock_stream)

    request = InferenceRequest(messages=[ChatMessage(role="user", content="hello")])
    chunks = []
    async for chunk in adapter.generate_stream(request, {"model": "claude"}):
        chunks.append(chunk)

    assert len(chunks) == 3
    assert chunks[0] == {"delta": "Hello", "finish_reason": None}
    assert chunks[1] == {"delta": " World", "finish_reason": None}
    assert chunks[2] == {"delta": "", "finish_reason": "end_turn"}


@pytest.mark.asyncio
async def test_routing_provider_delegation() -> None:
    """Verify RoutingLLMProvider routes call to the configured adapter."""
    mock_openai = AsyncMock(spec=OpenAILLMAdapter)
    mock_anthropic = AsyncMock(spec=AnthropicLLMAdapter)
    
    router = RoutingLLMProvider(openai_adapter=mock_openai, anthropic_adapter=mock_anthropic)
    request = InferenceRequest(messages=[])

    # Route to OpenAI
    await router.generate(request, {"provider_name": "openai"})
    mock_openai.generate.assert_called_once()
    mock_anthropic.generate.assert_not_called()

    mock_openai.generate.reset_mock()
    mock_anthropic.generate.reset_mock()

    # Route to Anthropic
    await router.generate(request, {"provider_name": "anthropic"})
    mock_anthropic.generate.assert_called_once()
    mock_openai.generate.assert_not_called()
