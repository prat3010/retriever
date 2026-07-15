import math
import re
from collections import Counter

from src.domain.abstractions.retrieval import SearchResult


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def _compute_tfidf(docs: list[str]) -> list[dict[str, float]]:
    tokenized = [_tokenize(d) for d in docs]
    n = len(docs)
    tfs = [Counter(t) for t in tokenized]
    df: Counter[str] = Counter()
    for t in tokenized:
        df.update(set(t))
    idf = {term: math.log(1 + (n - freq + 0.5) / (freq + 0.5)) for term, freq in df.items()}
    return [{t: tf[t] * idf.get(t, 0) for t in tf} for tf in tfs]


def _cosine_sim(a: dict[str, float], b: dict[str, float]) -> float:
    dot = 0.0
    for t in a:
        if t in b:
            dot += a[t] * b[t]
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def mmr_diversify(
    candidates: list[SearchResult],
    lambda_param: float = 0.7,
    top_k: int = 10,
) -> list[SearchResult]:
    if len(candidates) <= 1:
        return candidates[:top_k]

    docs = [r.content for r in candidates]
    tfidf_vecs = _compute_tfidf(docs)

    selected: list[int] = []
    remaining = list(range(len(candidates)))

    sim_matrix = [[_cosine_sim(tfidf_vecs[i], tfidf_vecs[j]) for j in range(len(candidates))] for i in range(len(candidates))]

    for _ in range(min(top_k, len(candidates))):
        best = -1
        best_score = -1.0

        for i in remaining:
            relevance = candidates[i].score
            if selected:
                max_sim = max(sim_matrix[i][j] for j in selected)
            else:
                max_sim = 0.0
            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim
            if mmr_score > best_score:
                best_score = mmr_score
                best = i

        selected.append(best)
        remaining.remove(best)

    return [candidates[i] for i in selected]
