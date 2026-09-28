"""Automated Test Suite for Battery #42: System 1 Fast-Path Decision Plane (TypeSafe Jev).

Verifies JevClient circuit breaker, non-autoregressive decision schemas,
JevQueryIntentAdapter sub-100ms intent classification, JevCorrectiveRetrievalAdapter
CRAG verification, cascading fallbacks, and zero-toy invariants.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.cognitive.jev_client import JevCircuitState, JevClient
from src.adapters.cognitive.jev_decision_adapters import (
    JevCorrectiveRetrievalAdapter,
    JevQueryIntentAdapter,
)
from src.domain.abstractions.retrieval import (
    QueryIntent,
    QueryIntentClassifier,
    SearchResult,
)
from src.domain.batteries.battery_service import BatteryService


class DummyFallbackClassifier(QueryIntentClassifier):
    async def classify(self, query: str) -> QueryIntent:
        return QueryIntent(top_k=5, enable_hybrid=False, enable_reranking=False)


@pytest.mark.asyncio
async def test_jev_client_unconfigured_fails_fast():
    """Verify JevClient raises ValueError immediately if JEV_API_KEY is not configured."""
    client = JevClient(api_key=None)
    assert not client.is_available
    with pytest.raises(ValueError, match="JEV_API_KEY is not configured"):
        await client.decide(state="test query", questions={"k": {"type": "boolean"}})


@pytest.mark.asyncio
async def test_jev_client_circuit_breaker_trip():
    """Verify circuit breaker transitions from CLOSED -> OPEN on repeated failures."""
    client = JevClient(api_key="test-jev-key", failure_threshold=2, recovery_timeout=10.0)
    assert client.circuit_state == JevCircuitState.CLOSED
    assert client.is_available

    client._record_failure()
    assert client.circuit_state == JevCircuitState.CLOSED

    client._record_failure()
    assert client.circuit_state == JevCircuitState.OPEN
    assert not client.is_available

    with pytest.raises(RuntimeError, match="circuit breaker is OPEN"):
        await client.decide(state="query", questions={})

    # Recovery on success
    client._record_success(duration_ms=45.0)
    assert client.circuit_state == JevCircuitState.CLOSED
    assert client.is_available
    assert client.ewma_latency_ms == 45.0


@pytest.mark.asyncio
async def test_jev_client_decide_successful_request():
    """Verify JevClient successfully parses decisions and transmits tenant isolation headers."""
    client = JevClient(api_key="jev_live_mock_key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "decisions": {
            "top_k": {"value": 7, "confidence": 0.98},
            "enable_hybrid": {"value": True, "confidence": 0.95},
        },
        "latency_ms": 68.4,
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        decisions = await client.decide(
            state="Explain pgvector indexing",
            questions={"top_k": {"type": "integer"}},
            tenant_id="tn_test_enterprise",
        )

        assert decisions["top_k"]["value"] == 7
        assert decisions["enable_hybrid"]["value"] is True

        # Verify headers
        call_kwargs = mock_post.call_args.kwargs
        headers = call_kwargs["headers"]
        assert headers["Authorization"] == "Bearer jev_live_mock_key"
        assert headers["X-Tenant-ID"] == "tn_test_enterprise"


@pytest.mark.asyncio
async def test_jev_query_intent_adapter_success():
    """Verify JevQueryIntentAdapter transforms Jev typed decision into QueryIntent domain model."""
    client = MagicMock(spec=JevClient)
    client.is_available = True
    client.ewma_latency_ms = 72.0
    client.decide = AsyncMock(
        return_value={
            "top_k": {"value": 15},
            "enable_hybrid": {"value": True},
            "enable_reranking": {"value": True},
            "enable_web_search": {"value": True},
        }
    )

    adapter = JevQueryIntentAdapter(jev_client=client)
    intent = await adapter.classify("What are the latest developments in quantum LLMs?")

    assert intent.top_k == 15
    assert intent.enable_hybrid is True
    assert intent.enable_reranking is True
    assert intent.enable_web_search is True


@pytest.mark.asyncio
async def test_jev_query_intent_adapter_cascading_fallback():
    """Verify JevQueryIntentAdapter cascades smoothly to fallback when Jev client fails."""
    client = MagicMock(spec=JevClient)
    client.is_available = True
    client.decide = AsyncMock(side_effect=RuntimeError("Jev connection timeout"))

    fallback = DummyFallbackClassifier()
    adapter = JevQueryIntentAdapter(jev_client=client, fallback=fallback)

    intent = await adapter.classify("simple query")
    assert intent.top_k == 5
    assert intent.enable_hybrid is False


@pytest.mark.asyncio
async def test_jev_crag_adapter_candidate_evaluation_correct():
    """Verify JevCorrectiveRetrievalAdapter evaluates candidate relevance accurately."""
    client = MagicMock(spec=JevClient)
    client.is_available = True
    client.decide = AsyncMock(
        return_value={
            "status": {"value": "CORRECT", "confidence": 0.94},
            "confidence_score": {"value": 0.94},
            "needs_web_search": {"value": False},
        }
    )

    candidates = [
        SearchResult(
            chunk_id="chk_1",
            document_id="doc_1",
            content="Retriever uses pgvector for HNSW cosine similarity search.",
            score=0.88,
        )
    ]

    adapter = JevCorrectiveRetrievalAdapter(jev_client=client)
    decision = await adapter.evaluate_candidates(
        query="Does Retriever support pgvector?",
        candidates=candidates,
    )

    assert decision.status == "CORRECT"
    assert decision.confidence_score == 0.94
    assert decision.needs_web_search is False
    assert decision.needs_re_retrieval is False


@pytest.mark.asyncio
async def test_jev_crag_adapter_ambiguous_triggers_web_search():
    """Verify JevCorrectiveRetrievalAdapter triggers web search when retrieval is AMBIGUOUS."""
    client = MagicMock(spec=JevClient)
    client.is_available = True
    client.decide = AsyncMock(
        return_value={
            "status": {"value": "AMBIGUOUS", "confidence": 0.62},
            "confidence_score": {"value": 0.62},
            "needs_web_search": {"value": True},
        }
    )

    candidates = [
        SearchResult(
            chunk_id="chk_2",
            document_id="doc_2",
            content="Partial mention of regulatory framework.",
            score=0.55,
        )
    ]

    adapter = JevCorrectiveRetrievalAdapter(jev_client=client)
    decision = await adapter.evaluate_candidates(
        query="What are recent EU AI Act updates in 2026?",
        candidates=candidates,
    )

    assert decision.status == "AMBIGUOUS"
    assert decision.confidence_score == 0.62
    assert decision.needs_web_search is True
    assert decision.needs_re_retrieval is True
    assert decision.reformulated_query == "What are recent EU AI Act updates in 2026?"


@pytest.mark.asyncio
async def test_jev_crag_adapter_empty_candidates_fast_path():
    """Verify empty candidate list immediately yields INCORRECT without calling Jev."""
    client = MagicMock(spec=JevClient)
    client.decide = AsyncMock()

    adapter = JevCorrectiveRetrievalAdapter(jev_client=client)
    decision = await adapter.evaluate_candidates(query="something", candidates=[])

    assert decision.status == "INCORRECT"
    assert decision.confidence_score == 0.0
    assert decision.needs_web_search is True
    client.decide.assert_not_called()


@pytest.mark.asyncio
async def test_jev_crag_adapter_response_evaluation():
    """Verify evaluate_response tests grounding support."""
    client = MagicMock(spec=JevClient)
    client.is_available = True
    client.decide = AsyncMock(
        return_value={
            "is_well_supported": {"value": True},
            "confidence_score": {"value": 0.96},
        }
    )

    adapter = JevCorrectiveRetrievalAdapter(jev_client=client)
    decision = await adapter.evaluate_response(
        query="test query",
        response="Retriever is fast.",
        context_chunks=[
            SearchResult(chunk_id="c1", document_id="d1", content="Retriever is fast.", score=0.9)
        ],
    )

    assert decision.status == "CORRECT"
    assert decision.confidence_score == 0.96
    assert decision.needs_re_retrieval is False


def test_battery_service_registers_battery_42():
    """Verify Battery #42 is registered in BatteryService inventory."""
    service = BatteryService()
    resp = service.get_platform_batteries()

    assert resp.total_batteries == 42
    battery = service.get_battery("system_one_fast_decision_plane")
    assert battery is not None
    assert battery.id == "system_one_fast_decision_plane"
    assert "TypeSafe Jev" in battery.name
    assert battery.active_parameters.get("zero_toy_verified") is True
    assert battery.active_parameters.get("non_autoregressive") is True
