"""Domain abstractions and interfaces for GraphRAG Knowledge Graph Indexing."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class EntityTriple(BaseModel):
    """Subject-Predicate-Object relationship triple extracted from document text."""

    triple_id: str | None = None
    subject: str = Field(..., description="Source entity or subject term")
    predicate: str = Field(..., description="Relationship or predicate type")
    object: str = Field(..., description="Target entity or object term")
    chunk_id: str | None = Field(default=None, description="Source document chunk ID")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphSearchResult(BaseModel):
    """Result of multi-hop knowledge graph retrieval."""

    root_entity: str
    max_hops: int
    triples: list[EntityTriple] = Field(default_factory=list)
    connected_entities: list[str] = Field(default_factory=list)


class GraphCapabilities(BaseModel):
    """Machine capability profile and supported graph engines."""

    machine_profile: str = Field(..., description="Host hardware profile (e.g. 'macbook', 'oracle_vm_lean')")
    supported_engines: list[str] = Field(default_factory=list, description="List of allowed graph engine types")
    active_engine: str = Field(..., description="Currently active graph engine ('postgres' | 'neo4j')")
    neo4j_status: str = Field(..., description="Status of Neo4j connection ('online' | 'offline' | 'unsupported')")
    message: str = Field(..., description="Human-readable status or guidance message")


class BaseGraphRepository(ABC):
    """Abstract Port for Knowledge Graph storage and multi-hop retrieval."""

    @abstractmethod
    async def add_triples(self, tenant_id: str, triples: list[EntityTriple]) -> int:
        """Persist a list of entity relationship triples for a tenant."""
        pass

    @abstractmethod
    async def search_triples(
        self, tenant_id: str, entity: str, max_hops: int = 2
    ) -> GraphSearchResult:
        """Perform multi-hop graph traversal starting from a root entity."""
        pass

    @abstractmethod
    async def get_graph_summary(self, tenant_id: str) -> dict[str, Any]:
        """Summarize knowledge graph statistics for a tenant."""
        pass

    @abstractmethod
    async def delete_document_triples(self, tenant_id: str, document_id: str) -> int:
        """Remove all entity triples associated with a specific document."""
        pass

    @abstractmethod
    async def delete_triple(self, tenant_id: str, triple_id: str) -> bool:
        """Delete a single triple by ID."""
        pass
