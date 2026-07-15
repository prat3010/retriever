"""Anthropic LLM Adapter.

Implements the LlmProvider port using the official Anthropic API for both
synchronous generation and streaming.
"""

from collections.abc import AsyncIterator
from typing import Any

import anthropic

from src.domain.abstractions.inference import (
    ChatMessage,
    InferenceRequest,
    InferenceResponse,
    LlmProvider,
    Usage,
)


class AnthropicLLMAdapter(LlmProvider):
    """Concrete adapter for Anthropic chat completions."""

    def __init__(
        self, api_key: str, default_model: str = "claude-3-5-sonnet-20240620"
    ) -> None:
        self.default_model = default_model
        self._api_key = api_key
        self._client: anthropic.AsyncAnthropic | None = None

    @property
    def client(self) -> anthropic.AsyncAnthropic:
        """Lazy-initialize the Anthropic async client."""
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key or "placeholder-key")
        return self._client

    def _client_for_key(self, api_key: str | None) -> anthropic.AsyncAnthropic:
        """Return client with specific tenant API key if provided."""
        if api_key and api_key != self._api_key:
            return anthropic.AsyncAnthropic(api_key=api_key)
        return self.client

    def _compile_messages(self, messages: list[ChatMessage]) -> tuple[str, list[dict[str, Any]]]:
        """Separate system messages from conversational history.

        Anthropic expects the system prompt as a top-level param, and
        conversational history role values restricted to 'user' and 'assistant'.
        """
        system_parts = []
        compiled_history = []

        for msg in messages:
            if msg.role == "system":
                system_parts.append(msg.content)
            else:
                role = "assistant" if msg.role == "assistant" else "user"
                compiled_history.append({
                    "role": role,
                    "content": msg.content
                })

        system_prompt = "\n\n".join(system_parts)
        return system_prompt, compiled_history

    async def generate(
        self, request: InferenceRequest, configuration: dict[str, Any]
    ) -> InferenceResponse:
        """Execute a synchronous generation."""
        model = configuration.get("model", self.default_model)
        client = self._client_for_key(configuration.get("api_key"))
        system_prompt, messages = self._compile_messages(request.messages)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens or 4096,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = await client.messages.create(**kwargs, stream=False)

        input_tokens = response.usage.input_tokens if response.usage else 0
        output_tokens = response.usage.output_tokens if response.usage else 0

        return InferenceResponse(
            content=response.content[0].text if response.content else "",
            usage=Usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            ),
            finish_reason=response.stop_reason or "stop",
        )

    async def generate_stream(
        self, request: InferenceRequest, configuration: dict[str, Any]
    ) -> AsyncIterator[dict]:
        """Execute a streaming generation yielding delta dicts."""
        model = configuration.get("model", self.default_model)
        client = self._client_for_key(configuration.get("api_key"))
        system_prompt, messages = self._compile_messages(request.messages)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens or 4096,
            "stream": True,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        # Call client and stream events
        response_stream = await client.messages.create(**kwargs)
        async for event in response_stream:
            if event.type == "content_block_delta":
                yield {"delta": event.delta.text, "finish_reason": None}
            elif event.type == "message_delta":
                yield {"delta": "", "finish_reason": event.delta.stop_reason}
