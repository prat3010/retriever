"""Pydantic data models for Retriever Python SDK."""

from typing import Any, Literal
from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    chunk_id: str = Field(alias="chunkId")
    document_id: str = Field(default="", alias="documentId")
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    total: int
    latency_ms: float
    strategy_used: str = "hybrid"
    cached: bool = False


class DocumentResponse(BaseModel):
    document_id: str = Field(alias="documentId")
    filename: str
    file_size: int = Field(alias="fileSize")
    mime_type: str = Field(alias="mimeType")
    status: str
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(default="", alias="updatedAt")

    model_config = {"populate_by_name": True}


class ReActEvent(BaseModel):
    type: Literal[
        "thought",
        "tool_call_start",
        "tool_call_done",
        "token",
        "final_answer",
        "error",
    ]
    content: str | None = None
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    result: Any | None = None
    step: int | None = None


class CognitiveMemoryNode(BaseModel):
    memory_id: str
    tenant_id: str
    category: Literal["episodic", "procedural", "factual"]
    content: str
    retention_score: float
    stability: float = 1.0
    created_at: str = ""


class SwarmDebateResult(BaseModel):
    debate_id: str
    consensus_response: str
    quorum_confidence: float
    rounds_evaluated: int
    participating_roles: list[str]
    pruned_hallucinations_count: int = 0
    consensus_reached: bool = True


class McpToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    category: str = "general"


class EnclaveEvidence(BaseModel):
    platform: str
    pcr0: str
    nonce: str
    signature: str
    verified: bool
    attested_at: str = ""


class ConnectorManifestDTO(BaseModel):
    connector_type: str
    name: str
    description: str
    icon: str = "database"
    supports_incremental: bool = False
    required_parameters: list[str] = Field(default_factory=list)
    optional_parameters: dict[str, Any] = Field(default_factory=dict)


class ConnectorConfigDTO(BaseModel):
    id: str
    name: str
    connector_type: str
    status: Literal["idle", "syncing", "failed", "disabled"] = "idle"
    sync_interval_minutes: int = 1440
    configuration: dict[str, Any] = Field(default_factory=dict)
    last_sync_at: str | None = None
    created_at: str = ""
    updated_at: str = ""


class ConnectorSyncResponseDTO(BaseModel):
    connector_id: str = Field(alias="connectorId")
    status: str
    documents_discovered: int = Field(alias="documentsDiscovered")
    documents_ingested: int = Field(alias="documentsIngested")
    duration_ms: float = Field(alias="durationMs")
    message: str

    model_config = {"populate_by_name": True}
