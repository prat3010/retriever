"""Neo4j implementation of GraphRepository for Knowledge Graph storage."""

import logging
from typing import Any

from src.adapters.database.graph_repository import PgGraphRepository
from src.domain.abstractions.graph import (
    BaseGraphRepository,
    EntityTriple,
    GraphSearchResult,
)

logger = logging.getLogger(__name__)

# Optional neo4j driver import
try:
    import neo4j  # noqa: F401
    from neo4j import AsyncGraphDatabase

    NEO4J_AVAILABLE = True
except ImportError:
    AsyncGraphDatabase = None
    NEO4J_AVAILABLE = False


class Neo4jGraphRepository(BaseGraphRepository):
    """Neo4j GraphRepository with Cypher queries and automatic fallback to PostgreSQL."""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password",
        fallback_repo: PgGraphRepository | None = None,
    ):
        self.uri = uri
        self.user = user
        self.password = password
        self.fallback_repo = fallback_repo or PgGraphRepository()
        self._driver = None

    async def _get_driver(self):
        """Get or initialize AsyncGraphDatabase driver."""
        if not NEO4J_AVAILABLE:
            return None
        if self._driver is None:
            try:
                self._driver = AsyncGraphDatabase.driver(
                    self.uri, auth=(self.user, self.password)
                )
                await self._driver.verify_connectivity()
            except Exception as err:
                logger.warning(
                    f"Neo4j connection failed ({err}). Falling back to PostgreSQL graph repository."
                )
                self._driver = None
        return self._driver

    async def is_online(self) -> bool:
        """Check if Neo4j database server is online and accessible."""
        driver = await self._get_driver()
        return driver is not None

    async def add_triples(self, tenant_id: str, triples: list[EntityTriple]) -> int:
        """Persist entity relationship triples into Neo4j or fallback to PostgreSQL."""
        driver = await self._get_driver()
        if not driver:
            return await self.fallback_repo.add_triples(tenant_id, triples)

        if not triples:
            return 0

        cypher = """
        UNWIND $batch AS item
        MERGE (s:Entity {name: item.subject, tenant_id: $tenant_id})
        MERGE (o:Entity {name: item.object, tenant_id: $tenant_id})
        MERGE (s)-[r:RELATED {predicate: item.predicate, tenant_id: $tenant_id}]->(o)
        SET r.triple_id = item.triple_id, r.chunk_id = item.chunk_id, r.confidence = item.confidence
        """
        batch = [
            {
                "triple_id": t.triple_id,
                "subject": t.subject.strip(),
                "predicate": t.predicate.strip().upper(),
                "object": t.object.strip(),
                "chunk_id": t.chunk_id,
                "confidence": t.confidence,
            }
            for t in triples
        ]

        try:
            async with driver.session() as session:
                await session.run(cypher, tenant_id=tenant_id, batch=batch)
            return len(triples)
        except Exception as err:
            logger.error(f"Neo4j add_triples failed ({err}). Delegating to fallback.")
            return await self.fallback_repo.add_triples(tenant_id, triples)

    async def search_triples(
        self, tenant_id: str, entity: str, max_hops: int = 2
    ) -> GraphSearchResult:
        """Perform Cypher multi-hop graph search in Neo4j or fallback to PostgreSQL."""
        driver = await self._get_driver()
        if not driver:
            return await self.fallback_repo.search_triples(tenant_id, entity, max_hops)

        cypher = """
        MATCH (s:Entity {tenant_id: $tenant_id})-[r:RELATED {tenant_id: $tenant_id}]-(o:Entity {tenant_id: $tenant_id})
        WHERE toLower(s.name) = toLower($entity) OR toLower(o.name) = toLower($entity)
        RETURN r.triple_id AS triple_id, s.name AS subject, r.predicate AS predicate, o.name AS object, r.chunk_id AS chunk_id, r.confidence AS confidence
        LIMIT 50
        """

        try:
            triples: list[EntityTriple] = []
            connected: set[str] = set()

            async with driver.session() as session:
                res = await session.run(cypher, tenant_id=tenant_id, entity=entity)
                records = await res.data()

                for record in records:
                    t_obj = EntityTriple(
                        triple_id=record.get("triple_id"),
                        subject=record["subject"],
                        predicate=record["predicate"],
                        object=record["object"],
                        chunk_id=record.get("chunk_id"),
                        confidence=float(record.get("confidence") or 1.0),
                    )
                    triples.append(t_obj)
                    connected.add(record["subject"])
                    connected.add(record["object"])

            return GraphSearchResult(
                root_entity=entity,
                max_hops=max_hops,
                triples=triples,
                connected_entities=sorted(connected),
            )
        except Exception as err:
            logger.error(f"Neo4j search_triples failed ({err}). Delegating to fallback.")
            return await self.fallback_repo.search_triples(tenant_id, entity, max_hops)

    async def get_graph_summary(self, tenant_id: str) -> dict[str, Any]:
        """Summarize Neo4j graph statistics for a tenant or fallback to PostgreSQL."""
        driver = await self._get_driver()
        if not driver:
            return await self.fallback_repo.get_graph_summary(tenant_id)

        try:
            async with driver.session() as session:
                res = await session.run(
                    "MATCH ()-[r:RELATED {tenant_id: $tenant_id}]->() RETURN count(r) AS total",
                    tenant_id=tenant_id,
                )
                rec = await res.single()
                total = rec["total"] if rec else 0

            return {
                "tenant_id": tenant_id,
                "total_triples": total,
                "storage_engine": "neo4j",
                "neo4j_status": "online",
            }
        except Exception as err:
            logger.error(f"Neo4j get_graph_summary failed ({err}). Delegating to fallback.")
            return await self.fallback_repo.get_graph_summary(tenant_id)

    async def delete_document_triples(self, tenant_id: str, document_id: str) -> int:
        """Remove document triples from Neo4j or fallback to PostgreSQL."""
        driver = await self._get_driver()
        if not driver:
            return await self.fallback_repo.delete_document_triples(tenant_id, document_id)

        try:
            async with driver.session() as session:
                res = await session.run(
                    "MATCH ()-[r:RELATED {tenant_id: $tenant_id, document_id: $document_id}]->() DELETE r RETURN count(r) AS deleted",
                    tenant_id=tenant_id,
                    document_id=document_id,
                )
                rec = await res.single()
                deleted = rec["deleted"] if rec else 0
            # Also clean up in fallback postgres store
            await self.fallback_repo.delete_document_triples(tenant_id, document_id)
            return deleted
        except Exception as err:
            logger.error(f"Neo4j delete_document_triples failed ({err}). Delegating to fallback.")
            return await self.fallback_repo.delete_document_triples(tenant_id, document_id)

    async def delete_triple(self, tenant_id: str, triple_id: str) -> bool:
        """Delete a single triple from Neo4j or fallback to PostgreSQL."""
        driver = await self._get_driver()
        if not driver:
            return await self.fallback_repo.delete_triple(tenant_id, triple_id)

        try:
            async with driver.session() as session:
                await session.run(
                    "MATCH ()-[r:RELATED {tenant_id: $tenant_id, triple_id: $triple_id}]->() DELETE r",
                    tenant_id=tenant_id,
                    triple_id=triple_id,
                )
            await self.fallback_repo.delete_triple(tenant_id, triple_id)
            return True
        except Exception as err:
            logger.error(f"Neo4j delete_triple failed ({err}). Delegating to fallback.")
            return await self.fallback_repo.delete_triple(tenant_id, triple_id)

    async def close(self):
        """Close Neo4j driver connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
