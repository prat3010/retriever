import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from src.adapters.cognitive.anthropic_adapter import AnthropicLLMAdapter
from src.adapters.cognitive.openai_adapter import OpenAILLMAdapter
from src.domain.abstractions.exceptions import ProviderUnavailableError
from src.domain.abstractions.inference import (
    InferenceRequest,
    InferenceResponse,
    LlmProvider,
)

logger = logging.getLogger("api")


class RoutingLLMProvider(LlmProvider):

    def __init__(
        self, openai_adapter: OpenAILLMAdapter, anthropic_adapter: AnthropicLLMAdapter
    ) -> None:
        self.openai_adapter = openai_adapter
        self.anthropic_adapter = anthropic_adapter

    def _get_provider(self, provider_name: str) -> LlmProvider:
        if provider_name == "anthropic":
            return self.anthropic_adapter
        return self.openai_adapter

    async def generate(
        self, request: InferenceRequest, configuration: dict[str, Any]
    ) -> InferenceResponse:
        config = configuration or {}
        primary = config.get("provider_name", "openai")
        fallback = config.get("fallback_provider", "")
        retries = config.get("retry_attempts", 0)
        delay = config.get("retry_delay_ms", 500)

        providers_to_try = [primary]
        if fallback and fallback != primary:
            providers_to_try.append(fallback)

        attempted = []
        for provider_name in providers_to_try:
            for attempt in range(1 + retries):
                provider = self._get_provider(provider_name)
                attempted.append(provider_name)
                try:
                    response = await provider.generate(request, configuration)
                    if len(attempted) > 1:
                        config["_actual_provider"] = provider_name
                    return response
                except ProviderUnavailableError:
                    if attempt < retries:
                        sleep_sec = (2 ** attempt) * delay / 1000
                        await asyncio.sleep(sleep_sec)
                        continue
                    break
            if provider_name != providers_to_try[-1]:
                config.pop("api_key", None)

        raise ProviderUnavailableError(
            f"All providers unavailable. Tried: {' -> '.join(attempted)} "
            f"(retries={retries}, delay={delay}ms)"
        )

    async def generate_stream(
        self, request: InferenceRequest, configuration: dict[str, Any]
    ) -> AsyncIterator[dict]:
        config = configuration or {}
        primary = config.get("provider_name", "openai")
        fallback = config.get("fallback_provider", "")
        retries = config.get("retry_attempts", 0)
        delay = config.get("retry_delay_ms", 500)

        providers_to_try = [primary]
        if fallback and fallback != primary:
            providers_to_try.append(fallback)

        attempted = []
        for provider_name in providers_to_try:
            provider = self._get_provider(provider_name)
            attempted.append(provider_name)
            try:
                if len(attempted) > 1:
                    config["_actual_provider"] = provider_name
                    yield {"event": "info", "message": f"Failing over to {provider_name}"}
                async for chunk in provider.generate_stream(request, configuration):
                    yield chunk
                return
            except ProviderUnavailableError:
                if provider_name == providers_to_try[-1]:
                    raise
                sleep_sec = (2 ** (retries or 1)) * delay / 1000
                await asyncio.sleep(sleep_sec)
                continue

        raise ProviderUnavailableError(
            f"All providers unavailable for streaming. Tried: {' -> '.join(attempted)}"
        )
