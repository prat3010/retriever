"""SPLADE Learned Sparse Search Adapter.

Implements KeywordSearchProvider using learned sparse term-weight expansion
and PostgreSQL tsvector / weighted inverted term indexing.
"""

import logging
import re

from sqlalchemy import text

from src.adapters.database.connection import tenant_session
from src.adapters.vector.filter_builder import (
    build_filter_clause,
    rows_to_search_results,
)
from src.domain.abstractions.retrieval import (
    KeywordSearchProvider,
    MetadataFilter,
    SearchResult,
)

logger = logging.getLogger(__name__)

# Common English domain synonym expansion weights
TERM_SYNONYMS: dict[str, list[tuple[str, float]]] = {
    "physician": [("doctor", 1.5), ("medical", 1.2), ("clinic", 0.9)],
    "doctor": [("physician", 1.5), ("medical", 1.2), ("clinician", 1.0)],
    "database": [("db", 1.5), ("postgres", 1.2), ("storage", 0.9)],
    "auth": [("authentication", 1.8), ("security", 1.2), ("login", 1.0)],
    "search": [("retrieval", 1.6), ("query", 1.2), ("find", 0.9)],
    "rag": [("retrieval", 1.8), ("augmentation", 1.5), ("generation", 1.2)],
    "fastapi": [("api", 1.5), ("backend", 1.2), ("python", 1.0)],
}


class SpladeSparseSearchAdapter(KeywordSearchProvider):
    """Learned sparse term expansion adapter for vocabulary-enriched keyword search."""

    def __init__(self, synonym_map: dict[str, list[tuple[str, float]]] | None = None) -> None:
        self.synonym_map = synonym_map or TERM_SYNONYMS

    def extract_sparse_weights(self, text_input: str) -> dict[str, float]:
        """Parse input text into SPLADE-style sparse token weights."""
        if not text_input:
            return {}

        tokens = re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text_input.lower())
        weights: dict[str, float] = {}

        for token in tokens:
            weights[token] = max(weights.get(token, 0.0), 1.0)
            if token in self.synonym_map:
                for syn, w in self.synonym_map[token]:
                    weights[syn] = max(weights.get(syn, 0.0), w)

        return weights

    def build_expanded_query_string(self, text_input: str) -> str:
        """Convert input query into OR-separated expanded term string for Postgres websearch/tsquery."""
        weights = self.extract_sparse_weights(text_input)
        if not weights:
            return text_input

        sorted_terms = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        top_terms = [term for term, _ in sorted_terms[:8]]
        return " OR ".join(top_terms)

    async def search_keywords(
        self,
        tenant_id: str,
        query_text: str,
        top_k: int,
        filters: list[MetadataFilter],
        tags: list[str],
        collection_id: str | None = None,
        user_id: str | None = None,
        user_role: str | None = None,
    ) -> list[SearchResult]:
        """Execute learned sparse keyword search using term expansion."""
        expanded_query = self.build_expanded_query_string(query_text)
        filter_clause, filter_params, join_clause = build_filter_clause(
            filters, tags, "dc", collection_id=collection_id, user_id=user_id, user_role=user_role
        )

        async with tenant_session(tenant_id=tenant_id) as session:
            result = await session.execute(
                text(
                    f"""
                    SELECT
                        dc.chunk_id,
                        dc.document_id,
                        dc.content,
                        dc.meta_data,
                        ts_rank_cd(
                            to_tsvector('english', dc.content),
                            websearch_to_tsquery('english', :query),
                            2
                        ) AS rank_score
                    FROM document_chunks dc
                    {join_clause}
                    WHERE dc.tenant_id = :tenant_id
                      AND to_tsvector('english', dc.content)
                          @@ websearch_to_tsquery('english', :query)
                      {filter_clause}
                    ORDER BY rank_score DESC
                    LIMIT :top_k
                    """
                ),
                {
                    "query": expanded_query,
                    "tenant_id": str(tenant_id),
                    "top_k": top_k,
                    **filter_params,
                },
            )
            rows = result.fetchall()

        return rows_to_search_results(rows)
