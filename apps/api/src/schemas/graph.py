"""DTO Schemas for Knowledge Graph Admin Endpoints."""

from pydantic import BaseModel, Field

from src.domain.abstractions.graph import EntityTriple


class GraphQueryRequest(BaseModel):
    """Request model for GraphRAG multi-hop query endpoint."""

    entity: str = Field(..., description="Root entity to start multi-hop traversal")
    max_hops: int = Field(default=2, ge=1, le=5, description="Maximum graph depth traversal hops")


class GraphEngineSwitchRequest(BaseModel):
    """Request model for 1-click graph engine switching."""

    engine: str = Field(..., description="Target graph engine ('postgres' | 'neo4j')")


class GraphCapabilitiesResponse(BaseModel):
    """Response model for machine profile and graph engine capabilities."""

    machine_profile: str
    supported_engines: list[str]
    active_engine: str
    neo4j_status: str
    message: str


class GraphSummaryResponse(BaseModel):
    """Response model for tenant knowledge graph summary."""

    tenant_id: str
    total_triples: int
    unique_entities: int
    storage_engine: str
    neo4j_status: str | None = None


class GraphQueryResponse(BaseModel):
    """Response model for multi-hop entity graph query."""

    root_entity: str
    max_hops: int
    triples: list[EntityTriple]
    connected_entities: list[str]
