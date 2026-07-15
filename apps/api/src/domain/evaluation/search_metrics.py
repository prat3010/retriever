import math

from src.domain.abstractions.evaluation import SearchMetrics


def _dcg_at_k(relevance: list[float], k: int) -> float:
    k = min(k, len(relevance))
    if k == 0:
        return 0.0
    result = relevance[0]
    for i in range(1, k):
        result += relevance[i] / math.log2(i + 1)
    return result


def ndcg_at_k(retrieved: list[str], relevant: set[str], k: int = 10) -> float:
    relevance = [1.0 if cid in relevant else 0.0 for cid in retrieved[:k]]
    dcg = _dcg_at_k(relevance, k)
    ideal = sorted(relevance, reverse=True)
    idcg = _dcg_at_k(ideal, k)
    return dcg / idcg if idcg > 0 else 0.0


def mrr(retrieved: list[str], relevant: set[str]) -> float:
    for i, cid in enumerate(retrieved):
        if cid in relevant:
            return 1.0 / (i + 1)
    return 0.0


def hit_rate_at_k(retrieved: list[str], relevant: set[str], k: int = 10) -> float:
    return 1.0 if any(cid in relevant for cid in retrieved[:k]) else 0.0


def compute_search_metrics(
    retrieved_chunk_ids: list[str],
    relevant_chunk_ids: list[str],
    k: int = 10,
) -> SearchMetrics:
    relevant = set(relevant_chunk_ids)
    return SearchMetrics(
        ndcg_at_10=ndcg_at_k(retrieved_chunk_ids, relevant, k),
        mrr=mrr(retrieved_chunk_ids, relevant),
        hit_rate_at_10=hit_rate_at_k(retrieved_chunk_ids, relevant, k),
    )
