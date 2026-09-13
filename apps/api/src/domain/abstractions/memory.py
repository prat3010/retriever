"""Domain abstractions for Cognitive Agent Memory Consolidation & Experience Distillation (M108).

Conforms strictly to Hexagonal Architecture boundaries (0 framework imports).
Defines:
- Memory types (Episodic, Semantic, Procedural)
- Episodic memory node representation
- Ebbinghaus forgetting curve retention contracts
- Experience distillation and ReAct consolidation payloads
- Cognitive memory abstract interface protocol
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Classification of cognitive memory representations."""

    EPISODIC = "episodic"  # Specific task resolution trace, situation & outcome
    SEMANTIC = "semantic"  # Distilled factual knowledge or schema relation
    PROCEDURAL = "procedural"  # Learned tool execution pattern or error recovery rule


class EpisodicMemoryNode(BaseModel):
    """An immutable, consolidated cognitive memory node."""

    id: str
    tenant_id: str
    memory_type: MemoryType = MemoryType.EPISODIC
    query: str
    distilled_insight: str
    tool_chain: list[str] = Field(default_factory=list)
    success: bool = True
    turns_count: int = 1
    importance_score: float = 0.5  # 0.0 to 1.0 scale
    stability_score: float = 1.0  # S: Memory stability in days
    last_accessed_at: float = Field(default_factory=time.time)
    access_count: int = 0
    created_at: float = Field(default_factory=time.time)
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryQuery(BaseModel):
    """Specification for querying cognitive memory."""

    query: str
    limit: int = 5
    min_similarity: float = 0.65
    memory_type: MemoryType | None = None


class MemorySearchResult(BaseModel):
    """Search hit with calculated dynamic retention score."""

    node: EpisodicMemoryNode
    similarity_score: float
    retention_score: float  # Computed dynamically via Ebbinghaus curve: R(t) = exp(-dt / S)


class DistilledGuidance(BaseModel):
    """Consolidated experience guidance injected into prompt context."""

    relevant_nodes: list[MemorySearchResult] = Field(default_factory=list)
    guidance_prompt: str = ""
    matched_tool_chains: list[list[str]] = Field(default_factory=list)


class ConsolidationRequest(BaseModel):
    """Payload for consolidating a completed ReAct trace into episodic memory."""

    tenant_id: str
    session_id: str = ""
    query: str
    turns: list[dict[str, Any]] = Field(default_factory=list)
    final_answer: str | None = None
    success: bool = True


class ConsolidationResult(BaseModel):
    """Result of memory consolidation."""

    node_id: str
    distilled_insight: str
    importance_score: float
    tool_chain: list[str] = Field(default_factory=list)
    memory_type: MemoryType = MemoryType.EPISODIC
    status: str = "consolidated"


class MemoryStats(BaseModel):
    """Tenant-isolated memory aggregate metrics."""

    total_memories: int = 0
    episodic_count: int = 0
    semantic_count: int = 0
    procedural_count: int = 0
    avg_stability: float = 1.0
    total_access_count: int = 0


class CognitiveMemoryProtocol(ABC):
    """Hexagonal domain port for cognitive memory operations."""

    @abstractmethod
    async def consolidate_trace(
        self, tenant_id: str, request: ConsolidationRequest
    ) -> ConsolidationResult:
        """Consolidate a ReAct execution trace into an episodic memory node."""
        raise NotImplementedError

    @abstractmethod
    async def retrieve_guidance(
        self, tenant_id: str, query: str, limit: int = 3, min_similarity: float = 0.65
    ) -> DistilledGuidance:
        """Retrieve relevant past experiences and format distilled guidance."""
        raise NotImplementedError

    @abstractmethod
    async def list_memories(
        self,
        tenant_id: str,
        memory_type: MemoryType | None = None,
        query: str | None = None,
        limit: int = 50,
    ) -> list[EpisodicMemoryNode]:
        """List and search cognitive memories for a tenant."""
        raise NotImplementedError

    @abstractmethod
    async def delete_memory(self, tenant_id: str, node_id: str) -> bool:
        """Delete a specific cognitive memory node (compliance & hygiene)."""
        raise NotImplementedError

    @abstractmethod
    async def prune_memories(self, tenant_id: str, min_retention: float = 0.15) -> int:
        """Prune decayed memories whose Ebbinghaus retention falls below threshold."""
        raise NotImplementedError

    @abstractmethod
    async def get_stats(self, tenant_id: str) -> MemoryStats:
        """Retrieve aggregate memory statistics for a tenant."""
        raise NotImplementedError
