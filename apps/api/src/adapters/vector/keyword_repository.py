from sqlalchemy import text

from src.adapters.database.connection import tenant_session
from src.adapters.vector.filter_builder import build_filter_clause, rows_to_search_results
from src.domain.abstractions.retrieval import KeywordSearchProvider, MetadataFilter, SearchResult


class PgKeywordSearchAdapter(KeywordSearchProvider):

    async def search_keywords(
        self,
        tenant_id: str,
        query_text: str,
        top_k: int,
        filters: list[MetadataFilter],
        tags: list[str],
    ) -> list[SearchResult]:
        filter_clause, filter_params, join_clause = build_filter_clause(filters, tags, "dc")

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
                    {join_clause}
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

        return rows_to_search_results(rows)
