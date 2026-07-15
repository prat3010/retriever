from sqlalchemy import text

from src.adapters.database.connection import tenant_session
from src.adapters.vector.filter_builder import build_filter_clause, rows_to_search_results
from src.domain.abstractions.retrieval import MetadataFilter, SearchResult, VectorSearchProvider


class PgVectorSearchAdapter(VectorSearchProvider):

    async def search_similar(
        self,
        tenant_id: str,
        embedding: list[float],
        top_k: int,
        filters: list[MetadataFilter],
        tags: list[str],
    ) -> list[SearchResult]:
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

        filter_clause, filter_params, join_clause = build_filter_clause(filters, tags, "dc")

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
                    {join_clause}
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

        return rows_to_search_results(rows)
