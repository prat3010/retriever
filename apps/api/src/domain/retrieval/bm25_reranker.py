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
) -> list[SearchResult]:
    if not candidates or not query.strip():
        return candidates

    query_tokens = _tokenize(query)
    if not query_tokens:
        return candidates

    # Document lengths (in tokens) and average
    doc_lengths = [len(_tokenize(r.content)) for r in candidates]
    avgdl = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 1.0

    n = len(candidates)

    # Document frequency: in how many candidates does each query token appear
    df: Counter[str] = Counter()
    for r in candidates:
        tokens = set(_tokenize(r.content))
        for qt in set(query_tokens):
            if qt in tokens:
                df[qt] += 1

    for i, r in enumerate(candidates):
        doc_tokens = _tokenize(r.content)
        tf_counter = Counter(doc_tokens)
        doc_len = doc_lengths[i]

        score = 0.0
        for qt in set(query_tokens):
            tf = tf_counter.get(qt, 0)
            if tf == 0:
                continue
            idf = math.log(1 + (n - df.get(qt, 0) + 0.5) / (df.get(qt, 0) + 0.5))
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_len / avgdl)
            score += idf * numerator / denominator

        r.score = score

    candidates.sort(key=lambda x: x.score, reverse=True)
    return candidates
