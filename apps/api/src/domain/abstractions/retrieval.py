from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, Field

Operator = Literal[
    "eq", "neq", "in", "gt", "gte", "lt", "lte",
    "exists", "contains", "regex",
]


class MetadataFilter(BaseModel):
    field: str
    operator: Operator
    value: Any = None


class SearchQuery(BaseModel):
    query: str
    tenant_id: str
    top_k: int = 10
    filters: list[MetadataFilter] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    enable_hybrid: bool = True
    enable_reranking: bool = True
    enable_self_query: bool = False
    enable_bm25: bool = False
    enable_mmr: bool = False
    enable_query_rewriting: bool = False
    enable_query_intent: bool = False
    rrf_k: int = 60
    reranking_threshold: float = 0.7
    rerank_candidate_multiplier: int = 5
    enable_web_search: bool = False
    web_search_provider: str = "tavily"
    web_search_api_key: str | None = None
    web_search_threshold: float = 0.65
    web_search_max_results: int = 5


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchMeta(BaseModel):
    strategy: str
    total_candidates: int
    returned_results: int
    duration_ms: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    search_meta: SearchMeta


class VectorSearchProvider(ABC):

    @abstractmethod
    async def search_similar(
        self,
        tenant_id: str,
        embedding: list[float],
        top_k: int,
        filters: list[MetadataFilter],
        tags: list[str],
    ) -> list[SearchResult]:
        pass


class KeywordSearchProvider(ABC):

    @abstractmethod
    async def search_keywords(
        self,
        tenant_id: str,
        query_text: str,
        top_k: int,
        filters: list[MetadataFilter],
        tags: list[str],
    ) -> list[SearchResult]:
        pass


class EmbeddingProvider(ABC):

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        pass


class RerankerProvider(ABC):

    @abstractmethod
    async def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        top_n: int,
        threshold: float,
    ) -> list[SearchResult]:
        pass


class SemanticCacheProvider(ABC):

    @abstractmethod
    async def get_cached_search(
        self,
        tenant_id: str,
        query_embedding: list[float],
    ) -> list[SearchResult] | None:
        pass

    @abstractmethod
    async def cache_search(
        self,
        tenant_id: str,
        query_text: str,
        query_embedding: list[float],
        results: list[SearchResult],
    ) -> None:
        pass


class SelfQueryProvider(ABC):

    @abstractmethod
    async def parse_query(self, query: str) -> list[MetadataFilter]:
        pass


class QueryRewriterProvider(ABC):

    @abstractmethod
    async def rewrite(self, query: str) -> list[str]:
        pass


class CorrectiveRetrievalDecision(BaseModel):
    needs_re_retrieval: bool = False
    confidence_score: float = 0.0
    reason: str = ""
    reformulated_query: str | None = None


class CorrectiveRetrievalProvider(ABC):

    @abstractmethod
    async def evaluate_response(
        self,
        query: str,
        response: str,
        context_chunks: list[SearchResult],
    ) -> CorrectiveRetrievalDecision:
        pass


class QueryIntent(BaseModel):
    top_k: int = 10
    enable_hybrid: bool = True
    enable_reranking: bool = True
    enable_web_search: bool = False


class QueryIntentClassifier(ABC):

    @abstractmethod
    async def classify(self, query: str) -> QueryIntent:
        pass
