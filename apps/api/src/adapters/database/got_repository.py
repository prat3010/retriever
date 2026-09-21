"""PostgreSQL Database Adapter for Graph-of-Thoughts Persistence (M123).

Enforces strict tenant isolation via PostgreSQL Row-Level Security (RLS).
Persists, updates, and reconstitutes GoTGraph DAGs and their thought vertices.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import GoTGraphDb, GoTThoughtDb
from src.domain.abstractions.got_planner import (
    GoTEdge,
    GoTEdgeType,
    GoTGraph,
    GoTRepositoryProtocol,
    GoTThoughtNode,
    GoTThoughtStatus,
    GoTThoughtType,
)

logger = logging.getLogger(__name__)


class PgGoTRepository(GoTRepositoryProtocol):
    """PostgreSQL implementation of GoTRepositoryProtocol."""

    async def save_graph(self, graph: GoTGraph) -> None:
        """Persist or update a GoTGraph and all its thought vertices."""
        try:
            tenant_uuid = UUID(graph.tenant_id)
        except (ValueError, TypeError):
            logger.warning("Invalid tenant UUID '%s' for GoT graph save", graph.tenant_id)
            return

        async with tenant_session(graph.tenant_id) as session:
            # 1. Upsert Graph record
            existing_graph = await session.get(GoTGraphDb, graph.graph_id)
            if not existing_graph:
                db_graph = GoTGraphDb(
                    graph_id=graph.graph_id,
                    tenant_id=tenant_uuid,
                    query=graph.query,
                    root_id=graph.root_id,
                    is_converged=graph.is_converged,
                    best_score=graph.best_score,
                    optimal_path=graph.optimal_path,
                    total_tokens=graph.total_tokens,
                    total_latency_ms=graph.total_latency_ms,
                    created_at=datetime.fromtimestamp(graph.created_at, tz=UTC),
                    updated_at=datetime.fromtimestamp(graph.updated_at, tz=UTC),
                )
                session.add(db_graph)
            else:
                existing_graph.is_converged = graph.is_converged
                existing_graph.best_score = graph.best_score
                existing_graph.optimal_path = graph.optimal_path
                existing_graph.total_tokens = graph.total_tokens
                existing_graph.total_latency_ms = graph.total_latency_ms
                existing_graph.updated_at = datetime.fromtimestamp(graph.updated_at, tz=UTC)

            # 2. Upsert thought vertices
            for node in graph.nodes.values():
                existing_thought = await session.get(GoTThoughtDb, node.id)
                t_type = node.thought_type.value if hasattr(node.thought_type, "value") else str(node.thought_type)
                t_status = node.status.value if hasattr(node.status, "value") else str(node.status)

                if not existing_thought:
                    db_thought = GoTThoughtDb(
                        thought_id=node.id,
                        graph_id=graph.graph_id,
                        tenant_id=tenant_uuid,
                        prompt=node.prompt,
                        content=node.content,
                        thought_type=t_type,
                        status=t_status,
                        parent_ids=node.parent_ids,
                        child_ids=node.child_ids,
                        score=node.score,
                        grounding_score=node.grounding_score,
                        coherence_score=node.coherence_score,
                        constraint_score=node.constraint_score,
                        token_cost=node.token_cost,
                        latency_ms=node.latency_ms,
                        iteration_depth=node.iteration_depth,
                        is_optimal_path=node.is_optimal_path,
                        meta_data=node.metadata,
                        created_at=datetime.fromtimestamp(node.created_at, tz=UTC),
                    )
                    session.add(db_thought)
                else:
                    existing_thought.content = node.content
                    existing_thought.status = t_status
                    existing_thought.score = node.score
                    existing_thought.grounding_score = node.grounding_score
                    existing_thought.coherence_score = node.coherence_score
                    existing_thought.constraint_score = node.constraint_score
                    existing_thought.token_cost = node.token_cost
                    existing_thought.latency_ms = node.latency_ms
                    existing_thought.is_optimal_path = node.is_optimal_path
                    existing_thought.child_ids = node.child_ids

            await session.commit()

    async def get_graph(self, tenant_id: str, graph_id: str) -> GoTGraph | None:
        """Fetch and reconstitute a GoTGraph by ID."""
        try:
            tenant_uuid = UUID(tenant_id)
        except (ValueError, TypeError):
            return None

        async with tenant_session(tenant_id) as session:
            stmt = select(GoTGraphDb).where(
                GoTGraphDb.graph_id == graph_id,
                GoTGraphDb.tenant_id == tenant_uuid,
            )
            res = await session.execute(stmt)
            db_graph = res.scalar_one_or_none()
            if not db_graph:
                return None

            # Fetch thoughts
            t_stmt = select(GoTThoughtDb).where(GoTThoughtDb.graph_id == graph_id)
            t_res = await session.execute(t_stmt)
            db_thoughts = t_res.scalars().all()

            nodes: dict[str, GoTThoughtNode] = {}
            edges: list[GoTEdge] = []

            for dt in db_thoughts:
                try:
                    ttype = GoTThoughtType(dt.thought_type)
                except ValueError:
                    ttype = GoTThoughtType.GENERATION

                try:
                    tstatus = GoTThoughtStatus(dt.status)
                except ValueError:
                    tstatus = GoTThoughtStatus.SCORED

                node = GoTThoughtNode(
                    id=dt.thought_id,
                    tenant_id=str(dt.tenant_id),
                    prompt=dt.prompt,
                    content=dt.content,
                    thought_type=ttype,
                    status=tstatus,
                    parent_ids=dt.parent_ids or [],
                    child_ids=dt.child_ids or [],
                    score=dt.score,
                    grounding_score=dt.grounding_score,
                    coherence_score=dt.coherence_score,
                    constraint_score=dt.constraint_score,
                    token_cost=dt.token_cost,
                    latency_ms=dt.latency_ms,
                    iteration_depth=dt.iteration_depth,
                    is_optimal_path=dt.is_optimal_path,
                    metadata=dt.meta_data or {},
                    created_at=dt.created_at.timestamp() if dt.created_at else 0.0,
                )
                nodes[node.id] = node

                # Reconstruct derivation edges from parents
                for pid in node.parent_ids:
                    edges.append(
                        GoTEdge(
                            source_id=pid,
                            target_id=node.id,
                            edge_type=GoTEdgeType.AGGREGATION if len(node.parent_ids) > 1 else GoTEdgeType.DERIVATION,
                            weight=node.score,
                        )
                    )

            c_at = db_graph.created_at.timestamp() if db_graph.created_at else 0.0
            u_at = db_graph.updated_at.timestamp() if db_graph.updated_at else 0.0

            return GoTGraph(
                graph_id=db_graph.graph_id,
                tenant_id=str(db_graph.tenant_id),
                query=db_graph.query,
                root_id=db_graph.root_id,
                nodes=nodes,
                edges=edges,
                optimal_path=db_graph.optimal_path or [],
                best_score=db_graph.best_score,
                is_converged=db_graph.is_converged,
                total_tokens=db_graph.total_tokens,
                total_latency_ms=db_graph.total_latency_ms,
                created_at=c_at,
                updated_at=u_at,
            )

    async def list_graphs(self, tenant_id: str, limit: int = 50) -> list[GoTGraph]:
        """List all stored GoT graphs for a tenant."""
        try:
            tenant_uuid = UUID(tenant_id)
        except (ValueError, TypeError):
            return []

        async with tenant_session(tenant_id) as session:
            stmt = (
                select(GoTGraphDb)
                .where(GoTGraphDb.tenant_id == tenant_uuid)
                .order_by(GoTGraphDb.created_at.desc())
                .limit(limit)
            )
            res = await session.execute(stmt)
            graphs: list[GoTGraph] = []
            for g in res.scalars().all():
                full_graph = await self.get_graph(tenant_id, g.graph_id)
                if full_graph:
                    graphs.append(full_graph)
            return graphs
