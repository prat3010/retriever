"""Stub Embedding Adapter.

Placeholder implementation of the EmbeddingProvider port returning zero vectors.
Will be replaced with a real OpenAI/HuggingFace adapter in Milestone 6.
"""

from src.domain.abstractions.retrieval import EmbeddingProvider


EMBEDDING_DIMENSION = 1536


class StubEmbeddingAdapter(EmbeddingProvider):
    """Stub adapter returning zero-valued embedding vectors for testing."""

    async def embed_text(self, text: str) -> list[float]:
        """Return a zero vector of the configured embedding dimension."""
        return [0.0] * EMBEDDING_DIMENSION

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return zero vectors for each input text."""
        return [[0.0] * EMBEDDING_DIMENSION for _ in texts]
