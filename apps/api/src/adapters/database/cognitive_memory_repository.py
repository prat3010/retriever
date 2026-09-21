"""PostgreSQL Database Adapter for Cognitive Agent Memory Persistence (M108).

Enforces strict tenant isolation via PostgreSQL Row-Level Security (RLS).
Persists and retrieves episodic, semantic, and procedural memory nodes.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select, update

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import CognitiveMemoryDb
from src.domain.abstractions.memory import (
    CognitiveMemoryRepositoryProtocol,
    EpisodicMemoryNode,
    MemoryType,
)

logger = logging.getLogger(__name__)


class PgCognitiveMemoryRepository(CognitiveMemoryRepositoryProtocol):
    """PostgreSQL implementation of CognitiveMemoryRepositoryProtocol."""

    async def save_node(self, node: EpisodicMemoryNode) -> None:
        """Persist an episodic memory node with tenant isolation."""
        try:
            tenant_uuid = UUID(node.tenant_id)
        except (ValueError, TypeError):
            logger.warning("Invalid tenant UUID '%s' for memory save", node.tenant_id)
            return

        async with tenant_session(node.tenant_id) as session:
            db_node = CognitiveMemoryDb(
                id=node.id,
                tenant_id=tenant_uuid,
                memory_type=node.memory_type.value if hasattr(node.memory_type, "value") else str(node.memory_type),
                query=node.query,
                distilled_insight=node.distilled_insight,
                tool_chain=node.tool_chain,
                success=node.success,
                turns_count=node.turns_count,
                importance_score=node.importance_score,
                stability_score=node.stability_score,
                last_accessed_at=datetime.fromtimestamp(node.last_accessed_at, tz=UTC),
                access_count=node.access_count,
                embedding=node.embedding,
                meta_data=node.metadata,
                created_at=datetime.fromtimestamp(node.created_at, tz=UTC),
            )
            session.add(db_node)
            await session.commit()

    async def get_nodes(
        self, tenant_id: str, memory_type: MemoryType | None = None
    ) -> list[EpisodicMemoryNode]:
        """Fetch all stored memory nodes for a tenant."""
        try:
            tenant_uuid = UUID(tenant_id)
        except (ValueError, TypeError):
            return []

        async with tenant_session(tenant_id) as session:
            stmt = select(CognitiveMemoryDb).where(CognitiveMemoryDb.tenant_id == tenant_uuid)
            if memory_type is not None:
                m_type = memory_type.value if hasattr(memory_type, "value") else str(memory_type)
                stmt = stmt.where(CognitiveMemoryDb.memory_type == m_type)

            result = await session.execute(stmt)
            rows = result.scalars().all()

            nodes: list[EpisodicMemoryNode] = []
            for row in rows:
                try:
                    mem_t = MemoryType(row.memory_type)
                except ValueError:
                    mem_t = MemoryType.EPISODIC

                last_acc = row.last_accessed_at.timestamp() if row.last_accessed_at else 0.0
                created = row.created_at.timestamp() if row.created_at else 0.0

                node = EpisodicMemoryNode(
                    id=row.id,
                    tenant_id=str(row.tenant_id),
                    memory_type=mem_t,
                    query=row.query,
                    distilled_insight=row.distilled_insight,
                    tool_chain=row.tool_chain or [],
                    success=row.success,
                    turns_count=row.turns_count,
                    importance_score=row.importance_score,
                    stability_score=row.stability_score,
                    last_accessed_at=last_acc,
                    access_count=row.access_count,
                    created_at=created,
                    embedding=row.embedding,
                    metadata=row.meta_data or {},
                )
                nodes.append(node)
            return nodes

    async def delete_node(self, tenant_id: str, node_id: str) -> bool:
        """Delete a memory node by ID."""
        try:
            tenant_uuid = UUID(tenant_id)
        except (ValueError, TypeError):
            return False

        async with tenant_session(tenant_id) as session:
            stmt = (
                delete(CognitiveMemoryDb)
                .where(CognitiveMemoryDb.id == node_id)
                .where(CognitiveMemoryDb.tenant_id == tenant_uuid)
            )
            result = await session.execute(stmt)
            await session.commit()
            return (result.rowcount or 0) > 0

    async def update_access(
        self,
        tenant_id: str,
        node_id: str,
        stability_score: float,
        last_accessed_at: float,
        access_count: int,
    ) -> None:
        """Update node access telemetry and reinforced stability score."""
        try:
            tenant_uuid = UUID(tenant_id)
        except (ValueError, TypeError):
            return

        async with tenant_session(tenant_id) as session:
            dt = datetime.fromtimestamp(last_accessed_at, tz=UTC)
            stmt = (
                update(CognitiveMemoryDb)
                .where(CognitiveMemoryDb.id == node_id)
                .where(CognitiveMemoryDb.tenant_id == tenant_uuid)
                .values(
                    stability_score=stability_score,
                    last_accessed_at=dt,
                    access_count=access_count,
                )
            )
            await session.execute(stmt)
            await session.commit()
