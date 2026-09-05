"""Domain Abstractions for Sovereign Edge Vector Synchronization (M98).

Defines pure domain entities, data models, and abstract protocols for
differential vector synchronization, embedded SQLite FTS5/vector storage,
offline-first hybrid context retrieval, and mutation reconciliation.
Zero infrastructure or framework imports (strictly Hexagonal).
"""

from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class EdgeNodeStatus(StrEnum):
    """Operational status of an edge node device."""

    ONLINE = "online"
    OFFLINE = "offline"
    SYNCING = "syncing"


class SyncDirection(StrEnum):
    """Direction of synchronization between cloud and edge."""

    DOWNSTREAM_PULL = "downstream_pull"
    UPSTREAM_PUSH = "upstream_push"
    FULL_BUNDLE = "full_bundle"


class OfflineExecutionTier(StrEnum):
    """Offline LLM / context resolution tier."""

    HYBRID_CACHE = "hybrid_cache"
    LOCAL_SLM = "local_slm"
    GROUNDED_EXTRACTION = "grounded_extraction"
    SPECULATIVE_QUEUE = "speculative_queue"


class ChunkSyncItem(BaseModel):
    """A single document chunk for edge synchronization."""

    chunk_id: str
    document_id: str
    chunk_index: int = 0
    content: str
    token_count: int = 0
    meta_data: dict[str, Any] = Field(default_factory=dict)
    sequence_num: int = 0


class VectorSyncItem(BaseModel):
    """A single vector embedding item for edge synchronization."""

    chunk_id: str
    embedding: list[float]
    dimension: int = 768


class EdgeSyncDelta(BaseModel):
    """Differential delta of changes since a previous sequence checkpoint."""

    tenant_id: str
    checkpoint_sequence: int = 0
    previous_sequence: int = 0
    added_chunks: list[ChunkSyncItem] = Field(default_factory=list)
    added_vectors: list[VectorSyncItem] = Field(default_factory=list)
    deleted_chunk_ids: list[str] = Field(default_factory=list)
    checksum_sha256: str = ""
    generated_at: str = ""

    @property
    def total_chunks(self) -> int:
        return len(self.added_chunks)

    @property
    def since_seq(self) -> int:
        return self.previous_sequence

    @property
    def high_watermark_seq(self) -> int:
        return self.checkpoint_sequence

    @property
    def chunks(self) -> list[ChunkSyncItem]:
        return self.added_chunks

    @property
    def vectors(self) -> list[VectorSyncItem]:
        return self.added_vectors


class EdgeMutation(BaseModel):
    """A mutation created on an edge device while offline."""

    mutation_id: str
    tenant_id: str
    node_id: str
    entity_type: str  # e.g. "feedback", "annotation", "chat_log", "field_note"
    action: str = "insert"  # e.g. "insert", "update", "delete"
    payload: dict[str, Any] = Field(default_factory=dict)
    lamport_timestamp: int = 0
    device_timestamp: str = ""


class EdgeSyncConflictResolution(BaseModel):
    """Reconciliation result for an edge mutation."""

    mutation_id: str
    status: str  # "applied", "discarded", "merged"
    cloud_sequence: int = 0
    resolution_strategy: str  # "last_write_wins", "idempotent_ignore", "appended"
    message: str = ""


class EdgeSearchRequest(BaseModel):
    """Offline or simulated edge hybrid search query."""

    query: str
    query_embedding: list[float] | None = None
    top_k: int = 5
    alpha: float = 0.5  # 0.0 = pure BM25, 1.0 = pure vector
    use_hybrid: bool = True
    filters: dict[str, Any] = Field(default_factory=dict)


class EdgeSearchResultItem(BaseModel):
    """Single result from edge hybrid search."""

    chunk_id: str
    document_id: str
    content: str
    score: float = 0.0
    vector_score: float = 0.0
    bm25_score: float = 0.0
    match_type: str = "hybrid"  # "vector", "bm25", "hybrid"
    meta_data: dict[str, Any] = Field(default_factory=dict)


class EdgeSearchResponse(BaseModel):
    """Response from edge search with offline execution attribution."""

    results: list[EdgeSearchResultItem] = Field(default_factory=list)
    total_hits: int = 0
    latency_ms: float = 0.0
    source: str = "local_sqlite"
    execution_tier: OfflineExecutionTier = OfflineExecutionTier.GROUNDED_EXTRACTION
    synthesized_answer: str | None = None

    @property
    def items(self) -> list[EdgeSearchResultItem]:
        return self.results

    @property
    def hybrid_mode(self) -> bool:
        return self.total_hits > 0 and any(r.match_type == "hybrid" for r in self.results)


class EdgeBundleManifest(BaseModel):
    """Manifest describing a pre-built Sovereign Edge database bundle."""

    bundle_id: str
    tenant_id: str
    database_engine: str = "sqlite3"
    total_documents: int = 0
    total_chunks: int = 0
    total_vectors: int = 0
    vector_dimension: int = 768
    checkpoint_sequence: int = 0
    checksum_sha256: str = ""
    created_at: str = ""
    file_size_bytes: int = 0
    bundle_path: str = ""
    sqlite_version: str = "3.43.0"

    @property
    def high_watermark_seq(self) -> int:
        return self.checkpoint_sequence


class EdgeNodeMetadata(BaseModel):
    """Registered edge node device metadata."""

    node_id: str
    tenant_id: str
    device_name: str
    platform: str = "darwin_arm64"
    tier: OfflineExecutionTier = OfflineExecutionTier.HYBRID_CACHE
    last_synced_seq: int = 0
    last_heartbeat_at: str = ""
    status: EdgeNodeStatus = EdgeNodeStatus.ONLINE
    vector_dimension: int = 768
    capabilities: list[str] = Field(default_factory=lambda: ["fts5", "vector_blob"])
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def node_name(self) -> str:
        return self.device_name

    @property
    def last_synced_sequence(self) -> int:
        return self.last_synced_seq


class EdgeDeltaCalculatorProtocol(Protocol):
    """Protocol for calculating delta packages between sequence numbers."""

    def compute_delta(
        self,
        tenant_id: str,
        since_seq: int,
        current_seq: int,
        chunks: list[ChunkSyncItem],
        vectors: list[VectorSyncItem],
        deleted_ids: list[str],
    ) -> EdgeSyncDelta: ...

    def verify_checksum(self, delta: EdgeSyncDelta) -> bool: ...


class EdgeDatabaseEngineProtocol(Protocol):
    """Protocol for interacting with the local embedded SQLite edge database."""

    def initialize_schema(self, db_path: str) -> None: ...

    def apply_delta(self, db_path: str, delta: EdgeSyncDelta) -> int: ...

    def search_hybrid(
        self,
        db_path: str,
        request: EdgeSearchRequest,
    ) -> EdgeSearchResponse: ...

    def record_mutation(self, db_path: str, mutation: EdgeMutation) -> None: ...

    def get_pending_mutations(self, db_path: str) -> list[EdgeMutation]: ...


class EdgeReconciliationProtocol(Protocol):
    """Protocol for reconciling edge mutations into the central cloud cluster."""

    async def reconcile_mutations(
        self,
        tenant_id: str,
        mutations: list[EdgeMutation],
    ) -> list[EdgeSyncConflictResolution]: ...


class EdgeSyncAdapterProtocol(Protocol):
    """Protocol for cloud-side delta generation and bundle assembly."""

    async def get_delta_for_tenant(
        self,
        tenant_id: str,
        since_seq: int,
        limit: int = 500,
    ) -> EdgeSyncDelta: ...

    async def export_sovereign_bundle(
        self,
        tenant_id: str,
        output_path: str,
    ) -> EdgeBundleManifest: ...
