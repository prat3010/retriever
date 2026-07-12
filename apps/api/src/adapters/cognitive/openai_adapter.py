"""OpenAI LLM Adapter.

Implements the LlmProvider port using the OpenAI API for both
synchronous generation and SSE-compatible streaming.
"""

from typing import Any, AsyncIterator
from openai import AsyncOpenAI

from src.domain.abstractions.inference import (
    LlmProvider,
    InferenceRequest,
    InferenceResponse,
    Usage,
)


class OpenAILLMAdapter(LlmProvider):
    """Concrete adapter for OpenAI / OpenAI-compatible chat completions."""

    def __init__(
        self, api_key: str, base_url: str = "", default_model: str = "gpt-4o"
    ) -> None:
        self.default_model = default_model
        self._api_key = api_key
        self._base_url = base_url
        self._async_client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        """Lazy-initialize the OpenAI async client."""
        if self._async_client is None:
            kwargs: dict[str, Any] = {"api_key": self._api_key}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._async_client = AsyncOpenAI(**kwargs)
        return self._async_client

    async def generate(
        self, request: InferenceRequest, configuration: dict[str, Any]
    ) -> InferenceResponse:
        """Execute a synchronous non-streaming generation."""
        model = configuration.get("model", self.default_model)
        messages = [m.model_dump() for m in request.messages]

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
        }
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens

        response = await self.client.chat.completions.create(
            **kwargs, stream=False
        )

        choice = response.choices[0]
        return InferenceResponse(
            content=choice.message.content or "",
            usage=Usage(
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
            ),
            finish_reason=choice.finish_reason or "stop",
        )

    async def generate_stream(
        self, request: InferenceRequest, configuration: dict[str, Any]
    ) -> AsyncIterator[dict]:
        """Execute a streaming generation yielding delta dicts."""
        model = configuration.get("model", self.default_model)
        messages = [m.model_dump() for m in request.messages]

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens

        stream = await self.client.chat.completions.create(**kwargs)

        async for chunk in stream:
            choice = chunk.choices[0] if chunk.choices else None
            if choice and choice.delta and choice.delta.content:
                yield {"delta": choice.delta.content}
            if choice and choice.finish_reason:
                yield {"finish_reason": choice.finish_reason}
                break

        yield {"finish_reason": "stop"}
