"""OpenAI Embedding Adapter.

Implements the EmbeddingProvider port using OpenAI's embedding API with
configurable model, exponential backoff with jitter, and request timeout.
"""

import asyncio
import random
from typing import Optional

import openai

from src.domain.abstractions.retrieval import EmbeddingProvider


DEFAULT_MODEL = "text-embedding-3-small"
DEFAULT_DIMENSION = 1536


class OpenAIEmbeddingAdapter(EmbeddingProvider):
    """OpenAI-backed embedding adapter.

    Args:
        api_key: OpenAI API key.  Falls back to ``OPENAI_API_KEY`` env var.
        model: Embedding model to use (default: ``text-embedding-3-small``).
        base_url: Optional custom API base URL.
        dimension: Expected embedding dimension (default: 1536).
    """

    def __init__(
        self,
        api_key: str = "",
        model: str = DEFAULT_MODEL,
        base_url: str = "",
        dimension: int = DEFAULT_DIMENSION,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._dimension = dimension
        self._client: Optional[openai.AsyncOpenAI] = None

    @property
    def client(self) -> openai.AsyncOpenAI:
        if self._client is None:
            kwargs = {"api_key": self._api_key or "sk-placeholder"}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = openai.AsyncOpenAI(**kwargs)
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        embedding = await self._embed_with_retry(self.client, [text], self._model)
        return embedding[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return await self._embed_with_retry(self.client, texts, self._model)

    @staticmethod
    async def _embed_with_retry(
        client: openai.AsyncOpenAI,
        texts: list[str],
        model: str,
        max_retries: int = 5,
    ) -> list[list[float]]:
        """Call OpenAI embedding API with exponential backoff and jitter."""
        for attempt in range(max_retries + 1):
            try:
                response = await client.embeddings.create(
                    input=texts,
                    model=model,
                    timeout=30,
                )
                sorted_data = sorted(response.data, key=lambda x: x.index)
                return [item.embedding for item in sorted_data]
            except (openai.APIError, openai.APITimeoutError, openai.RateLimitError) as e:
                if attempt == max_retries:
                    raise
                sleep_seconds = (2 ** attempt) + random.uniform(0, 1)
                await asyncio.sleep(sleep_seconds)
