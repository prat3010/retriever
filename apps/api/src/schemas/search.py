from pydantic import BaseModel, Field

from src.domain.abstractions.retrieval import MetadataFilter


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=100)
    collection_id: str | None = Field(None, alias="collectionId")
    filters: list[MetadataFilter] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    hybrid_alpha: float | None = Field(default=0.7, alias="hybridAlpha", ge=0.0, le=1.0)
    enable_lora_adapter: bool | None = Field(default=False, alias="enableLoraAdapter")
    reranker_engine: str | None = Field(default=None, alias="rerankerEngine")
    enable_colbert_rerank: bool | None = Field(default=False, alias="enableColbertRerank")


class SearchResultItem(BaseModel):
    chunkId: str
    documentId: str
    content: str
    score: float
    metadata: dict[str, object] = Field(default_factory=dict)


class SearchMetaResponse(BaseModel):
    strategy: str
    totalCandidates: int
    returnedResults: int
    durationMs: float


class SearchResponseDto(BaseModel):
    query: str
    results: list[SearchResultItem]
    searchMeta: SearchMetaResponse
