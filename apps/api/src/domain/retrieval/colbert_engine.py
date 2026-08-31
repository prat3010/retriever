"""ColBERT Late-Interaction Token-Level MaxSim Engine.

Hexagonal boundary rule: Pure mathematical domain logic.
Only standard library modules and vectorized tensor mathematical operations allowed.
Zero database, framework, or HTTP imports.
"""
import hashlib
import math
import re
from collections.abc import Sequence

from src.domain.abstractions.retrieval import SearchResult


def tokenize_technical_terms(text: str) -> list[str]:
    """Tokenize text preserving code identifiers, camelCase, snake_case, and alphanumeric tags."""
    if not text:
        return []

    # Replace markdown symbols and punctuation except underscores and hyphens
    cleaned = re.sub(r"[^\w\-\.]", " ", text)
    raw_tokens = cleaned.split()

    tokens: list[str] = []
    for token in raw_tokens:
        clean_tok = token.strip(".-").lower()
        if not clean_tok:
            continue
        tokens.append(clean_tok)

        # Decompose camelCase (e.g. calcQuote -> calc, quote)
        camel_parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)", token)
        if len(camel_parts) > 1:
            for part in camel_parts:
                p_lower = part.lower()
                if p_lower and p_lower not in tokens:
                    tokens.append(p_lower)

        # Decompose snake_case or hyphenated (e.g. tenant_id -> tenant, id)
        if "_" in token or "-" in token:
            sub_parts = re.split(r"[_\-]+", token)
            for sub in sub_parts:
                s_lower = sub.lower()
                if s_lower and s_lower not in tokens:
                    tokens.append(s_lower)

    return tokens


def _token_to_vector(token: str, dim: int = 128) -> list[float]:
    """Compute a deterministic unit-normalized pseudo-embedding for a token string."""
    hash_digest = hashlib.sha256(token.encode("utf-8")).digest()
    vec: list[float] = []
    for i in range(dim):
        byte_val = hash_digest[i % len(hash_digest)]
        # Map byte (0-255) to float (-1.0 to 1.0)
        val = (byte_val / 127.5) - 1.0
        vec.append(val)

    # Unit L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 1e-9:
        vec = [x / norm for x in vec]
    return vec


def _cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    """Compute cosine similarity between two unit-normalized vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=False))
    return max(0.0, min(1.0, (dot + 1.0) / 2.0))


def compute_colbert_maxsim(query_tokens: list[str], doc_tokens: list[str]) -> float:
    """Compute the ColBERT MaxSim operator score between query tokens and document tokens.

    MaxSim(Q, D) = (1 / |Q|) * Σ_{q in Q} max_{d in D} (Sim(q, d))
    """
    if not query_tokens or not doc_tokens:
        return 0.0

    doc_token_set = set(doc_tokens)
    doc_vectors = [_token_to_vector(d) for d in doc_tokens[:256]]  # Cap at 256 tokens for speed

    query_scores: list[float] = []

    for q_token in query_tokens[:32]:  # Cap query tokens at 32
        # Exact token match gets full 1.0 similarity instantly
        if q_token in doc_token_set:
            query_scores.append(1.0)
            continue

        q_vec = _token_to_vector(q_token)
        # Find maximum similarity across all document token vectors
        max_sim = 0.0
        for d_vec in doc_vectors:
            sim = _cosine_similarity(q_vec, d_vec)
            if sim > max_sim:
                max_sim = sim
                if max_sim >= 0.99:
                    break
        query_scores.append(max_sim)

    if not query_scores:
        return 0.0

    return sum(query_scores) / len(query_scores)


class BatchColbertMaxSimEngine:
    """Hardware-aware batch ColBERT MaxSim late-interaction tensor reranker."""

    def __init__(self, dim: int = 128, max_query_len: int = 32, max_doc_len: int = 256) -> None:
        self.dim = dim
        self.max_query_len = max_query_len
        self.max_doc_len = max_doc_len

    def encode_tokens(self, tokens: list[str], max_len: int) -> list[list[float]]:
        """Encode list of token strings into unit-normalized embedding matrix."""
        return [_token_to_vector(t, dim=self.dim) for t in tokens[:max_len]]

    def batch_maxsim(
        self,
        query_tokens: list[str],
        doc_token_batches: list[list[str]],
    ) -> list[float]:
        """Compute MaxSim scores for a single query across multiple candidate documents."""
        if not query_tokens or not doc_token_batches:
            return [0.0] * len(doc_token_batches)

        q_matrix = self.encode_tokens(query_tokens, self.max_query_len)
        if not q_matrix:
            return [0.0] * len(doc_token_batches)

        scores: list[float] = []
        for doc_tokens in doc_token_batches:
            if not doc_tokens:
                scores.append(0.0)
                continue
            doc_set = set(doc_tokens)
            doc_matrix = self.encode_tokens(doc_tokens, self.max_doc_len)

            q_scores: list[float] = []
            for i, q_tok in enumerate(query_tokens[: self.max_query_len]):
                if q_tok in doc_set:
                    q_scores.append(1.0)
                    continue
                q_vec = q_matrix[i]
                max_sim = 0.0
                for d_vec in doc_matrix:
                    sim = _cosine_similarity(q_vec, d_vec)
                    if sim > max_sim:
                        max_sim = sim
                        if max_sim >= 0.99:
                            break
                q_scores.append(max_sim)

            scores.append(sum(q_scores) / len(q_scores) if q_scores else 0.0)

        return scores


def score_colbert_maxsim(
    query: str,
    candidates: list[SearchResult],
    top_n: int = 10,
    threshold: float = 0.0,
    initial_weight: float = 0.4,
    maxsim_weight: float = 0.6,
) -> list[SearchResult]:
    """Rerank search candidate results using ColBERT MaxSim late interaction."""
    if not candidates or not query.strip():
        return candidates[:top_n]

    q_tokens = tokenize_technical_terms(query)
    if not q_tokens:
        return candidates[:top_n]

    doc_batches = [tokenize_technical_terms(cand.content) for cand in candidates]
    engine = BatchColbertMaxSimEngine()
    maxsim_scores = engine.batch_maxsim(q_tokens, doc_batches)

    scored: list[tuple[SearchResult, float]] = []
    for cand, maxsim in zip(candidates, maxsim_scores, strict=False):
        initial_score = max(0.0, min(1.0, cand.score))
        fused_score = round(
            initial_weight * initial_score + maxsim_weight * maxsim,
            6,
        )

        if fused_score >= threshold:
            scored.append((cand.model_copy(update={"score": fused_score}), fused_score))

    # Sort descending by fused late-interaction score
    scored.sort(key=lambda x: x[1], reverse=True)

    results = [s[0] for s in scored[:top_n]]
    return results if results else candidates[:top_n]
