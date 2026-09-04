from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    documentId: str
    collectionId: str | None = None
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


class RawDocumentRequest(BaseModel):
    title: str = Field(..., description="Document title or web page title")
    content: str = Field(..., description="Raw text or markdown content extracted")
    source_url: str | None = Field(None, description="Origin URL or file path")
    mime_type: str = Field("text/markdown", description="Content MIME type")
    tags: list[str] = Field(default_factory=lambda: ["raw_ingest"])


class RawDocumentResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int
    status: str
    message: str
