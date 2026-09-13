"""FastAPI Router for Cognitive Agent Memory & Experience Distillation (M108)."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.adapters.api.security import verify_tenant_or_admin
from src.container import container
from src.domain.abstractions.memory import (
    ConsolidationRequest,
    ConsolidationResult,
    DistilledGuidance,
    EpisodicMemoryNode,
    MemoryStats,
    MemoryType,
)

router = APIRouter(prefix="/v1", tags=["Cognitive Memory"])


class GuidanceQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Prompt to retrieve relevant past experience guidance for")
    limit: int = Field(default=3, ge=1, le=10, description="Max memory nodes to retrieve")
    min_similarity: float = Field(default=0.65, ge=0.0, le=1.0, description="Minimum cosine similarity threshold")


class PruneRequest(BaseModel):
    min_retention: float = Field(default=0.15, ge=0.01, le=1.0, description="Retention threshold below which decayed memories are pruned")


@router.get(
    "/tenants/{tenantId}/memory/stats",
    response_model=MemoryStats,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
)
@router.get(
    "/tenants/{tenantId}/agentic/memory/stats",
    response_model=MemoryStats,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
    include_in_schema=False,
)
async def get_memory_stats(tenantId: str) -> MemoryStats:
    """Retrieve aggregate cognitive memory statistics for a tenant."""
    memory_engine = getattr(container, "cognitive_memory", None)
    if not memory_engine:
        raise HTTPException(status_code=503, detail="Cognitive memory engine is not initialized.")
    return await memory_engine.get_stats(tenantId)


@router.get(
    "/tenants/{tenantId}/memory/nodes",
    response_model=list[EpisodicMemoryNode],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
)
@router.get(
    "/tenants/{tenantId}/agentic/memory/nodes",
    response_model=list[EpisodicMemoryNode],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
    include_in_schema=False,
)
async def list_memory_nodes(
    tenantId: str,
    type: MemoryType | None = Query(default=None, description="Optional filter by MemoryType (episodic, semantic, procedural)"),
    query: str | None = Query(default=None, description="Optional search term matching query or distilled insight"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of nodes to return"),
) -> list[EpisodicMemoryNode]:
    """List cognitive memory nodes for a tenant with optional filtering."""
    memory_engine = getattr(container, "cognitive_memory", None)
    if not memory_engine:
        raise HTTPException(status_code=503, detail="Cognitive memory engine is not initialized.")
    return await memory_engine.list_memories(tenant_id=tenantId, memory_type=type, query=query, limit=limit)


@router.post(
    "/tenants/{tenantId}/memory/guidance",
    response_model=DistilledGuidance,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
)
@router.post(
    "/tenants/{tenantId}/agentic/memory/guidance",
    response_model=DistilledGuidance,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
    include_in_schema=False,
)
async def retrieve_experience_guidance(
    tenantId: str,
    request: GuidanceQueryRequest,
) -> DistilledGuidance:
    """Test and simulate experience distillation guidance for an incoming query."""
    memory_engine = getattr(container, "cognitive_memory", None)
    if not memory_engine:
        raise HTTPException(status_code=503, detail="Cognitive memory engine is not initialized.")
    return await memory_engine.retrieve_guidance(
        tenant_id=tenantId,
        query=request.query,
        limit=request.limit,
        min_similarity=request.min_similarity,
    )


@router.post(
    "/tenants/{tenantId}/memory/consolidate",
    response_model=ConsolidationResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_tenant_or_admin)],
)
@router.post(
    "/tenants/{tenantId}/agentic/memory/consolidate",
    response_model=ConsolidationResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_tenant_or_admin)],
    include_in_schema=False,
)
async def consolidate_experience_trace(
    tenantId: str,
    request: ConsolidationRequest,
) -> ConsolidationResult:
    """Consolidate a ReAct execution trace into an episodic memory node."""
    memory_engine = getattr(container, "cognitive_memory", None)
    if not memory_engine:
        raise HTTPException(status_code=503, detail="Cognitive memory engine is not initialized.")
    return await memory_engine.consolidate_trace(tenant_id=tenantId, request=request)


@router.delete(
    "/tenants/{tenantId}/memory/nodes/{nodeId}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
)
@router.delete(
    "/tenants/{tenantId}/agentic/memory/nodes/{nodeId}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
    include_in_schema=False,
)
async def delete_memory_node(
    tenantId: str,
    nodeId: str,
) -> dict[str, Any]:
    """Delete a specific cognitive memory node."""
    memory_engine = getattr(container, "cognitive_memory", None)
    if not memory_engine:
        raise HTTPException(status_code=503, detail="Cognitive memory engine is not initialized.")
    deleted = await memory_engine.delete_memory(tenant_id=tenantId, node_id=nodeId)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Memory node '{nodeId}' not found.")
    return {"deleted": True, "node_id": nodeId}


@router.post(
    "/tenants/{tenantId}/memory/prune",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
)
@router.post(
    "/tenants/{tenantId}/agentic/memory/prune",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
    include_in_schema=False,
)
async def prune_decayed_memories(
    tenantId: str,
    request: PruneRequest = PruneRequest(),
) -> dict[str, Any]:
    """Prune decayed memories whose Ebbinghaus retention score has decayed below threshold."""
    memory_engine = getattr(container, "cognitive_memory", None)
    if not memory_engine:
        raise HTTPException(status_code=503, detail="Cognitive memory engine is not initialized.")
    pruned_count = await memory_engine.prune_memories(tenant_id=tenantId, min_retention=request.min_retention)
    return {"pruned_count": pruned_count, "min_retention": request.min_retention}
