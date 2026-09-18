"""FastAPI Router for Graph-of-Thoughts (GoT) Planning & Hierarchical Memory (M123).

Exposes REST endpoints for:
- Initializing GoT reasoning DAG plans.
- Step-by-step transformations (Generate, Aggregate, Refine, Score, Prune).
- Autonomous multi-step plan execution to terminal convergence.
- Multi-antecedent thought aggregation.
- 3-tier Hierarchical Working Memory inspection and distillation.
- Interactive mathematical simulation for SaaS Studio.
- Platform Battery #38 health check.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status

from src.container import container
from src.domain.abstractions.got_planner import (
    DistillationRequest,
    DistillationResult,
    GoTAggregateRequest,
    GoTGraph,
    GoTPlanRequest,
    GoTPlanResponse,
    GoTSimulateRequest,
    GoTSimulateResponse,
    GoTStepRequest,
    HierarchicalMemoryView,
)

router = APIRouter(prefix="/v1", tags=["Graph-of-Thoughts Planning"])


def get_got_planner() -> Any:
    planner = getattr(container, "got_planner_adapter", None)
    if not planner:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GoT Planner service is not initialized in application container.",
        )
    return planner


@router.post(
    "/tenants/{tenantId}/got/plans",
    response_model=GoTPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_got_plan(tenantId: str, request: GoTPlanRequest) -> GoTPlanResponse:
    """Initialize a new Graph-of-Thoughts reasoning session for a prompt."""
    planner = get_got_planner()
    graph = await planner.create_plan(tenantId, request)
    return GoTPlanResponse(graph=graph, message="GoT planning session initialized successfully.")


@router.get(
    "/tenants/{tenantId}/got/plans/{planId}",
    response_model=GoTGraph,
    status_code=status.HTTP_200_OK,
)
async def get_got_plan(tenantId: str, planId: str) -> GoTGraph:
    """Retrieve full DAG graph state of an active or completed GoT plan."""
    planner = get_got_planner()
    graph = await planner.get_plan(tenantId, planId)
    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"GoT Plan '{planId}' not found for tenant '{tenantId}'.",
        )
    return graph


@router.post(
    "/tenants/{tenantId}/got/plans/{planId}/step",
    response_model=GoTGraph,
    status_code=status.HTTP_200_OK,
)
async def step_got_plan(tenantId: str, planId: str, request: GoTStepRequest) -> GoTGraph:
    """Execute a single graph transformation step (generate, refine, score, prune)."""
    planner = get_got_planner()
    try:
        return await planner.step_plan(tenantId, planId, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/tenants/{tenantId}/got/plans/{planId}/execute",
    response_model=GoTGraph,
    status_code=status.HTTP_200_OK,
)
async def execute_got_plan(tenantId: str, planId: str) -> GoTGraph:
    """Autonomously drive GoT loop to terminal convergence."""
    planner = get_got_planner()
    try:
        return await planner.execute_plan(tenantId, planId)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post(
    "/tenants/{tenantId}/got/plans/{planId}/aggregate",
    response_model=GoTGraph,
    status_code=status.HTTP_200_OK,
)
async def aggregate_got_thoughts(tenantId: str, planId: str, request: GoTAggregateRequest) -> GoTGraph:
    """Combine multiple independent thought branches into a unified synthesis vertex."""
    planner = get_got_planner()
    try:
        return await planner.aggregate_thoughts(tenantId, planId, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/tenants/{tenantId}/got/memory/hierarchy",
    response_model=HierarchicalMemoryView,
    status_code=status.HTTP_200_OK,
)
async def get_hierarchical_memory(tenantId: str) -> HierarchicalMemoryView:
    """Retrieve multi-tier memory view (L1 Scratchpad, L2 Episodic, L3 Semantic) for tenant."""
    planner = get_got_planner()
    return await planner.get_hierarchical_memory(tenantId)


@router.post(
    "/tenants/{tenantId}/got/memory/distill",
    response_model=DistillationResult,
    status_code=status.HTTP_200_OK,
)
async def distill_got_graph(tenantId: str, request: DistillationRequest) -> DistillationResult:
    """Contract and distill a completed GoT graph into long-term hierarchical memory."""
    planner = get_got_planner()
    try:
        return await planner.distill_graph(tenantId, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/got/simulate",
    response_model=GoTSimulateResponse,
    status_code=status.HTTP_200_OK,
)
async def simulate_got(request: GoTSimulateRequest) -> GoTSimulateResponse:
    """Interactive GoT and hierarchical memory mathematical simulation for SaaS Studio."""
    planner = get_got_planner()
    return planner.simulate(request)


@router.get(
    "/got/health",
    status_code=status.HTTP_200_OK,
)
async def got_battery_health() -> dict[str, Any]:
    """Health check endpoint for Platform Battery #38 (hierarchical_memory_got_planner)."""
    return {
        "status": "healthy",
        "battery_id": "hierarchical_memory_got_planner",
        "battery_number": 38,
        "category": "computation_graph",
        "milestone": "M123 (v2.2.0-alpha1)",
        "capabilities": [
            "graph_of_thoughts_dag",
            "multi_in_degree_aggregation",
            "pareto_frontier_pruning",
            "highest_scoring_path_traversal",
            "hierarchical_working_memory_l1_l2_l3",
            "ebbinghaus_retention_decay",
            "spreading_activation_graph_contraction",
        ],
    }
