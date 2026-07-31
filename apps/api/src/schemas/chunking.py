from typing import Any, Literal

from pydantic import BaseModel, Field


class ChunkPreviewRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100000, description="Raw text string to audit for chunking splits.")
    chunk_size: int = Field(default=512, ge=16, le=4096, description="Target chunk token/character size.")
    chunk_overlap: int = Field(default=64, ge=0, le=1024, description="Overlap size between consecutive chunks.")
    strategy: Literal["sliding", "semantic", "hierarchical"] = Field(
        default="sliding", description="Chunking strategy algorithm."
    )


class ChunkPreviewItem(BaseModel):
    chunkIndex: int
    content: str
    tokenCount: int
    charCount: int
    startCharIdx: int
    endCharIdx: int
    metaData: dict[str, Any] = Field(default_factory=dict)


class ChunkPreviewResponse(BaseModel):
    totalChunks: int
    totalTokens: int
    totalChars: int
    avgChunkTokens: float
    chunks: list[ChunkPreviewItem]
