"""PostgreSQL BM25 Keyword Search Adapter.

Implements the KeywordSearchProvider port using PostgreSQL full-text search
with tsvector/tsquery and ts_rank scoring. Enforces RLS via tenant_session.
"""

from typing import Any

from sqlalchemy import text

from src.adapters.database.connection import tenant_session
from src.domain.abstractions.retrieval import KeywordSearchProvider, SearchResult


class PgKeywordSearchAdapter(KeywordSearchProvider):
    """Concrete adapter executing BM25-style keyword searches via PostgreSQL."""

    @staticmethod
    def _build_meta_filter(
        filters: dict[str, Any], alias: str
    ) -> tuple[str, dict[str, Any]]:
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

    async def search_keywords(
        self,
        tenant_id: str,
        query_text: str,
        top_k: int,
        filters: dict[str, Any],
    ) -> list[SearchResult]:
        """Query document_chunks using full-text search with ts_rank scoring."""
        filter_clause, filter_params = self._build_meta_filter(filters, "dc")

        async with tenant_session(tenant_id=tenant_id) as session:
            result = await session.execute(
                text(
                    f"""
                    SELECT
                        dc.chunk_id,
                        dc.document_id,
                        dc.content,
                        dc.meta_data,
                        ts_rank(
                            to_tsvector('english', dc.content),
                            plainto_tsquery('english', :query)
                        ) AS rank_score
                    FROM document_chunks dc
                    WHERE dc.tenant_id = :tenant_id
                      AND to_tsvector('english', dc.content)
                          @@ plainto_tsquery('english', :query)
                      {filter_clause}
                    ORDER BY rank_score DESC
                    LIMIT :top_k
                    """
                ),
                {
                    "query": query_text,
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
