from pydantic import BaseModel, Field

from src.domain.abstractions.retrieval import MetadataFilter


class CreateSessionResponse(BaseModel):
    sessionId: str
    createdAt: str


class ChatMessageRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    stream: bool = True
    system_prompt_name: str = "default"
    filters: list[MetadataFilter] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class FeedbackSubmitRequest(BaseModel):
    rating: int = Field(default=0, description="Rating score, +1 for positive, -1 for negative.")
    feedback_text: str | None = Field(None, description="Optional text comment.")
    scores: dict[str, int] | None = Field(None, description="Per-dimension scores, e.g. helpfulness=5, accuracy=4.")
