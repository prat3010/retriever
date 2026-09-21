"""Tests for ResilientEmbeddingAdapter and DeterministicLocalEmbedder."""

import asyncio
import math
from unittest.mock import AsyncMock

import pytest

from src.adapters.cognitive.resilient_embedder import (
    CircuitState,
    DeterministicLocalEmbedder,
    ResilientEmbeddingAdapter,
)


def _vector_l2_norm(vec: list[float]) -> float:
    return math.sqrt(sum(x * x for x in vec))


@pytest.mark.asyncio
async def test_deterministic_local_embedder() -> None:
    embedder = DeterministicLocalEmbedder(dimension=768)

    # 1. Text embedding shape & unit norm
    vec1 = await embedder.embed_text("High performance database indexing")
    assert len(vec1) == 768
    assert pytest.approx(_vector_l2_norm(vec1), rel=1e-3) == 1.0

    # 2. Determinism
    vec1_repeat = await embedder.embed_text("High performance database indexing")
    assert vec1 == vec1_repeat

    # 3. Discrimination
    vec2 = await embedder.embed_text("Culinary recipes for Italian pasta")
    assert vec1 != vec2

    # 4. Empty text handling
    empty_vec = await embedder.embed_text("")
    assert len(empty_vec) == 768
    assert pytest.approx(_vector_l2_norm(empty_vec), rel=1e-3) == 1.0

    # 5. Batch embedding
    batch = await embedder.embed_batch(["text one", "text two"])
    assert len(batch) == 2
    assert len(batch[0]) == 768
    assert len(batch[1]) == 768


@pytest.mark.asyncio
async def test_resilient_embedder_normal_operation() -> None:
    primary = AsyncMock()
    primary.embed_text = AsyncMock(return_value=[0.5] * 768)
    primary.embed_batch = AsyncMock(return_value=[[0.5] * 768])

    resilient = ResilientEmbeddingAdapter(
        primary=primary,
        failure_threshold=3,
        cooldown_seconds=10.0,
        dimension=768,
    )

    assert resilient.state == CircuitState.CLOSED

    res = await resilient.embed_text("Normal query")
    assert res == [0.5] * 768
    assert primary.embed_text.call_count == 1
    assert resilient.state == CircuitState.CLOSED
    assert resilient.consecutive_failures == 0


@pytest.mark.asyncio
async def test_resilient_embedder_circuit_trip_and_fallback() -> None:
    primary = AsyncMock()
    # Simulate connection outage on Ollama
    primary.embed_text = AsyncMock(side_effect=RuntimeError("Ollama connection refused"))

    resilient = ResilientEmbeddingAdapter(
        primary=primary,
        failure_threshold=3,
        cooldown_seconds=1.0,
        dimension=768,
    )

    # First 2 failures: circuit still closed but fails over to local
    for _ in range(2):
        vec = await resilient.embed_text("Query during outage")
        assert len(vec) == 768
        assert pytest.approx(_vector_l2_norm(vec), rel=1e-3) == 1.0
        assert resilient.state == CircuitState.CLOSED

    assert resilient.consecutive_failures == 2

    # 3rd failure: trips the circuit to OPEN
    vec3 = await resilient.embed_text("Trip trigger query")
    assert len(vec3) == 768
    assert resilient.state == CircuitState.OPEN
    assert resilient.consecutive_failures == 3

    # Subsequent call while circuit is OPEN: primary should NOT be invoked at all
    primary.embed_text.reset_mock()
    vec_bypassed = await resilient.embed_text("Bypassed query")
    assert len(vec_bypassed) == 768
    assert primary.embed_text.call_count == 0


@pytest.mark.asyncio
async def test_resilient_embedder_cooldown_and_recovery() -> None:
    primary = AsyncMock()
    primary.embed_text = AsyncMock(side_effect=RuntimeError("Transient error"))

    resilient = ResilientEmbeddingAdapter(
        primary=primary,
        failure_threshold=2,
        cooldown_seconds=0.1,  # Short cooldown for test
        dimension=768,
    )

    # Trip the circuit
    await resilient.embed_text("q1")
    await resilient.embed_text("q2")
    assert resilient.state == CircuitState.OPEN

    # Wait for cooldown to elapse
    await asyncio.sleep(0.15)

    # Now primary has recovered
    primary.embed_text = AsyncMock(return_value=[0.7] * 768)

    # Next call probes primary (HALF_OPEN -> CLOSED)
    vec = await resilient.embed_text("Probe query")
    assert vec == [0.7] * 768
    assert resilient.state == CircuitState.CLOSED
    assert resilient.consecutive_failures == 0


@pytest.mark.asyncio
async def test_resilient_embedder_secondary_failover() -> None:
    primary = AsyncMock()
    primary.embed_text = AsyncMock(side_effect=RuntimeError("Primary down"))

    secondary = AsyncMock()
    secondary.embed_text = AsyncMock(return_value=[0.3] * 768)

    resilient = ResilientEmbeddingAdapter(
        primary=primary,
        secondary=secondary,
        failure_threshold=2,
        cooldown_seconds=10.0,
        dimension=768,
    )

    vec = await resilient.embed_text("Failover query")
    assert vec == [0.3] * 768
    assert secondary.embed_text.call_count == 1
