import json
import uuid
from sqlalchemy import text
from src.adapters.database.connection import engine
from src.domain.abstractions.retrieval import SearchResult, SemanticCacheProvider


class PgSemanticCacheAdapter(SemanticCacheProvider):
    """SQLAlchemy-backed semantic cache manager implementing pgvector lookups."""

    async def get_cached_search(
        self,
        tenant_id: str,
        query_embedding: list[float],
    ) -> list[SearchResult] | None:
        async with engine.connect() as conn:
            # Set local tenant RLS context for select query
            await conn.execute(text("SET LOCAL app.current_tenant_id = :tenant_id"), {"tenant_id": tenant_id})
            res = await conn.execute(
                text(
                    """
                    SELECT search_results, (embedding <=> :embedding::vector) as distance FROM semantic_cache 
                    WHERE tenant_id = :tenant_id
                    AND expires_at > NOW()
                    ORDER BY embedding <=> :embedding::vector LIMIT 1
                    """
                ),
                {"tenant_id": tenant_id, "embedding": query_embedding}
            )
            row = res.fetchone()
            if row and row[1] is not None and row[1] < 0.01:
                cached_results_raw = row[0]
                results = []
                for item in cached_results_raw:
                    results.append(SearchResult(
                        chunk_id=item["chunk_id"],
                        document_id=item["document_id"],
                        content=item["content"],
                        score=item["score"],
                        metadata=item.get("metadata", {})
                    ))
                return results
        return None

    async def cache_search(
        self,
        tenant_id: str,
        query_text: str,
        query_embedding: list[float],
        results: list[SearchResult],
    ) -> None:
        results_serializable = []
        for r in results:
            results_serializable.append({
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "content": r.content,
                "score": r.score,
                "metadata": r.metadata
            })
            
        async with engine.begin() as conn:
            await conn.execute(text("SET LOCAL app.bypass_rls = 'true'"))
            await conn.execute(
                text(
                    """
                    INSERT INTO semantic_cache 
                    (cache_id, tenant_id, query_text, embedding, search_results, created_at, expires_at)
                    VALUES (:cache_id, :tenant_id, :query_text, :embedding::vector, :search_results, NOW(), NOW() + INTERVAL '24 hours')
                    """
                ),
                {
                    "cache_id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "query_text": query_text,
                    "embedding": query_embedding,
                    "search_results": results_serializable
                }
            )
