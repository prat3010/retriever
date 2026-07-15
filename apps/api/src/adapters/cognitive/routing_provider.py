"""Routing LLM Provider Adapter.

Acts as a composite / router delegating requests to either the OpenAI or
Anthropic adapters based on dynamic tenant configurations.
"""

from collections.abc import AsyncIterator
from typing import Any

from src.domain.abstractions.inference import (
    InferenceRequest,
    InferenceResponse,
    LlmProvider,
)
from src.adapters.cognitive.openai_adapter import OpenAILLMAdapter
from src.adapters.cognitive.anthropic_adapter import AnthropicLLMAdapter


class RoutingLLMProvider(LlmProvider):
    """Router delegating generate calls to configured backend provider adapters."""

    def __init__(
        self, openai_adapter: OpenAILLMAdapter, anthropic_adapter: AnthropicLLMAdapter
    ) -> None:
        self.openai_adapter = openai_adapter
        self.anthropic_adapter = anthropic_adapter

    def _get_provider(self, configuration: dict[str, Any]) -> LlmProvider:
        """Inspect config dictionary and return appropriate provider adapter."""
        provider_name = configuration.get("provider_name", "openai")
        if provider_name == "anthropic":
            return self.anthropic_adapter
        return self.openai_adapter

    async def generate(
        self, request: InferenceRequest, configuration: dict[str, Any]
    ) -> InferenceResponse:
        """Route non-streaming execution to selected provider."""
        provider = self._get_provider(configuration)
        return await provider.generate(request, configuration)

    async def generate_stream(
        self, request: InferenceRequest, configuration: dict[str, Any]
    ) -> AsyncIterator[dict]:
        """Route streaming execution to selected provider."""
        provider = self._get_provider(configuration)
        async for chunk in provider.generate_stream(request, configuration):
            yield chunk
