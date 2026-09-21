"""Resilient Embedding Adapter with Circuit Breaker and Local Fallback.

Wraps an upstream EmbeddingProvider (e.g. OllamaEmbeddingAdapter) with a stateful
circuit breaker pattern. When the primary provider encounters consecutive failures,
the circuit opens and requests fail over to a secondary provider or an in-process
deterministic projection embedder without hard-failing ingestion or query pipelines.
"""

import asyncio
import hashlib
import logging
import math
import re
import time
from enum import StrEnum

from src.domain.abstractions.retrieval import EmbeddingProvider

logger = logging.getLogger(__name__)


class CircuitState(StrEnum):
    """Operational states of the resilient embedding circuit breaker."""
    CLOSED = "CLOSED"        # Normal operation: routing to primary provider
    OPEN = "OPEN"            # Tripped: primary is failing, routing to fallback
    HALF_OPEN = "HALF_OPEN"  # Probe: cooldown elapsed, testing primary recovery


class DeterministicLocalEmbedder(EmbeddingProvider):
    """In-process deterministic semantic projection embedder.

    Produces normalized float vectors using feature hashing with sublinear TF
    and n-gram tokenization. Guarantees reproducible, unit-length embeddings
    of arbitrary dimension (default 768) without external network dependencies.
    """

    def __init__(self, dimension: int = 768) -> None:
        self.dimension = dimension

    async def embed_text(self, text: str) -> list[float]:
        return self._project_text(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._project_text(t) for t in texts]

    def _project_text(self, text: str) -> list[float]:
        if not text or not text.strip():
            # Return unit vector along first dimension for empty input
            vec = [0.0] * self.dimension
            vec[0] = 1.0
            return vec

        # Tokenize words and character 3-grams
        tokens = re.findall(r"\w+", text.lower())
        features: dict[str, int] = {}
        for token in tokens:
            features[token] = features.get(token, 0) + 1
            if len(token) >= 3:
                for i in range(len(token) - 2):
                    ngram = token[i : i + 3]
                    features[ngram] = features.get(ngram, 0) + 1

        # Project features into dense dimension via hashing trick
        dense = [0.0] * self.dimension
        for feat, count in features.items():
            # Sublinear TF weighting
            weight = 1.0 + math.log(count)
            # Hash to index and sign bit
            h = int(hashlib.sha256(feat.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if ((h >> 31) & 1) == 0 else -1.0
            dense[idx] += sign * weight

        # L2 unit normalization
        norm = math.sqrt(sum(x * x for x in dense))
        if norm > 1e-12:
            return [x / norm for x in dense]

        vec = [0.0] * self.dimension
        vec[0] = 1.0
        return vec


class ResilientEmbeddingAdapter(EmbeddingProvider):
    """Circuit-breaking wrapper for embedding providers.

    Args:
        primary: Primary upstream embedding provider (e.g. OllamaEmbeddingAdapter).
        secondary: Optional secondary provider to try before local projection.
        failure_threshold: Number of consecutive failures to trip the circuit (default: 3).
        cooldown_seconds: Duration to hold circuit OPEN before probing (default: 60.0).
        dimension: Embedding vector dimension (default: 768).
    """

    def __init__(
        self,
        primary: EmbeddingProvider,
        secondary: EmbeddingProvider | None = None,
        failure_threshold: int = 3,
        cooldown_seconds: float = 60.0,
        dimension: int = 768,
    ) -> None:
        self._primary = primary
        self._secondary = secondary
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._dimension = dimension
        self._local_fallback = DeterministicLocalEmbedder(dimension=dimension)

        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._last_failure_time: float | None = None
        self._fallback_count = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    @property
    def fallback_count(self) -> int:
        return self._fallback_count

    @property
    def cooldown_seconds(self) -> float:
        return self._cooldown_seconds

    async def embed_text(self, text: str) -> list[float]:
        should_try_primary = await self._check_primary_allowed()

        if should_try_primary:
            try:
                result = await self._primary.embed_text(text)
                await self._record_success()
                return result
            except Exception as exc:
                await self._record_failure(exc)

        # Fallback path
        return await self._execute_fallback_text(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        should_try_primary = await self._check_primary_allowed()

        if should_try_primary:
            try:
                result = await self._primary.embed_batch(texts)
                await self._record_success()
                return result
            except Exception as exc:
                await self._record_failure(exc)

        # Fallback path
        return await self._execute_fallback_batch(texts)

    async def _check_primary_allowed(self) -> bool:
        """Determines whether primary should be attempted based on circuit state."""
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                now = time.monotonic()
                if self._last_failure_time and (now - self._last_failure_time) >= self._cooldown_seconds:
                    logger.info(
                        "ResilientEmbedder: Cooldown period elapsed (%.1fs). Transitioning to HALF_OPEN probe.",
                        self._cooldown_seconds,
                    )
                    self._state = CircuitState.HALF_OPEN
                    return True
                return False

            if self._state == CircuitState.HALF_OPEN:
                return True

            return False

    async def _record_success(self) -> None:
        """Records a successful primary call and closes the circuit."""
        async with self._lock:
            if self._state != CircuitState.CLOSED:
                logger.info(
                    "ResilientEmbedder: Primary provider recovered. Transitioning from %s to CLOSED.",
                    self._state.value,
                )
            self._state = CircuitState.CLOSED
            self._consecutive_failures = 0
            self._last_failure_time = None

    async def _record_failure(self, exc: Exception) -> None:
        """Records a failure from the primary provider and updates circuit state."""
        async with self._lock:
            self._consecutive_failures += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                logger.warning(
                    "ResilientEmbedder: Probe failed in HALF_OPEN state (%s). Reopening circuit for %.1fs.",
                    exc,
                    self._cooldown_seconds,
                )
                self._state = CircuitState.OPEN
            elif self._consecutive_failures >= self._failure_threshold:
                if self._state != CircuitState.OPEN:
                    logger.warning(
                        "ResilientEmbedder: Tripped circuit after %d consecutive failures (%s). Entering OPEN state.",
                        self._consecutive_failures,
                        exc,
                    )
                self._state = CircuitState.OPEN
            else:
                logger.warning(
                    "ResilientEmbedder: Primary provider failure %d/%d (%s).",
                    self._consecutive_failures,
                    self._failure_threshold,
                    exc,
                )

    async def _execute_fallback_text(self, text: str) -> list[float]:
        """Executes fallback via secondary provider if configured, else local projection."""
        async with self._lock:
            self._fallback_count += 1

        if self._secondary:
            try:
                return await self._secondary.embed_text(text)
            except Exception as sec_exc:
                logger.warning("ResilientEmbedder: Secondary provider also failed: %s", sec_exc)

        return await self._local_fallback.embed_text(text)

    async def _execute_fallback_batch(self, texts: list[str]) -> list[list[float]]:
        """Executes batch fallback via secondary provider if configured, else local projection."""
        async with self._lock:
            self._fallback_count += len(texts)

        if self._secondary:
            try:
                return await self._secondary.embed_batch(texts)
            except Exception as sec_exc:
                logger.warning("ResilientEmbedder: Secondary provider batch failed: %s", sec_exc)

        return await self._local_fallback.embed_batch(texts)
