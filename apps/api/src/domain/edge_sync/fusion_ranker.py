"""Edge Search Fusion Ranker Domain Service (M98).

Implements pure domain Reciprocal Rank Fusion (RRF) and linear score calibration
to combine local embedded vector cosine similarity with FTS5 BM25 match scores.
Zero framework or infrastructure imports (strictly Hexagonal).
"""

from typing import Any

from src.domain.abstractions.edge_sync import EdgeSearchResultItem


class EdgeFusionRanker:
    """Pure domain ranker combining vector similarity and full-text keyword scores."""

    def __init__(self, rrf_k: int = 60) -> None:
        self.rrf_k = rrf_k

    def fuse_results(
        self,
        vector_candidates: list[dict[str, Any]] | None = None,
        keyword_candidates: list[dict[str, Any]] | None = None,
        alpha: float = 0.5,
        top_k: int = 5,
        vector_results: list[dict[str, Any]] | None = None,
        fts_results: list[dict[str, Any]] | None = None,
        use_rrf: bool = True,
    ) -> list[EdgeSearchResultItem]:
        """Fuse vector and keyword candidate sets into a single ranked list.

        Args:
            vector_candidates: Ranked list from vector search (highest cosine first).
            keyword_candidates: Ranked list from FTS5 keyword search (highest BM25 first).
            alpha: Blend weight (0.0 = pure keyword, 1.0 = pure vector, 0.5 = hybrid).
            top_k: Maximum number of merged results to return.
            vector_results: Alias for vector_candidates.
            fts_results: Alias for keyword_candidates.
            use_rrf: Use Reciprocal Rank Fusion if True, else linear blend.
        """
        vecs = vector_candidates if vector_candidates is not None else (vector_results or [])
        kws = keyword_candidates if keyword_candidates is not None else (fts_results or [])

        all_chunk_ids: set[str] = set()
        chunk_map: dict[str, dict[str, Any]] = {}

        # Record ranks
        vector_ranks: dict[str, int] = {}
        vector_scores: dict[str, float] = {}
        for rank, item in enumerate(vecs):
            c_id = item["chunk_id"]
            vector_ranks[c_id] = rank + 1
            vector_scores[c_id] = float(item.get("vector_score", item.get("score", 0.0)))
            all_chunk_ids.add(c_id)
            if c_id not in chunk_map:
                chunk_map[c_id] = item

        keyword_ranks: dict[str, int] = {}
        keyword_scores: dict[str, float] = {}
        for rank, item in enumerate(kws):
            c_id = item["chunk_id"]
            keyword_ranks[c_id] = rank + 1
            keyword_scores[c_id] = float(item.get("fts_score", item.get("bm25_score", item.get("score", 0.0))))
            all_chunk_ids.add(c_id)
            if c_id not in chunk_map:
                chunk_map[c_id] = item

        # Calculate combined scores
        scored_items: list[EdgeSearchResultItem] = []
        for c_id in all_chunk_ids:
            v_rank = vector_ranks.get(c_id, 1000)
            k_rank = keyword_ranks.get(c_id, 1000)

            v_score = vector_scores.get(c_id, 0.0)
            k_score = keyword_scores.get(c_id, 0.0)

            in_vec = c_id in vector_ranks
            in_kw = c_id in keyword_ranks

            if in_vec and in_kw:
                match_type = "hybrid"
            elif in_vec:
                match_type = "vector"
            else:
                match_type = "bm25"

            if use_rrf:
                rrf_score = (alpha * (1.0 / (self.rrf_k + v_rank))) + ((1.0 - alpha) * (1.0 / (self.rrf_k + k_rank)))
                final_score = rrf_score
            else:
                final_score = (alpha * v_score) + ((1.0 - alpha) * k_score)

            raw_item = chunk_map[c_id]
            scored_items.append(
                EdgeSearchResultItem(
                    chunk_id=c_id,
                    document_id=raw_item.get("document_id", ""),
                    content=raw_item.get("content", ""),
                    score=round(final_score, 6),
                    vector_score=round(v_score, 4),
                    bm25_score=round(k_score, 4),
                    match_type=match_type,
                    meta_data=raw_item.get("meta_data", {}),
                )
            )

        # Sort descending by composite score
        scored_items.sort(key=lambda x: x.score, reverse=True)
        return scored_items[:top_k]
