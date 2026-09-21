"""Domain abstractions for Graph-of-Thoughts (GoT) Planning & Hierarchical Memory (M123).

Conforms strictly to Hexagonal Architecture boundaries:
- Standard library + pydantic only (0 framework, ORM, or third-party ML imports).
- Defines Graph-of-Thoughts DAG representation, thought vertices, directed edges.
- Defines graph operations: generate, aggregate, refine, score, prune.
- Defines 3-tier Hierarchical Working Memory: L1 Scratchpad, L2 Episodic, L3 Semantic.
- Defines GoTPlannerProtocol port interface.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class GoTThoughtType(StrEnum):
    """Classification of thought node origin in the reasoning DAG."""

    ROOT = "root"
    GENERATION = "generation"
    AGGREGATION = "aggregation"
    REFINEMENT = "refinement"
    TERMINAL = "terminal"


class GoTThoughtStatus(StrEnum):
    """Lifecycle status of a thought vertex in the GoT graph."""

    PENDING = "pending"
    EXPLORING = "exploring"
    SCORED = "scored"
    PRUNED = "pruned"
    CONVERGED = "converged"


class GoTEdgeType(StrEnum):
    """Type of directed dependency link between thoughts."""

    DERIVATION = "derivation"
    AGGREGATION = "aggregation"
    REFINEMENT = "refinement"
    CONVERGENCE = "convergence"


class MemoryLayer(StrEnum):
    """Cognitive memory hierarchy layers."""

    L1_SCRATCHPAD = "l1_scratchpad"
    L2_EPISODIC = "l2_episodic"
    L3_SEMANTIC = "l3_semantic"


class GoTThoughtNode(BaseModel):
    """A discrete thought vertex in the reasoning Directed Acyclic Graph."""

    id: str = Field(..., description="Unique identifier of the thought vertex")
    tenant_id: str = Field(..., description="Tenant namespace owner")
    prompt: str = Field(..., description="Prompt or goal steering this thought")
    content: str = Field(..., description="Synthesized reasoning content, hypothesis, or solution")
    thought_type: GoTThoughtType = Field(default=GoTThoughtType.GENERATION)
    status: GoTThoughtStatus = Field(default=GoTThoughtStatus.PENDING)
    parent_ids: list[str] = Field(default_factory=list, description="In-degree antecedent thought IDs")
    child_ids: list[str] = Field(default_factory=list, description="Out-degree descendant thought IDs")
    score: float = Field(default=0.0, ge=0.0, le=1.0, description="Composite evaluation score S(v)")
    grounding_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Contextual grounding score")
    coherence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Logical coherence score")
    constraint_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Constraint satisfaction score")
    token_cost: int = Field(default=0, ge=0, description="Tokens expended to generate/score thought")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Inference latency in milliseconds")
    iteration_depth: int = Field(default=0, ge=0, description="Topological depth in the DAG")
    is_optimal_path: bool = Field(default=False, description="Whether thought lies on best converged path")
    created_at: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GoTEdge(BaseModel):
    """Directed causal dependency edge between two thoughts (source -> target)."""

    source_id: str = Field(..., description="Antecedent thought vertex ID")
    target_id: str = Field(..., description="Successor thought vertex ID")
    edge_type: GoTEdgeType = Field(default=GoTEdgeType.DERIVATION)
    weight: float = Field(default=1.0, ge=0.0, description="Edge affinity or derivation confidence")


class GoTGraph(BaseModel):
    """The complete Graph-of-Thoughts DAG structure for a planning task."""

    graph_id: str = Field(..., description="Unique plan session identifier")
    tenant_id: str = Field(..., description="Tenant namespace owner")
    query: str = Field(..., description="Original complex prompt or objective")
    root_id: str = Field(..., description="Root thought vertex ID")
    nodes: dict[str, GoTThoughtNode] = Field(default_factory=dict, description="Map of vertex ID to thought")
    edges: list[GoTEdge] = Field(default_factory=list, description="Directed dependency edges")
    optimal_path: list[str] = Field(default_factory=list, description="Optimal vertex sequence root -> terminal")
    best_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Highest score along optimal path")
    is_converged: bool = Field(default=False, description="Whether graph reached terminal convergence")
    total_tokens: int = Field(default=0, ge=0, description="Cumulative tokens across all thoughts")
    total_latency_ms: float = Field(default=0.0, ge=0.0, description="Total execution time in ms")
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class GoTPlanRequest(BaseModel):
    """Request to initiate a new Graph-of-Thoughts planning session."""

    query: str = Field(..., min_length=2, description="Target prompt or goal to plan with GoT")
    branching_factor: int = Field(default=3, ge=1, le=10, description="Successors generated per branch (k)")
    max_depth: int = Field(default=4, ge=1, le=10, description="Maximum search / reasoning depth")
    pruning_threshold: float = Field(default=0.4, ge=0.0, le=1.0, description="Score threshold below which thoughts are pruned (tau)")
    aggregation_threshold: int = Field(default=2, ge=2, le=5, description="Min candidate branches required to aggregate (m)")
    metadata: dict[str, Any] = Field(default_factory=dict)


class GoTPlanResponse(BaseModel):
    """Response containing the initialized or updated GoT graph."""

    graph: GoTGraph
    message: str = "Plan session initialized"


class GoTStepRequest(BaseModel):
    """Request to execute a single graph transformation step."""

    action: str = Field(..., description="Step action: 'generate', 'aggregate', 'refine', 'score', 'prune'")
    target_node_ids: list[str] = Field(default_factory=list, description="Specific nodes to transform")
    parameters: dict[str, Any] = Field(default_factory=dict)


class GoTAggregateRequest(BaseModel):
    """Request to combine multiple independent thought branches into one synthesis."""

    source_node_ids: list[str] = Field(..., min_length=2, description="Vertices to combine into aggregate")
    synthesis_prompt: str | None = Field(default=None, description="Optional custom synthesis guidance")


class HierarchicalMemoryNode(BaseModel):
    """A memory unit stored across the hierarchical cognitive pyramid."""

    id: str = Field(..., description="Memory record identifier")
    tenant_id: str = Field(..., description="Tenant namespace owner")
    layer: MemoryLayer = Field(..., description="L1 Scratchpad, L2 Episodic, or L3 Semantic")
    title: str = Field(..., description="Short cognitive title or concept label")
    content: str = Field(..., description="Distilled knowledge or thought content")
    activation: float = Field(default=1.0, ge=0.0, description="Current spreading activation level A(v)")
    stability_days: float = Field(default=1.0, ge=0.1, description="Ebbinghaus memory stability S")
    retention_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Current Ebbinghaus retention R(t)")
    access_count: int = Field(default=0, ge=0)
    linked_graph_id: str | None = None
    linked_thought_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    last_accessed_at: float = Field(default_factory=time.time)
    created_at: float = Field(default_factory=time.time)


class HierarchicalMemoryView(BaseModel):
    """Tenant-isolated view of all hierarchical memory tiers."""

    tenant_id: str
    l1_scratchpad: list[HierarchicalMemoryNode] = Field(default_factory=list)
    l2_episodic: list[HierarchicalMemoryNode] = Field(default_factory=list)
    l3_semantic: list[HierarchicalMemoryNode] = Field(default_factory=list)
    total_nodes: int = 0
    average_retention: float = 0.0


class DistillationRequest(BaseModel):
    """Request to contract and distill a completed GoT graph into persistent memory."""

    graph_id: str = Field(..., description="ID of completed GoT graph to distill")
    target_layer: MemoryLayer = Field(default=MemoryLayer.L3_SEMANTIC)
    distillation_prompt: str | None = None


class DistillationResult(BaseModel):
    """Outcome of distilling a GoT plan into long-term hierarchical memory."""

    distilled_node_id: str
    layer: MemoryLayer
    title: str
    summary: str
    status: str = "distilled"


class GoTSimulateRequest(BaseModel):
    """Parameters for running an interactive Graph-of-Thoughts planning simulation."""

    query: str = Field(default="Optimize distributed RAG vector retrieval latency")
    branching_factor: int = Field(default=3, ge=1, le=5)
    aggregation_fanin: int = Field(default=2, ge=2, le=4)
    pruning_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    max_depth: int = Field(default=3, ge=1, le=5)


class GoTSimulateResponse(BaseModel):
    """Empirical output of a Graph-of-Thoughts simulation."""

    graph_id: str
    nodes_count: int
    edges_count: int
    aggregations_count: int
    pruned_count: int
    optimal_path_ids: list[str]
    best_score: float
    tokens_consumed: int
    estimated_latency_ms: float
    nodes: list[GoTThoughtNode]
    edges: list[GoTEdge]
    hierarchical_memory: HierarchicalMemoryView


class GoTPlannerProtocol(ABC):
    """Port interface for Graph-of-Thoughts Planning and Hierarchical Memory."""

    @abstractmethod
    async def create_plan(self, tenant_id: str, request: GoTPlanRequest) -> GoTGraph:
        """Initialize a new GoT planning graph with root query node."""

    @abstractmethod
    async def get_plan(self, tenant_id: str, graph_id: str) -> GoTGraph | None:
        """Retrieve full state of a GoT plan graph."""

    @abstractmethod
    async def step_plan(self, tenant_id: str, graph_id: str, request: GoTStepRequest) -> GoTGraph:
        """Execute a single graph transformation step (generate/refine/score/prune)."""

    @abstractmethod
    async def execute_plan(self, tenant_id: str, graph_id: str) -> GoTGraph:
        """Autonomously drive GoT loop to terminal convergence."""

    @abstractmethod
    async def aggregate_thoughts(self, tenant_id: str, graph_id: str, request: GoTAggregateRequest) -> GoTGraph:
        """Combine multiple independent thought vertices into a synthesis vertex."""

    @abstractmethod
    async def get_hierarchical_memory(self, tenant_id: str) -> HierarchicalMemoryView:
        """Retrieve L1, L2, and L3 memory tiers for a tenant."""

    @abstractmethod
    async def distill_graph(self, tenant_id: str, request: DistillationRequest) -> DistillationResult:
        """Distill high-scoring GoT reasoning graph into long-term hierarchical memory."""

    @abstractmethod
    def simulate(self, request: GoTSimulateRequest) -> GoTSimulateResponse:
        """Run self-contained mathematical GoT simulation."""


class GoTRepositoryProtocol(Protocol):
    """Port interface for persistent storage and retrieval of GoT reasoning graphs."""

    async def save_graph(self, graph: GoTGraph) -> None:
        """Persist or update a complete GoTGraph and its thought vertices."""
        ...

    async def get_graph(self, tenant_id: str, graph_id: str) -> GoTGraph | None:
        """Fetch a GoTGraph by ID for a specific tenant."""
        ...

    async def list_graphs(self, tenant_id: str, limit: int = 50) -> list[GoTGraph]:
        """List GoT graphs for a tenant."""
        ...
