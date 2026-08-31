"""Contrastive LoRA Domain Adapter for Embedding Calibration.

Implements Low-Rank Adaptation (LoRA) projection:
  h_adapted = h + (alpha / r) * (h @ B) @ A
where B in R^{d x r} (init 0), A in R^{r x d} (init Gaussian), rank r in {8, 16}.

Trained via MultipleNegativesRankingLoss / InfoNCE contrastive optimization
to calibrate local embeddings (nomic-embed-text) for software architecture & SOW domains.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class LoraAdapterConfig:
    dim: int = 768
    rank: int = 8
    alpha: float = 16.0
    temperature: float = 0.05
    learning_rate: float = 1e-3
    epochs: int = 20
    batch_size: int = 16


class LoraEmbeddingAdapter:
    """Low-Rank Embedding Adapter for Domain-Specific Space Calibration."""

    def __init__(
        self,
        dim: int = 768,
        rank: int = 8,
        alpha: float = 16.0,
        temperature: float = 0.05,
        weights: dict[str, Any] | None = None,
    ) -> None:
        self.dim = dim
        self.rank = rank
        self.alpha = alpha
        self.scaling = alpha / rank if rank > 0 else 1.0
        self.temperature = temperature

        if weights:
            self.load_state_dict(weights)
        else:
            # Gaussian init for A, Zero init for B (exact identity forward at start)
            rng = np.random.default_rng(seed=42)
            self.matrix_a = (rng.standard_normal((self.rank, self.dim)) * (1.0 / np.sqrt(self.dim))).astype(np.float32)
            self.matrix_b = np.zeros((self.dim, self.rank), dtype=np.float32)

    def adapt_vector(self, vector: list[float] | np.ndarray) -> list[float]:
        """Project a single embedding vector through the LoRA residual layer."""
        v = np.asarray(vector, dtype=np.float32)
        if v.shape[0] != self.dim:
            # Dim mismatch fallback (e.g. 1536 vs 768) -> return original without crashing
            return list(vector)

        # Residual delta = (v @ B) @ A * scaling
        delta = self.scaling * ((v @ self.matrix_b) @ self.matrix_a)
        adapted = v + delta

        # L2 Normalize
        norm = np.linalg.norm(adapted)
        if norm > 1e-12:
            adapted = adapted / norm

        return adapted.tolist()

    def adapt_batch(self, vectors: np.ndarray | list[list[float]]) -> np.ndarray:
        """Project a batch of embedding vectors (N x D) through the LoRA layer."""
        v = np.asarray(vectors, dtype=np.float32)
        if v.ndim == 1:
            return np.array(self.adapt_vector(v), dtype=np.float32)

        if v.shape[1] != self.dim:
            return v

        delta = self.scaling * ((v @ self.matrix_b) @ self.matrix_a)
        adapted = v + delta
        norms = np.linalg.norm(adapted, axis=1, keepdims=True)
        norms = np.where(norms > 1e-12, norms, 1.0)
        return (adapted / norms).astype(np.float32)

    def state_dict(self) -> dict[str, Any]:
        """Serialize adapter weights to a JSON-compatible dictionary."""
        return {
            "dim": self.dim,
            "rank": self.rank,
            "alpha": self.alpha,
            "temperature": self.temperature,
            "matrix_a": self.matrix_a.tolist(),
            "matrix_b": self.matrix_b.tolist(),
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        """Load adapter weights from a dictionary."""
        self.dim = int(state.get("dim", self.dim))
        self.rank = int(state.get("rank", self.rank))
        self.alpha = float(state.get("alpha", self.alpha))
        self.scaling = self.alpha / self.rank if self.rank > 0 else 1.0
        self.temperature = float(state.get("temperature", self.temperature))
        self.matrix_a = np.array(state["matrix_a"], dtype=np.float32)
        self.matrix_b = np.array(state["matrix_b"], dtype=np.float32)


class ContrastiveTrainer:
    """Trainer optimizing LoRA adapter weights using MultipleNegativesRankingLoss."""

    def __init__(self, config: LoraAdapterConfig | None = None) -> None:
        self.config = config or LoraAdapterConfig()

    def train(
        self,
        queries: list[list[float]],
        positives: list[list[float]],
        adapter: LoraEmbeddingAdapter,
        epochs: int = 15,
        lr: float = 1e-3,
    ) -> float:
        """Train LoRA adapter parameters using InfoNCE contrastive in-batch loss.

        Returns final loss score.
        """
        q_arr = np.asarray(queries, dtype=np.float32)
        p_arr = np.asarray(positives, dtype=np.float32)

        n_samples = len(q_arr)
        if n_samples < 2 or q_arr.shape[1] != adapter.dim:
            return 0.0

        # Adam optimizer state
        m_b = np.zeros_like(adapter.matrix_b)
        v_b = np.zeros_like(adapter.matrix_b)
        m_a = np.zeros_like(adapter.matrix_a)
        v_a = np.zeros_like(adapter.matrix_a)
        beta1, beta2, eps = 0.9, 0.999, 1e-8
        step = 0
        final_loss = 0.0

        tau = adapter.temperature
        scale = adapter.scaling

        for epoch in range(epochs):
            # 1. Forward pass: compute adapted representations
            # Q_adapt: (N, D), P_adapt: (N, D)
            q_raw = q_arr
            p_raw = p_arr

            # Intermediate activations:
            # h_q = q_raw @ B : (N, r)
            # h_p = p_raw @ B : (N, r)
            h_q = q_raw @ adapter.matrix_b
            h_p = p_raw @ adapter.matrix_b

            q_delta = scale * (h_q @ adapter.matrix_a)
            p_delta = scale * (h_p @ adapter.matrix_a)

            q_hat = q_raw + q_delta
            p_hat = p_raw + p_delta

            q_norms = np.linalg.norm(q_hat, axis=1, keepdims=True)
            p_norms = np.linalg.norm(p_hat, axis=1, keepdims=True)
            q_norms = np.where(q_norms > 1e-12, q_norms, 1.0)
            p_norms = np.where(p_norms > 1e-12, p_norms, 1.0)

            q_normed = q_hat / q_norms
            p_normed = p_hat / p_norms

            # Similarity matrix: sim_mat[i, j] = q_normed[i] @ p_normed[j]
            # Dimensions: (N, N)
            sim_mat = (q_normed @ p_normed.T) / tau

            # Numerical stability: subtract max per row
            sim_max = np.max(sim_mat, axis=1, keepdims=True)
            exp_sim = np.exp(sim_mat - sim_max)
            sum_exp_sim = np.sum(exp_sim, axis=1, keepdims=True)
            probs = exp_sim / sum_exp_sim  # (N, N)

            # Cross entropy loss on diagonal (i == j)
            diag_probs = np.diagonal(probs)
            loss = -np.mean(np.log(np.maximum(diag_probs, 1e-12)))
            final_loss = float(loss)

            # 2. Backward pass (Gradient calculation)
            # dL/dS = (probs - I) / N
            grad_sim = (probs - np.eye(n_samples, dtype=np.float32)) / (n_samples * tau)

            # Gradients w.r.t q_normed and p_normed:
            grad_q_normed = grad_sim @ p_normed
            grad_p_normed = grad_sim.T @ q_normed

            # Gradients through L2 normalization:
            def backprop_norm(grad_out: np.ndarray, x: np.ndarray, norms: np.ndarray) -> np.ndarray:
                dot = np.sum(grad_out * x, axis=1, keepdims=True)
                return (grad_out - x * (dot / (norms ** 2))) / norms

            grad_q_hat = backprop_norm(grad_q_normed, q_hat, q_norms)
            grad_p_hat = backprop_norm(grad_p_normed, p_hat, p_norms)

            # Combined residual gradients
            grad_a = scale * (h_q.T @ grad_q_hat + h_p.T @ grad_p_hat)
            grad_b = scale * (q_raw.T @ (grad_q_hat @ adapter.matrix_a.T) + p_raw.T @ (grad_p_hat @ adapter.matrix_a.T))

            # 3. Adam weight update with gradient clipping
            np.clip(grad_a, -1.0, 1.0, out=grad_a)
            np.clip(grad_b, -1.0, 1.0, out=grad_b)

            step += 1
            m_a = beta1 * m_a + (1 - beta1) * grad_a
            v_a = beta2 * v_a + (1 - beta2) * (grad_a ** 2)
            m_b = beta1 * m_b + (1 - beta1) * grad_b
            v_b = beta2 * v_b + (1 - beta2) * (grad_b ** 2)

            m_a_hat = m_a / (1 - beta1 ** step)
            v_a_hat = v_a / (1 - beta2 ** step)
            m_b_hat = m_b / (1 - beta1 ** step)
            v_b_hat = v_b / (1 - beta2 ** step)

            # Cosine decay schedule
            current_lr = lr * 0.5 * (1.0 + np.cos(np.pi * epoch / epochs))
            adapter.matrix_a -= (current_lr * m_a_hat / (np.sqrt(v_a_hat) + eps)).astype(np.float32)
            adapter.matrix_b -= (current_lr * m_b_hat / (np.sqrt(v_b_hat) + eps)).astype(np.float32)

        return final_loss
