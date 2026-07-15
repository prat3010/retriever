import json as _json
from collections.abc import AsyncIterator
from typing import Any

import anthropic

from src.domain.abstractions.exceptions import ProviderUnavailableError
from src.domain.abstractions.inference import (
    ChatMessage,
    InferenceRequest,
    InferenceResponse,
    LlmProvider,
    Usage,
)


RETRYABLE_ERRORS = (
    anthropic.InternalServerError,
    anthropic.OverloadedError,
    anthropic.APITimeoutError,
    anthropic.APIConnectionError,
    anthropic.RateLimitError,
)


class AnthropicLLMAdapter(LlmProvider):

    def __init__(
        self, api_key: str, default_model: str = "claude-3-5-sonnet-20240620"
    ) -> None:
        self.default_model = default_model
        self._api_key = api_key
        self._client: anthropic.AsyncAnthropic | None = None

    @property
    def client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key or "placeholder-key")
        return self._client

    def _client_for_key(self, api_key: str | None) -> anthropic.AsyncAnthropic:
        if api_key and api_key != self._api_key:
            return anthropic.AsyncAnthropic(api_key=api_key)
        return self.client

    def _compile_messages(self, messages: list[ChatMessage]) -> tuple[str, list[dict[str, Any]]]:
        system_parts = []
        compiled_history = []

        for msg in messages:
            if msg.role == "system":
                system_parts.append(msg.content)
            else:
                role = "assistant" if msg.role == "assistant" else "user"
                if msg.images:
                    content_block: list[dict] = [{"type": "text", "text": msg.content}]
                    for img in msg.images:
                        url = img.get("image_url", {}).get("url", "")
                        if url.startswith("data:image"):
                            media_type = url.split(";")[0].split(":")[1]
                            data = url.split(",")[1]
                            content_block.append({
                                "type": "image",
                                "source": {"type": "base64", "media_type": media_type, "data": data},
                            })
                    compiled_history.append({"role": role, "content": content_block})
                else:
                    compiled_history.append({
                        "role": role,
                        "content": msg.content
                    })

        system_prompt = "\n\n".join(system_parts)
        return system_prompt, compiled_history

    async def generate(
        self, request: InferenceRequest, configuration: dict[str, Any]
    ) -> InferenceResponse:
        model = configuration.get("model", self.default_model)
        client = self._client_for_key(configuration.get("api_key"))
        system_prompt, messages = self._compile_messages(request.messages)

        if request.json_schema:
            schema_hint = f"\n\nReturn valid JSON matching this schema: {_json.dumps(request.json_schema)}"
            if system_prompt:
                system_prompt += schema_hint
            else:
                system_prompt = schema_hint

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens or 4096,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        try:
            response = await client.messages.create(**kwargs, stream=False)
        except RETRYABLE_ERRORS as e:
            raise ProviderUnavailableError(str(e)) from e

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

        try:
            response_stream = await client.messages.create(**kwargs)
        except RETRYABLE_ERRORS as e:
            raise ProviderUnavailableError(str(e)) from e

        async for event in response_stream:
            if event.type == "content_block_delta":
                yield {"delta": event.delta.text, "finish_reason": None}
            elif event.type == "message_delta":
                usage = getattr(event, "usage", None)
                if usage and usage.output_tokens:
                    yield {
                        "usage": {
                            "input_tokens": usage.input_tokens or 0,
                            "output_tokens": usage.output_tokens or 0,
                            "total_tokens": (usage.input_tokens or 0) + usage.output_tokens,
                        }
                    }
                yield {"delta": "", "finish_reason": event.delta.stop_reason}
