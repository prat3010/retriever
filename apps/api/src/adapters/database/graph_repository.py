"""PostgreSQL implementation of GraphRepository for Knowledge Graph storage."""

import uuid
from typing import Any

from sqlalchemy import delete, func, select, text

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import DocumentChunkDb, GraphTripleDb
from src.domain.abstractions.graph import (
    BaseGraphRepository,
    EntityTriple,
    GraphSearchResult,
)


class PgGraphRepository(BaseGraphRepository):
    """PostgreSQL-backed GraphRepository using relational tables and Recursive CTEs."""

    async def add_triples(self, tenant_id: str, triples: list[EntityTriple]) -> int:
        """Persist a list of entity relationship triples for a tenant."""
        if not triples:
            return 0

        created_count = 0
        async with tenant_session(tenant_id=tenant_id) as session:
            for t in triples:
                chunk_uuid = uuid.UUID(t.chunk_id) if t.chunk_id else None
                model = GraphTripleDb(
                    triple_id=uuid.UUID(t.triple_id) if t.triple_id else uuid.uuid4(),
                    tenant_id=uuid.UUID(tenant_id),
                    subject=t.subject.strip(),
                    predicate=t.predicate.strip().upper(),
                    object=t.object.strip(),
                    chunk_id=chunk_uuid,
                    confidence=t.confidence,
                    meta_data=t.metadata,
                )
                session.add(model)
                created_count += 1
            await session.commit()
        return created_count

    async def search_triples(
        self, tenant_id: str, entity: str, max_hops: int = 2
    ) -> GraphSearchResult:
        """Perform multi-hop graph traversal starting from a root entity using PostgreSQL Recursive SQL."""
        clean_entity = entity.strip().lower()
        if not clean_entity:
            return GraphSearchResult(root_entity=entity, max_hops=max_hops)

        # SQL Recursive CTE to traverse graph edges up to max_hops
        cte_query = text(
            """
            WITH RECURSIVE graph_cte AS (
                -- Base case: 1-hop connections from entity
                SELECT triple_id, tenant_id, subject, predicate, object, chunk_id, confidence, meta_data, 1 AS depth
                FROM graph_triples
                WHERE tenant_id = :tenant_id
                  AND (LOWER(subject) = :entity OR LOWER(object) = :entity)

                UNION ALL

                -- Recursive step: n-hop connections
                SELECT gt.triple_id, gt.tenant_id, gt.subject, gt.predicate, gt.object, gt.chunk_id, gt.confidence, gt.meta_data, gc.depth + 1
                FROM graph_triples gt
                INNER JOIN graph_cte gc ON (
                    (LOWER(gt.subject) = LOWER(gc.object) OR LOWER(gt.object) = LOWER(gc.subject))
                )
                WHERE gt.tenant_id = :tenant_id
                  AND gc.depth < :max_hops
            )
            SELECT DISTINCT triple_id, subject, predicate, object, chunk_id, confidence, meta_data
            FROM graph_cte;
            """
        )

        triples: list[EntityTriple] = []
        connected: set[str] = set()

        async with tenant_session(tenant_id=tenant_id) as session:
            result = await session.execute(
                cte_query,
                {
                    "tenant_id": uuid.UUID(tenant_id),
                    "entity": clean_entity,
                    "max_hops": max_hops,
                },
            )
            rows = result.fetchall()

            for row in rows:
                t_obj = EntityTriple(
                    triple_id=str(row.triple_id),
                    subject=row.subject,
                    predicate=row.predicate,
                    object=row.object,
                    chunk_id=str(row.chunk_id) if row.chunk_id else None,
                    confidence=float(row.confidence),
                    metadata=dict(row.meta_data) if row.meta_data else {},
                )
                triples.append(t_obj)
                connected.add(row.subject)
                connected.add(row.object)

        return GraphSearchResult(
            root_entity=entity,
            max_hops=max_hops,
            triples=triples,
            connected_entities=sorted(connected),
        )

    async def get_graph_summary(self, tenant_id: str) -> dict[str, Any]:
        """Summarize knowledge graph statistics for a tenant."""
        async with tenant_session(tenant_id=tenant_id) as session:
            count_stmt = select(func.count(GraphTripleDb.triple_id)).where(
                GraphTripleDb.tenant_id == uuid.UUID(tenant_id)
            )
            total_triples = (await session.execute(count_stmt)).scalar() or 0

            # Count distinct subjects and objects
            sub_stmt = select(func.count(func.distinct(GraphTripleDb.subject))).where(
                GraphTripleDb.tenant_id == uuid.UUID(tenant_id)
            )
            total_subjects = (await session.execute(sub_stmt)).scalar() or 0

            obj_stmt = select(func.count(func.distinct(GraphTripleDb.object))).where(
                GraphTripleDb.tenant_id == uuid.UUID(tenant_id)
            )
            total_objects = (await session.execute(obj_stmt)).scalar() or 0

        return {
            "tenant_id": tenant_id,
            "total_triples": total_triples,
            "unique_entities": max(total_subjects, total_objects),
            "storage_engine": "postgres",
        }

    async def delete_document_triples(self, tenant_id: str, document_id: str) -> int:
        """Remove all entity triples associated with a specific document."""
        async with tenant_session(tenant_id=tenant_id) as session:
            subquery = select(DocumentChunkDb.chunk_id).where(
                DocumentChunkDb.tenant_id == uuid.UUID(tenant_id),
                DocumentChunkDb.document_id == uuid.UUID(document_id),
            )
            stmt = delete(GraphTripleDb).where(
                GraphTripleDb.tenant_id == uuid.UUID(tenant_id),
                GraphTripleDb.chunk_id.in_(subquery),
            )
            res = await session.execute(stmt)
            await session.commit()
            return res.rowcount or 0

    async def delete_triple(self, tenant_id: str, triple_id: str) -> bool:
        """Delete a single triple by ID."""
        async with tenant_session(tenant_id=tenant_id) as session:
            stmt = delete(GraphTripleDb).where(
                GraphTripleDb.tenant_id == uuid.UUID(tenant_id),
                GraphTripleDb.triple_id == uuid.UUID(triple_id),
            )
            res = await session.execute(stmt)
            await session.commit()
            return (res.rowcount or 0) > 0
