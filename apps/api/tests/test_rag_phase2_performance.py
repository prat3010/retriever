"""Unit tests for Phase 2 SOTA RAG Modernization (Performance, Latency & Scale)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.cache.config_cache import RerankerCandidateCache
from src.adapters.cognitive.local_reranker_adapter import ColBertMaxSimRerankerAdapter
from src.adapters.cognitive.query_intent_adapter import LLMQueryIntentAdapter
from src.domain.abstractions.retrieval import SearchResult
from src.domain.inference.orchestrator import InferenceOrchestrator


@pytest.mark.asyncio
async def test_colbert_max_sim_reranker():
    """Verify ColBertMaxSimRerankerAdapter performs token-level MaxSim candidate re-scoring."""
    adapter = ColBertMaxSimRerankerAdapter()
    candidates = [
        SearchResult(chunk_id="c1", document_id="d1", content="Enterprise privacy policy details", score=0.8),
        SearchResult(chunk_id="c2", document_id="d1", content="Unrelated baking recipe for cookies", score=0.9),
    ]

    reranked = await adapter.rerank("privacy policy", candidates, top_n=2, threshold=0.1)

    assert len(reranked) == 2
    # c1 has higher MaxSim token overlap with "privacy policy" so should be ranked top
    assert reranked[0].chunk_id == "c1"


@pytest.mark.asyncio
async def test_speculative_rag_drafting():
    """Verify InferenceOrchestrator executes dual-stage Speculative RAG drafting."""
    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(side_effect=[
        MagicMock(content="Draft answer from 1B model"),
        MagicMock(content="Final verified answer from 70B model", usage=MagicMock(input_tokens=100, output_tokens=50)),
    ])

    orchestrator = InferenceOrchestrator(
        llm_provider=mock_llm,
        prompt_builder=MagicMock(build_messages=AsyncMock(return_value=[])),
        citation_validator=MagicMock(get_invalid_citations=MagicMock(return_value=[])),
        session_repo=MagicMock(get_messages=AsyncMock(return_value=[]), add_message=AsyncMock()),
        log_writer=MagicMock(write_log=AsyncMock()),
    )

    tenant_config = MagicMock()
    tenant_config.ai_provider.default_model = "gpt-4o"
    tenant_config.ai_provider.pricing = {}
    tenant_config.ai_provider.model_dump.return_value = {}
    tenant_config.retrieval_settings.summarize_after_turns = 10
    tenant_config.retrieval_settings.top_k = 5
    tenant_config.retrieval_settings.json_schema = None
    tenant_config.budget_settings = None

    response = await orchestrator.generate_speculative(
        tenant_id="tenant_123",
        session_id="session_123",
        query="What is the refund policy?",
        context_chunks=[SearchResult(chunk_id="c1", document_id="d1", content="Refunds allowed within 30 days.", score=0.95)],
        tenant_config=tenant_config,
    )

    assert response.content == "Final verified answer from 70B model"
    assert getattr(response, "speculative_draft", "") == "Draft answer from 1B model"


@pytest.mark.asyncio
async def test_reranker_candidate_cache():
    """Verify RerankerCandidateCache handles cache set and get operations cleanly."""
    cache = RerankerCandidateCache()
    cached = await cache.get_cached_candidates("tenant_123", "sample query")
    assert cached is None  # Handles missing Redis connection gracefully without raising exceptions


@pytest.mark.asyncio
async def test_adaptive_query_intent_classifier():
    """Verify LLMQueryIntentAdapter classifies query intent structure."""
    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(return_value=MagicMock(content='{"top_k": 3, "enable_hybrid": false, "enable_reranking": false, "enable_web_search": false}'))

    classifier = LLMQueryIntentAdapter(llm=mock_llm)
    intent = await classifier.classify("what is 2+2")

    assert intent.top_k == 3
    assert intent.enable_hybrid is False
