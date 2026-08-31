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
    document_id: str | None = Field(default=None, description="Source document ID")
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

    @abstractmethod
    async def get_all_triples(self, tenant_id: str, limit: int = 1000) -> list[EntityTriple]:
        """Fetch all entity relationship triples for a tenant."""
        pass



class GraphCommunity(BaseModel):
    """Hierarchical community cluster of entities and relationships."""

    community_id: str = Field(..., description="Unique community identifier")
    tenant_id: str = Field(..., description="Tenant ID owning the community")
    level: int = Field(default=0, description="Hierarchy level (0: micro-cluster, 1: domain, 2: macro-theme)")
    title: str = Field(..., description="Title or theme of the community")
    entities: list[str] = Field(default_factory=list, description="List of entity names in this community")
    triples: list[EntityTriple] = Field(default_factory=list, description="Core relationship triples in community")
    weight: float = Field(default=1.0, description="Community modularity / edge density weight")
    summary: str = Field(default="", description="Narrative summary of this community cluster")
    sub_community_ids: list[str] = Field(default_factory=list, description="Child sub-community IDs")
    metadata: dict[str, Any] = Field(default_factory=dict)


class CommunityHierarchy(BaseModel):
    """Multi-level community hierarchy output from Leiden detection."""

    tenant_id: str
    total_communities: int
    levels: dict[int, list[GraphCommunity]] = Field(default_factory=dict)
    modularity_score: float = Field(default=0.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseCommunityDetector(ABC):
    """Abstract port for graph community detection."""

    @abstractmethod
    def detect_communities(
        self, tenant_id: str, triples: list[EntityTriple], max_levels: int = 3
    ) -> CommunityHierarchy:
        """Partition entity-relation graph into hierarchical communities."""
        pass


class BaseCommunitySummarizer(ABC):
    """Abstract port for community synthesis and summarization."""

    @abstractmethod
    async def summarize_community(
        self, community: GraphCommunity, llm_provider: Any = None
    ) -> str:
        """Generate executive narrative summary for a community cluster."""
        pass

