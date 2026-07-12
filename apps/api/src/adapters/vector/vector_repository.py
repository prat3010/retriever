"""pgvector Cosine Similarity Search Adapter.

Implements the VectorSearchProvider port using PostgreSQL pgvector extension
with cosine distance operator (<=>). Enforces RLS via tenant_session.
"""

from typing import Any

from sqlalchemy import text

from src.adapters.database.connection import tenant_session
from src.domain.abstractions.retrieval import SearchResult, VectorSearchProvider


class PgVectorSearchAdapter(VectorSearchProvider):
    """Concrete adapter executing cosine similarity searches against pgvector."""

    @staticmethod
    def _build_meta_filter(
        filters: dict[str, Any], alias: str
    ) -> tuple[str, dict[str, Any]]:
        """Build SQL filter clause and parameters from metadata key-value pairs.

        Supports exact match for scalars (->> operator) and ANY-element match
        for list values (?| operator) against the JSONB meta_data column.
        """
        if not filters:
            return "", {}

        conditions: list[str] = []
        params: dict[str, Any] = {}
        for i, (key, value) in enumerate(filters.items()):
            param_key = f"meta_val_{i}"
            if isinstance(value, list):
                conditions.append(
                    f"{alias}.meta_data -> '{key}' ?| :{param_key}"
                )
                params[param_key] = [str(v) for v in value]
            else:
                conditions.append(
                    f"{alias}.meta_data ->> '{key}' = :{param_key}"
                )
                params[param_key] = str(value)

        return " AND " + " AND ".join(conditions), params

    async def search_similar(
        self,
        tenant_id: str,
        embedding: list[float],
        top_k: int,
        filters: dict[str, Any],
    ) -> list[SearchResult]:
        """Query vector_records using cosine distance, joining document_chunks."""
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

        filter_clause, filter_params = self._build_meta_filter(filters, "dc")

        async with tenant_session(tenant_id=tenant_id) as session:
            result = await session.execute(
                text(
                    f"""
                    SELECT
                        vr.chunk_id,
                        dc.document_id,
                        dc.content,
                        dc.meta_data,
                        1 - (vr.embedding <=> :query_vec::vector) AS similarity_score
                    FROM vector_records vr
                    JOIN document_chunks dc ON vr.chunk_id = dc.chunk_id
                    WHERE vr.tenant_id = :tenant_id
                    {filter_clause}
                    ORDER BY vr.embedding <=> :query_vec::vector
                    LIMIT :top_k
                    """
                ),
                {
                    "query_vec": embedding_str,
                    "tenant_id": str(tenant_id),
                    "top_k": top_k,
                    **filter_params,
                },
            )
            rows = result.fetchall()

        return [
            SearchResult(
                chunk_id=str(row[0]),
                document_id=str(row[1]),
                content=row[2],
                score=float(row[4]),
                metadata=row[3] if isinstance(row[3], dict) else {},
            )
            for row in rows
        ]
