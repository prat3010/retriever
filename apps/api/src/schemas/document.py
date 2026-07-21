from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    documentId: str
    filename: str
    fileSize: int
    mimeType: str
    status: str
    createdAt: str
    updatedAt: str


class ExtractRequest(BaseModel):
    json_schema: dict[str, object] = Field(..., description="JSON Schema to shape the extraction output")
    model: str | None = None


class ExtractResponse(BaseModel):
    data: dict[str, object]
    provider: str
    model: str
    inputTokens: int
    outputTokens: int
