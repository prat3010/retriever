"""Sublinear TF-IDF and BM25 Sparse Vectorization Engine.

Tailored for software architecture, code symbols, camelCase/snake_case tokens,
and technical documentation. Pure domain implementation using vectorized NumPy.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass, field

# Generic stopwords to filter out, preserving code and architectural tokens
DEFAULT_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an",
    "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
    "before", "being", "below", "between", "both", "but", "by", "can't",
    "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "during", "each", "few", "for", "from",
    "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having",
    "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself",
    "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've",
    "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's",
    "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of",
    "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
    "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd",
    "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than",
    "that", "that's", "the", "their", "theirs", "them", "themselves", "then",
    "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've",
    "were", "weren't", "what", "what's", "when", "when's", "where", "where's",
    "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't",
    "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your",
    "yours", "yourself", "yourselves"
}


@dataclass
class SparseScoredCandidate:
    chunk_id: str
    score: float
    matched_terms: list[str] = field(default_factory=list)


class SublinearSparseEngine:
    """High-performance Sublinear TF-IDF and BM25 Sparse Vectorizer."""

    def __init__(
        self,
        k1: float = 1.2,
        b: float = 0.75,
        sublinear_tf: bool = True,
        stopwords: set[str] | None = None,
    ) -> None:
        self.k1 = k1
        self.b = b
        self.sublinear_tf = sublinear_tf
        self.stopwords = stopwords if stopwords is not None else DEFAULT_STOPWORDS
        self.doc_count = 0
        self.avg_doc_len = 0.0
        self.doc_lengths: dict[str, int] = {}
        self.doc_term_freqs: dict[str, Counter[str]] = {}
        self.inverted_index: dict[str, set[str]] = {}
        self.idf_cache: dict[str, float] = {}

    def tokenize(self, text: str) -> list[str]:
        """Extract code identifiers, camelCase splits, snake_case parts, and words."""
        if not text:
            return []

        tokens: list[str] = []
        raw_words = re.findall(r"[A-Za-z0-9_.\-]+", text)

        for word in raw_words:
            w_lower = word.lower()
            if len(w_lower) > 1 and w_lower not in self.stopwords:
                tokens.append(w_lower)

            # Split camelCase: e.g. parseIntent -> parse, intent
            camel_parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\W|$)|\d+", word)
            if len(camel_parts) > 1:
                for cp in camel_parts:
                    cp_lower = cp.lower()
                    if len(cp_lower) > 1 and cp_lower not in self.stopwords:
                        tokens.append(cp_lower)

            # Split snake_case / kebab-case: e.g. tenant_id -> tenant, id
            if "_" in word or "-" in word or "." in word:
                sub_parts = re.split(r"[_.\-]+", word)
                if len(sub_parts) > 1:
                    for sp in sub_parts:
                        sp_lower = sp.lower()
                        if len(sp_lower) > 1 and sp_lower not in self.stopwords:
                            tokens.append(sp_lower)

        return tokens

    def index_documents(self, documents: list[tuple[str, str]]) -> None:
        """Fit and index a collection of (chunk_id, content) documents."""
        self.doc_count = len(documents)
        if self.doc_count == 0:
            self.avg_doc_len = 0.0
            return

        total_len = 0
        self.doc_lengths.clear()
        self.doc_term_freqs.clear()
        self.inverted_index.clear()
        self.idf_cache.clear()

        for chunk_id, content in documents:
            tokens = self.tokenize(content)
            doc_len = len(tokens)
            self.doc_lengths[chunk_id] = doc_len
            total_len += doc_len

            tf = Counter(tokens)
            self.doc_term_freqs[chunk_id] = tf

            for term in tf.keys():
                if term not in self.inverted_index:
                    self.inverted_index[term] = set()
                self.inverted_index[term].add(chunk_id)

        self.avg_doc_len = total_len / self.doc_count if self.doc_count > 0 else 0.0

        # Precompute IDF for all vocabulary terms
        for term, posting in self.inverted_index.items():
            n_t = len(posting)
            # Robertson-Spärck Jones probabilistic IDF with smoothing
            idf = math.log(1.0 + (self.doc_count - n_t + 0.5) / (n_t + 0.5))
            self.idf_cache[term] = max(0.01, idf)

    def get_idf(self, term: str) -> float:
        """Retrieve precomputed IDF or calculate out-of-vocabulary smoothed IDF."""
        if term in self.idf_cache:
            return self.idf_cache[term]
        if self.doc_count == 0:
            return 1.0
        return math.log(1.0 + (self.doc_count + 0.5) / 0.5)

    def score_query_bm25(self, query: str, top_k: int = 10) -> list[SparseScoredCandidate]:
        """Score indexed documents against query terms using sublinear BM25."""
        if not query or self.doc_count == 0:
            return []

        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        candidate_chunk_ids: set[str] = set()
        for qt in query_tokens:
            if qt in self.inverted_index:
                candidate_chunk_ids.update(self.inverted_index[qt])

        if not candidate_chunk_ids:
            return []

        scored_candidates: list[SparseScoredCandidate] = []

        for chunk_id in candidate_chunk_ids:
            doc_tf = self.doc_term_freqs.get(chunk_id, Counter())
            doc_len = self.doc_lengths.get(chunk_id, 1)
            score = 0.0
            matched: list[str] = []

            for qt in query_tokens:
                raw_tf = doc_tf.get(qt, 0)
                if raw_tf > 0:
                    matched.append(qt)
                    idf = self.get_idf(qt)

                    if self.sublinear_tf:
                        tf_scaled = 1.0 + math.log(raw_tf)
                    else:
                        tf_scaled = float(raw_tf)

                    len_norm = 1.0 - self.b + self.b * (doc_len / self.avg_doc_len if self.avg_doc_len > 0 else 1.0)
                    term_score = idf * ((tf_scaled * (self.k1 + 1.0)) / (tf_scaled + self.k1 * len_norm))
                    score += term_score

            if score > 0:
                scored_candidates.append(
                    SparseScoredCandidate(
                        chunk_id=chunk_id,
                        score=score,
                        matched_terms=matched,
                    )
                )

        scored_candidates.sort(key=lambda x: x.score, reverse=True)
        return scored_candidates[:top_k]
