from pydantic import BaseModel, Field

from src.domain.abstractions.retrieval import MetadataFilter


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=100)
    filters: list[MetadataFilter] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


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
