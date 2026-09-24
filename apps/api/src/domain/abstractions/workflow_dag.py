"""Domain abstractions for Visual DAG Workflow Canvas & Agentic Graph Composer (M126).

Conforms strictly to Hexagonal Architecture boundaries:
- Standard library + pydantic only (zero framework, database, or network imports).
- Defines DAG node classifications, directed edges, graph topological structures.
- Defines step execution details with token cost attribution and latency tracking.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DAGNodeType(StrEnum):
    """Classification of discrete computational nodes in a workflow DAG."""

    INPUT = "input"
    RETRIEVAL = "retrieval"
    GUARDRAIL = "guardrail"
    TRANSFORM = "transform"
    PROMPT = "prompt"
    LLM = "llm"
    EVALUATOR = "evaluator"
    ROUTER = "router"
    OUTPUT = "output"


class NodeExecutionStatus(StrEnum):
    """Lifecycle state of an individual node during DAG pipeline execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DAGNodePosition(BaseModel):
    """2D canvas coordinates for visual workflow graph layout."""

    x: float = 0.0
    y: float = 0.0


class DAGNode(BaseModel):
    """A discrete operation vertex in the visual workflow DAG."""

    id: str = Field(..., description="Unique node identifier within the graph")
    type: DAGNodeType = Field(..., description="Operational node type")
    title: str = Field(..., description="Human-readable title")
    description: str = Field(default="", description="Summary of node responsibility")
    position: DAGNodePosition = Field(default_factory=DAGNodePosition)
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Node-specific operational parameters (model, k, threshold, etc.)",
    )
    input_keys: list[str] = Field(
        default_factory=list,
        description="Variables required by this node from antecedent outputs or graph input",
    )
    output_keys: list[str] = Field(
        default_factory=list,
        description="Variables published by this node to descendant nodes or graph output",
    )


class DAGEdge(BaseModel):
    """Directed dependency link connecting a source node to a target node."""

    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node ID producing the upstream data")
    target: str = Field(..., description="Target node ID consuming the upstream data")
    source_handle: str | None = Field(default=None, description="Output port ID on the source")
    target_handle: str | None = Field(default=None, description="Input port ID on the target")
    condition: str | None = Field(
        default=None,
        description="Conditional branch predicate for router nodes (e.g. 'true', 'escalate')",
    )


class WorkflowDAGGraph(BaseModel):
    """Complete declarative specification of a Directed Acyclic Graph workflow."""

    id: str = Field(..., description="Unique graph ID")
    name: str = Field(..., description="Workflow title")
    description: str = Field(default="", description="Workflow overview")
    tenant_id: str | None = Field(default=None, description="Tenant namespace owner")
    nodes: list[DAGNode] = Field(default_factory=list, description="All node vertices")
    edges: list[DAGEdge] = Field(default_factory=list, description="All directed edges")


class StepExecutionDetail(BaseModel):
    """Audited execution record of an individual node in the DAG."""

    node_id: str
    node_type: DAGNodeType
    status: NodeExecutionStatus = NodeExecutionStatus.PENDING
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class DAGExecutionResult(BaseModel):
    """Full execution summary, step telemetry, and final output of a workflow DAG run."""

    execution_id: str
    tenant_id: str
    graph_id: str
    status: str = "completed"  # "completed" | "failed"
    topological_order: list[str] = Field(default_factory=list)
    step_details: dict[str, StepExecutionDetail] = Field(default_factory=dict)
    final_output: dict[str, Any] = Field(default_factory=dict)
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    started_at: str = ""
    completed_at: str = ""


class DAGCompilerResult(BaseModel):
    """Validation report and topological execution plan produced by the DAG compiler."""

    graph_id: str
    is_valid: bool
    topological_order: list[str] = Field(default_factory=list)
    parallel_stages: list[list[str]] = Field(
        default_factory=list,
        description="Topological partitions where nodes in the same stage can run concurrently",
    )
    variable_bindings: dict[str, list[str]] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
