"""Neural ONNX ColBERT Late-Interaction MaxSim Engine (M124).

Implements authentic contextual token-level late interaction:
    MaxSim(Q, D) = (1 / |Q|) * Σ_{q in Q} max_{d in D} (E_Q(q) · E_D(d)^T)

Supports lightweight in-process ONNX execution via FastEmbed LateInteractionTextEmbedding.
Includes seamless zero-dependency fallback to BatchColbertMaxSimEngine when running
in minimal environments or without pre-warmed weights.
"""

from __future__ import annotations

import logging
from typing import Any

from src.domain.abstractions.retrieval import SearchResult
from src.domain.retrieval.colbert_engine import (
    BatchColbertMaxSimEngine,
    compute_colbert_maxsim,
    tokenize_technical_terms,
)

logger = logging.getLogger(__name__)


class NeuralColbertEngine:
    """Hardware-aware, ONNX-accelerated ColBERT MaxSim reranking engine."""

    def __init__(
        self,
        model_name: str = "colbert-ir/colbertv2.0",
        dim: int = 128,
        prefer_neural: bool = True,
        neural_model: Any | None = None,
    ) -> None:
        self.model_name = model_name
        self.dim = dim
        self.prefer_neural = prefer_neural
        self._neural_model: Any | None = neural_model
        self._fallback_engine = BatchColbertMaxSimEngine(dim=dim)
        self._is_neural = neural_model is not None

        if prefer_neural and neural_model is None:
            self._try_load_neural_model()

    def _try_load_neural_model(self) -> None:
        """Attempt to lazily load ONNX ColBERT embedding model."""
        try:
            from fastembed.late_interaction import LateInteractionTextEmbedding

            self._neural_model = LateInteractionTextEmbedding(model_name=self.model_name)
            self._is_neural = True
            logger.info("Neural ONNX ColBERT model '%s' loaded successfully.", self.model_name)
        except Exception as exc:
            logger.debug(
                "Neural ColBERT model '%s' unavailable (%s). Using deterministic MaxSim hash engine.",
                self.model_name,
                exc,
            )
            self._neural_model = None
            self._is_neural = False

    @property
    def is_neural(self) -> bool:
        return self._is_neural

    @property
    def is_neural_active(self) -> bool:
        """Return True if running authentic neural ONNX weights."""
        return self._is_neural

    def score_pair(self, query: str, document_text: str) -> float:
        """Compute late-interaction MaxSim score between query and a document."""
        if self._is_neural and self._neural_model is not None:
            try:
                # FastEmbed returns generators yielding list of token embeddings per text
                q_embeddings = next(iter(self._neural_model.embed([query])))
                d_embeddings = next(iter(self._neural_model.embed([document_text])))

                # Compute MaxSim: for each query token vector, max dot product with doc token vectors
                import numpy as np

                q_mat = np.array(q_embeddings)  # shape: (Q_len, D)
                d_mat = np.array(d_embeddings)  # shape: (D_len, D)

                # Similarity matrix: (Q_len, D_len)
                sim_matrix = np.matmul(q_mat, d_mat.T)
                # Max similarity per query token
                max_sims = np.max(sim_matrix, axis=1)
                return float(np.mean(max_sims))
            except Exception as exc:
                logger.debug("Neural MaxSim score_pair failed: %s, falling back to hash", exc)

        # Fallback to deterministic token MaxSim
        q_tokens = tokenize_technical_terms(query)
        d_tokens = tokenize_technical_terms(document_text)
        return compute_colbert_maxsim(q_tokens, d_tokens)

    def rerank_candidates(
        self,
        query: str,
        candidates: list[SearchResult],
        top_k: int = 10,
    ) -> list[SearchResult]:
        """Rerank candidate SearchResults using ColBERT token-level late-interaction."""
        if not candidates or not query.strip():
            return candidates[:top_k]

        if self._is_neural and self._neural_model is not None:
            try:
                import numpy as np

                doc_texts = [c.content for c in candidates]
                q_embeddings = next(iter(self._neural_model.embed([query])))
                q_mat = np.array(q_embeddings)

                d_embeddings_list = list(self._neural_model.embed(doc_texts))

                scored_candidates: list[SearchResult] = []
                for idx, c in enumerate(candidates):
                    d_mat = np.array(d_embeddings_list[idx])
                    sim_matrix = np.matmul(q_mat, d_mat.T)
                    max_sims = np.max(sim_matrix, axis=1)
                    neural_score = float(np.mean(max_sims))

                    # Blend neural late-interaction score with upstream retrieval score
                    blended = 0.85 * neural_score + 0.15 * min(1.0, c.score)
                    scored_candidates.append(
                        c.model_copy(update={"score": round(blended, 4)})
                    )

                scored_candidates.sort(key=lambda x: x.score, reverse=True)
                return scored_candidates[:top_k]
            except Exception as exc:
                logger.debug("Neural rerank_candidates failed: %s, falling back to hash", exc)

        # Fallback path using batch deterministic MaxSim
        q_tokens = tokenize_technical_terms(query)
        doc_token_batches = [tokenize_technical_terms(c.content) for c in candidates]
        scores = self._fallback_engine.batch_maxsim(q_tokens, doc_token_batches)

        reranked: list[SearchResult] = []
        for c, s in zip(candidates, scores, strict=False):
            blended = 0.85 * s + 0.15 * min(1.0, c.score)
            reranked.append(c.model_copy(update={"score": round(blended, 4)}))

        reranked.sort(key=lambda x: x.score, reverse=True)
        return reranked[:top_k]
