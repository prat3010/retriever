import math
import re
from collections import Counter

from src.domain.abstractions.retrieval import SearchResult


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def bm25_rerank(
    query: str,
    candidates: list[SearchResult],
    k1: float = 1.5,
    b: float = 0.75,
    corpus_size: int | None = None,
    corpus_df: dict[str, int] | None = None,
) -> list[SearchResult]:
    """Rerank search candidate results using BM25 scoring with optional corpus-level IDF scaling."""
    if not candidates or not query.strip():
        return candidates

    query_tokens = _tokenize(query)
    if not query_tokens:
        return candidates

    # Document lengths (in tokens) and average
    doc_lengths = [len(_tokenize(r.content)) for r in candidates]
    avgdl = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 1.0

    n = len(candidates)
    effective_n = max(n, corpus_size) if corpus_size is not None else n

    # Document frequency: in how many candidates does each query token appear
    df: Counter[str] = Counter()
    for r in candidates:
        tokens = set(_tokenize(r.content))
        for qt in set(query_tokens):
            if qt in tokens:
                df[qt] += 1

    reranked: list[SearchResult] = []
    for i, r in enumerate(candidates):
        doc_tokens = _tokenize(r.content)
        tf_counter = Counter(doc_tokens)
        doc_len = doc_lengths[i]

        score = 0.0
        for qt in set(query_tokens):
            tf = tf_counter.get(qt, 0)
            if tf == 0:
                continue
            term_df = corpus_df.get(qt, df.get(qt, 0)) if corpus_df else df.get(qt, 0)
            idf = math.log(1 + (effective_n - term_df + 0.5) / (term_df + 0.5))
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_len / avgdl)
            score += idf * numerator / denominator

        reranked.append(r.model_copy(update={"score": score}))

    reranked.sort(key=lambda x: x.score, reverse=True)
    return reranked
