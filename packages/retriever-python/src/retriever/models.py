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


# ── Multimodal Vision GraphRAG (Battery #29) ─────────────────────────────────

class VisionBoundingBoxDTO(BaseModel):
    ymin: float
    xmin: float
    ymax: float
    xmax: float
    confidence: float = 1.0


class VisualElementDTO(BaseModel):
    element_id: str
    label: str
    element_type: str = "unknown"
    bounding_box: VisionBoundingBoxDTO
    confidence: float = 1.0
    properties: dict[str, Any] = Field(default_factory=dict)


class VisualConnectorDTO(BaseModel):
    connector_id: str
    source_element_id: str
    target_element_id: str
    label: str = ""
    directionality: str = "directed"
    protocol: str | None = None
    confidence: float = 1.0


class SchematicDiagramDTO(BaseModel):
    diagram_id: str
    filename: str
    document_id: str | None = None
    page_number: int = 1
    width: float = 1920.0
    height: float = 1080.0
    elements: list[VisualElementDTO] = Field(default_factory=list)
    connectors: list[VisualConnectorDTO] = Field(default_factory=list)
    summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class MultimodalGraphNodeDTO(BaseModel):
    id: str
    label: str
    node_type: str
    element_type: str | None = None
    bounding_box: VisionBoundingBoxDTO | None = None
    diagram_id: str | None = None
    document_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MultimodalGraphEdgeDTO(BaseModel):
    source: str
    target: str
    relation: str
    protocol: str | None = None
    is_cross_modal: bool = False
    confidence: float = 1.0


class MultimodalGraphResponseDTO(BaseModel):
    root_entity: str
    nodes: list[MultimodalGraphNodeDTO] = Field(default_factory=list)
    edges: list[MultimodalGraphEdgeDTO] = Field(default_factory=list)
    cross_modal_links_count: int = 0
    triples_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Voice Streaming & Barge-In (Battery #30 / Milestone 114) ─────────────────


class VoiceStreamSessionConfigDTO(BaseModel):
    session_id: str
    tenant_id: str
    selected_voice: str = "neural_natural"
    sample_rate_hz: int = 16000
    channels: int = 1
    sensitivity: float = 0.65
    silence_threshold_ms: int = 400
    speed: float = 1.0


class VoiceStreamEventDTO(BaseModel):
    event_type: str
    session_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


# ── Distributed MCP Mesh & Agent Federation (Battery #30 / Milestone 115) ─────


class MeshPeerNodeDTO(BaseModel):
    node_id: str
    cluster_id: str
    endpoint_url: str
    role: str = "sovereign_node"
    status: str = "online"
    advertised_tools: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: float = 10.0
    last_heartbeat: float = 0.0
    public_key_fingerprint: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class MeshStatusSummaryDTO(BaseModel):
    battery_id: str = "distributed_mcp_mesh"
    status: str = "active"
    total_nodes: int
    active_nodes: int
    total_mesh_tools: int
    routing_policy: str = "local_first"
    nodes: list[MeshPeerNodeDTO] = Field(default_factory=list)


class FederatedDelegationResponseDTO(BaseModel):
    delegation_id: str
    status: str
    source_cluster_id: str
    target_cluster_id: str
    tenant_id: str
    synthesis: str
    tool_trace_summary: list[dict[str, Any]] = Field(default_factory=list)
    execution_latency_ms: float = 0.0
    signature: str = ""
    error_message: str | None = None


