"""Retrieval Domain Abstractions (Ports).

Defines pure domain entities and abstract interfaces for the hybrid search,
embedding, and reranking subsystems. Contains zero infrastructure imports.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """Inbound search request domain entity."""

    query: str
    tenant_id: str
    top_k: int = 10
    filters: dict[str, Any] = Field(default_factory=dict)
    enable_hybrid: bool = True
    enable_reranking: bool = True
    rrf_k: int = 60
    reranking_threshold: float = 0.7


class SearchResult(BaseModel):
    """Individual search hit returned from retrieval pipelines."""

    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchMeta(BaseModel):
    """Operational metadata describing the search execution."""

    strategy: str
    total_candidates: int
    returned_results: int
    duration_ms: float


class SearchResponse(BaseModel):
    """Complete search response wrapping results and metadata."""

    query: str
    results: list[SearchResult]
    search_meta: SearchMeta


class VectorSearchProvider(ABC):
    """Port for dense vector similarity search backends."""

    @abstractmethod
    async def search_similar(
        self,
        tenant_id: str,
        embedding: list[float],
        top_k: int,
        filters: dict[str, Any],
    ) -> list[SearchResult]:
        """Execute cosine similarity search against vector indexes."""
        pass


class KeywordSearchProvider(ABC):
    """Port for sparse keyword (BM25/tsvector) search backends."""

    @abstractmethod
    async def search_keywords(
        self,
        tenant_id: str,
        query_text: str,
        top_k: int,
        filters: dict[str, Any],
    ) -> list[SearchResult]:
        """Execute keyword-based full-text search."""
        pass


class EmbeddingProvider(ABC):
    """Port for text-to-vector embedding generation."""

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding vector for a single text input."""
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a batch of text inputs."""
        pass


class RerankerProvider(ABC):
    """Port for cross-encoder reranking of search candidates."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        top_n: int,
        threshold: float,
    ) -> list[SearchResult]:
        """Re-score and filter candidates using a cross-encoder model."""
        pass
