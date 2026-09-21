"""Cognitive Agent Memory Consolidation & Long-Horizon Experience Distillation Engine (M108).

Conforms strictly to Hexagonal Architecture boundaries (0 framework/database imports).
Implements:
- Mathematical Ebbinghaus forgetting curve retention decay: R(t) = exp(-dt / (S * 86400))
- Memory stability reinforcement upon successful retrieval: S_new = S_old * 1.5 + 0.5
- Automatic ReAct trace consolidation into episodic and procedural knowledge triples
- In-memory tenant-isolated vector cosine similarity search with term projector
- Low-retention automated memory pruning and GDPR compliance deletion
"""

from __future__ import annotations

import logging
import math
import re
import time
from uuid import uuid4

from src.domain.abstractions.memory import (
    CognitiveMemoryProtocol,
    CognitiveMemoryRepositoryProtocol,
    ConsolidationRequest,
    ConsolidationResult,
    DistilledGuidance,
    EpisodicMemoryNode,
    MemorySearchResult,
    MemoryStats,
    MemoryType,
)

logger = logging.getLogger(__name__)



def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase alphanumeric tokens."""
    return re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower())


def _build_term_vector(tokens: list[str], dim: int = 128) -> list[float]:
    """Build a deterministic normalized term frequency projection vector."""
    if not tokens:
        return [0.0] * dim
    vec = [0.0] * dim
    for t in tokens:
        idx = hash(t) % dim
        vec[idx] += 1.0
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2, strict=False))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm1 * norm2)))


class CognitiveMemoryEngine(CognitiveMemoryProtocol):
    """Core domain engine managing episodic memory consolidation and experience distillation."""

    def __init__(
        self,
        vector_dim: int = 128,
        repository: CognitiveMemoryRepositoryProtocol | None = None,
    ) -> None:
        self._vector_dim = vector_dim
        self._repo = repository
        # Tenant-isolated storage: {tenant_id: {node_id: EpisodicMemoryNode}}
        self._stores: dict[str, dict[str, EpisodicMemoryNode]] = {}

    async def _ensure_tenant_store(self, tenant_id: str) -> dict[str, EpisodicMemoryNode]:
        if tenant_id not in self._stores:
            self._stores[tenant_id] = {}
            if self._repo:
                try:
                    persisted = await self._repo.get_nodes(tenant_id)
                    for node in persisted:
                        if not node.embedding:
                            tokens = _tokenize(f"{node.query} {node.distilled_insight} {' '.join(node.tool_chain)}")
                            node.embedding = _build_term_vector(tokens, self._vector_dim)
                        self._stores[tenant_id][node.id] = node
                except Exception as ex:
                    logger.warning("Failed to hydrate tenant memory store: %s", ex)
        return self._stores[tenant_id]

    def _get_tenant_store(self, tenant_id: str) -> dict[str, EpisodicMemoryNode]:
        if tenant_id not in self._stores:
            self._stores[tenant_id] = {}
        return self._stores[tenant_id]

    def _compute_retention(self, node: EpisodicMemoryNode, now: float) -> float:
        """Calculate current retention score using Ebbinghaus exponential forgetting curve."""
        dt = max(0.0, now - node.last_accessed_at)
        stability_seconds = max(0.1, node.stability_score) * 86400.0
        return math.exp(-dt / stability_seconds)

    async def consolidate_trace(
        self, tenant_id: str, request: ConsolidationRequest
    ) -> ConsolidationResult:
        """Consolidate a ReAct execution trace into an episodic memory node."""
        store = await self._ensure_tenant_store(tenant_id)
        now = time.time()

        # Extract tool names and inspect self-healing behavior
        tool_chain: list[str] = []
        had_error = False
        error_tool: str | None = None
        recovering_tool: str | None = None

        for turn in request.turns:
            tools_called = turn.get("tools_called", [])
            for tc in tools_called:
                tname = tc if isinstance(tc, str) else tc.get("tool_name", "")
                if tname and tname not in tool_chain:
                    tool_chain.append(tname)

            obs = str(turn.get("observation", "")).lower()
            if "error" in obs or "fail" in obs or "exception" in obs:
                had_error = True
                if tools_called and not error_tool:
                    first_tool = tools_called[0]
                    error_tool = first_tool if isinstance(first_tool, str) else first_tool.get("tool_name", "")
            elif had_error and tools_called and not recovering_tool:
                rec_tool = tools_called[0]
                recovering_tool = rec_tool if isinstance(rec_tool, str) else rec_tool.get("tool_name", "")

        # Classify memory type
        if had_error and request.success and recovering_tool:
            memory_type = MemoryType.PROCEDURAL
            distilled_insight = (
                f"When task '{request.query[:80]}' encounters failure in {error_tool or 'initial tool'}, "
                f"self-healed and succeeded by executing {recovering_tool}."
            )
            importance = 0.85
        elif any("graph" in t or "triple" in t for t in tool_chain):
            memory_type = MemoryType.SEMANTIC
            tools_str = ", ".join(tool_chain) or "direct synthesis"
            distilled_insight = (
                f"Knowledge exploration for '{request.query[:80]}': resolved relationships via [{tools_str}]."
            )
            importance = 0.70
        else:
            memory_type = MemoryType.EPISODIC
            tools_str = ", ".join(tool_chain) if tool_chain else "reasoning"
            distilled_insight = (
                f"Successfully resolved '{request.query[:80]}' via [{tools_str}] across {len(request.turns)} turn(s)."
            )
            importance = 0.75 if (len(request.turns) >= 2 or len(tool_chain) >= 2) else 0.60

        # Build term vector embedding for query + distilled insight
        tokens = _tokenize(f"{request.query} {distilled_insight} {' '.join(tool_chain)}")
        embedding = _build_term_vector(tokens, self._vector_dim)

        node_id = f"mem_{uuid4().hex[:12]}"
        node = EpisodicMemoryNode(
            id=node_id,
            tenant_id=tenant_id,
            memory_type=memory_type,
            query=request.query,
            distilled_insight=distilled_insight,
            tool_chain=tool_chain,
            success=request.success,
            turns_count=len(request.turns),
            importance_score=importance,
            stability_score=1.0,
            last_accessed_at=now,
            access_count=1,
            created_at=now,
            embedding=embedding,
            metadata={"session_id": request.session_id, "had_error": had_error},
        )

        store[node_id] = node
        if self._repo:
            try:
                await self._repo.save_node(node)
            except Exception as ex:
                logger.warning("Cognitive memory persistence failed: %s", ex)

        return ConsolidationResult(
            node_id=node_id,
            distilled_insight=distilled_insight,
            importance_score=importance,
            tool_chain=tool_chain,
            memory_type=memory_type,
            status="consolidated",
        )

    async def retrieve_guidance(
        self, tenant_id: str, query: str, limit: int = 3, min_similarity: float = 0.65
    ) -> DistilledGuidance:
        """Retrieve relevant past experiences and format distilled guidance."""
        store = await self._ensure_tenant_store(tenant_id)
        if not store:
            return DistilledGuidance(relevant_nodes=[], guidance_prompt="", matched_tool_chains=[])

        now = time.time()
        query_tokens = _tokenize(query)
        query_vec = _build_term_vector(query_tokens, self._vector_dim)

        scored_results: list[tuple[float, MemorySearchResult]] = []

        for node in store.values():
            if not node.embedding:
                continue

            sim = _cosine_similarity(query_vec, node.embedding)
            retention = self._compute_retention(node, now)
            # Composite score weighting similarity higher while acknowledging memory decay
            composite_score = 0.75 * sim + 0.25 * retention

            if sim >= min_similarity or composite_score >= min_similarity:
                res = MemorySearchResult(
                    node=node,
                    similarity_score=round(sim, 4),
                    retention_score=round(retention, 4),
                )
                scored_results.append((composite_score, res))

        # Sort descending by composite score
        scored_results.sort(key=lambda x: x[0], reverse=True)
        top_matches = [item[1] for item in scored_results[:limit]]

        if not top_matches:
            return DistilledGuidance(relevant_nodes=[], guidance_prompt="", matched_tool_chains=[])

        # Reinforce stability for retrieved memories
        matched_tool_chains: list[list[str]] = []
        guidance_lines = ["DISTILLED EXPERIENCE FROM PRIOR SESSIONS:"]
        for match in top_matches:
            node = store[match.node.id]
            node.access_count += 1
            node.last_accessed_at = now
            # Ebbinghaus stability reinforcement formula
            node.stability_score = round(node.stability_score * 1.5 + 0.5, 3)

            if self._repo:
                try:
                    await self._repo.update_access(
                        tenant_id=tenant_id,
                        node_id=node.id,
                        stability_score=node.stability_score,
                        last_accessed_at=node.last_accessed_at,
                        access_count=node.access_count,
                    )
                except Exception as ex:
                    logger.debug("Cognitive memory update_access failed: %s", ex)

            matched_tool_chains.append(node.tool_chain)
            tools_repr = " -> ".join(node.tool_chain) if node.tool_chain else "analytical synthesis"
            guidance_lines.append(
                f"- [Strategy ({node.memory_type.value.upper()}, sim={match.similarity_score:.2f})]: "
                f"{node.distilled_insight} (Recommended Tool Path: {tools_repr})"
            )

        guidance_lines.append("Use these proven historical patterns to prevent redundant tool errors.")
        guidance_prompt = "\n".join(guidance_lines)

        return DistilledGuidance(
            relevant_nodes=top_matches,
            guidance_prompt=guidance_prompt,
            matched_tool_chains=matched_tool_chains,
        )

    async def list_memories(
        self,
        tenant_id: str,
        memory_type: MemoryType | None = None,
        query: str | None = None,
        limit: int = 50,
    ) -> list[EpisodicMemoryNode]:
        """List and search cognitive memories for a tenant."""
        store = await self._ensure_tenant_store(tenant_id)
        nodes = list(store.values())

        if memory_type:
            nodes = [n for n in nodes if n.memory_type == memory_type]

        if query:
            q_lower = query.lower()
            nodes = [
                n for n in nodes
                if q_lower in n.query.lower() or q_lower in n.distilled_insight.lower()
            ]

        nodes.sort(key=lambda x: x.last_accessed_at, reverse=True)
        return nodes[:limit]

    async def delete_memory(self, tenant_id: str, node_id: str) -> bool:
        """Delete a specific cognitive memory node."""
        store = await self._ensure_tenant_store(tenant_id)
        existed = node_id in store
        if existed:
            del store[node_id]
        if self._repo:
            try:
                await self._repo.delete_node(tenant_id, node_id)
            except Exception as ex:
                logger.warning("Cognitive memory persistent delete failed: %s", ex)
        return existed

    async def prune_memories(self, tenant_id: str, min_retention: float = 0.15) -> int:
        """Prune decayed memories whose Ebbinghaus retention falls below threshold."""
        store = await self._ensure_tenant_store(tenant_id)
        now = time.time()
        to_delete: list[str] = []

        for nid, node in store.items():
            retention = self._compute_retention(node, now)
            if retention < min_retention:
                to_delete.append(nid)

        for nid in to_delete:
            del store[nid]
            if self._repo:
                try:
                    await self._repo.delete_node(tenant_id, nid)
                except Exception:
                    pass

        return len(to_delete)

    async def get_stats(self, tenant_id: str) -> MemoryStats:
        """Retrieve aggregate memory statistics for a tenant."""
        store = await self._ensure_tenant_store(tenant_id)
        total = len(store)
        if total == 0:
            return MemoryStats()

        ep_count = sum(1 for n in store.values() if n.memory_type == MemoryType.EPISODIC)
        sem_count = sum(1 for n in store.values() if n.memory_type == MemoryType.SEMANTIC)
        proc_count = sum(1 for n in store.values() if n.memory_type == MemoryType.PROCEDURAL)
        avg_stab = sum(n.stability_score for n in store.values()) / total
        total_access = sum(n.access_count for n in store.values())

        return MemoryStats(
            total_memories=total,
            episodic_count=ep_count,
            semantic_count=sem_count,
            procedural_count=proc_count,
            avg_stability=round(avg_stab, 2),
            total_access_count=total_access,
        )
