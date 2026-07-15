from collections.abc import AsyncIterator
from typing import Any

import openai

from src.domain.abstractions.exceptions import ProviderUnavailableError
from src.domain.abstractions.inference import (
    InferenceRequest,
    InferenceResponse,
    LlmProvider,
    Usage,
)


RETRYABLE_ERRORS = (
    openai.InternalServerError,
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.RateLimitError,
)


class OpenAILLMAdapter(LlmProvider):

    def __init__(
        self, api_key: str, base_url: str = "", default_model: str = "gemini-1.5-flash"
    ) -> None:
        self.default_model = default_model
        self._api_key = api_key
        self._base_url = base_url
        self._async_client: openai.AsyncOpenAI | None = None

    @property
    def client(self) -> openai.AsyncOpenAI:
        if self._async_client is None:
            kwargs: dict[str, Any] = {"api_key": self._api_key}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._async_client = openai.AsyncOpenAI(**kwargs)
        return self._async_client

    def _client_for_key(self, api_key: str | None) -> openai.AsyncOpenAI:
        if api_key and api_key != self._api_key:
            kwargs: dict[str, Any] = {"api_key": api_key}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            return openai.AsyncOpenAI(**kwargs)
        return self.client

    async def generate(
        self, request: InferenceRequest, configuration: dict[str, Any]
    ) -> InferenceResponse:
        model = configuration.get("model", self.default_model)
        messages = [m.model_dump() for m in request.messages]
        for msg in messages:
            images = msg.pop("images", None)
            if images:
                content_block: list[dict] = [{"type": "text", "text": msg["content"]}]
                content_block.extend(images)
                msg["content"] = content_block
        client = self._client_for_key(configuration.get("api_key"))

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
        }
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens
        if request.json_schema:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await client.chat.completions.create(**kwargs, stream=False)
        except RETRYABLE_ERRORS as e:
            raise ProviderUnavailableError(str(e)) from e

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
        model = configuration.get("model", self.default_model)
        messages = [m.model_dump() for m in request.messages]
        for msg in messages:
            images = msg.pop("images", None)
            if images:
                content_block: list[dict] = [{"type": "text", "text": msg["content"]}]
                content_block.extend(images)
                msg["content"] = content_block
        client = self._client_for_key(configuration.get("api_key"))

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens

        try:
            stream = await client.chat.completions.create(**kwargs)
        except RETRYABLE_ERRORS as e:
            raise ProviderUnavailableError(str(e)) from e

        async for chunk in stream:
            choice = chunk.choices[0] if chunk.choices else None
            if choice and choice.delta and choice.delta.content:
                yield {"delta": choice.delta.content}
            if choice and choice.finish_reason:
                yield {"delta": "", "finish_reason": choice.finish_reason}
            if chunk.usage:
                yield {
                    "usage": {
                        "input_tokens": chunk.usage.prompt_tokens or 0,
                        "output_tokens": chunk.usage.completion_tokens or 0,
                        "total_tokens": chunk.usage.total_tokens or 0,
                    }
                }
