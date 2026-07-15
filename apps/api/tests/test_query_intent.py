"""Tests for P-3 + P-4: Adaptive retrieval + query routing via QueryIntentClassifier."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.abstractions.inference import InferenceResponse, LlmProvider, Usage
from src.domain.abstractions.retrieval import QueryIntent, QueryIntentClassifier, SearchQuery
from src.domain.retrieval.search_service import HybridSearchService


# ── Step 1: QueryIntentClassifier abstraction ──────────────────────────


def test_classifier_provider_abstract() -> None:
    assert hasattr(QueryIntentClassifier, "classify")


# ── Step 2: LLMQueryIntentAdapter ──────────────────────────────────────


@pytest.mark.asyncio
async def test_adapter_classifies_simple_question() -> None:
    from src.adapters.cognitive.query_intent_adapter import LLMQueryIntentAdapter

    mock_llm = AsyncMock(spec=LlmProvider)
    mock_llm.generate.return_value = InferenceResponse(
        content='{"top_k": 3, "enable_hybrid": false, "enable_reranking": false, "enable_web_search": false}',
        usage=Usage(input_tokens=20, output_tokens=10),
    )

    adapter = LLMQueryIntentAdapter(llm=mock_llm, model="gemini-1.5-flash")
    intent = await adapter.classify("what is 2+2")

    assert intent.top_k == 3
    assert intent.enable_hybrid is False
    assert intent.enable_reranking is False
    assert intent.enable_web_search is False


@pytest.mark.asyncio
async def test_adapter_defaults_on_invalid_json() -> None:
    from src.adapters.cognitive.query_intent_adapter import LLMQueryIntentAdapter

    mock_llm = AsyncMock(spec=LlmProvider)
    mock_llm.generate.return_value = InferenceResponse(
        content="not json",
        usage=Usage(input_tokens=5, output_tokens=2),
    )

    adapter = LLMQueryIntentAdapter(llm=mock_llm, model="gemini-1.5-flash")
    intent = await adapter.classify("anything")

    assert intent == QueryIntent()


@pytest.mark.asyncio
async def test_adapter_graceful_on_llm_error() -> None:
    from src.adapters.cognitive.query_intent_adapter import LLMQueryIntentAdapter

    mock_llm = AsyncMock(spec=LlmProvider)
    mock_llm.generate.side_effect = RuntimeError("LLM unavailable")

    adapter = LLMQueryIntentAdapter(llm=mock_llm, model="gemini-1.5-flash")
    intent = await adapter.classify("anything")

    assert intent == QueryIntent()


# ── Step 3: HybridSearchService integration ────────────────────────────


@pytest.mark.asyncio
async def test_search_overrides_flags_when_intent_enabled() -> None:
    mock_classifier = AsyncMock(spec=QueryIntentClassifier)
    mock_classifier.classify.return_value = QueryIntent(
        top_k=3, enable_hybrid=False, enable_reranking=False, enable_web_search=False
    )

    service = HybridSearchService(
        vector_search=AsyncMock(),
        keyword_search=AsyncMock(),
        embedder=AsyncMock(),
        reranker=AsyncMock(),
        query_intent_classifier=mock_classifier,
    )
    service._fan_out_search = AsyncMock(return_value=([], []))
    service._fuse_results = MagicMock(return_value=[])
    service._determine_strategy = MagicMock(return_value="vector_only")

    query = SearchQuery(
        query="what is 2+2",
        tenant_id="t1",
        top_k=10,
        enable_hybrid=True,
        enable_reranking=True,
        enable_query_intent=True,
    )
    await service.search(query)

    mock_classifier.classify.assert_called_once_with("what is 2+2")
    passed_query = service._fan_out_search.call_args[0][0]
    assert passed_query.top_k == 3
    assert passed_query.enable_hybrid is False
    assert passed_query.enable_reranking is False


@pytest.mark.asyncio
async def test_search_skips_classifier_when_disabled() -> None:
    mock_classifier = AsyncMock(spec=QueryIntentClassifier)

    service = HybridSearchService(
        vector_search=AsyncMock(),
        keyword_search=AsyncMock(),
        embedder=AsyncMock(),
        reranker=AsyncMock(),
        query_intent_classifier=mock_classifier,
    )
    service._fan_out_search = AsyncMock(return_value=([], []))
    service._fuse_results = MagicMock(return_value=[])
    service._determine_strategy = MagicMock(return_value="vector_only")

    query = SearchQuery(
        query="what is 2+2",
        tenant_id="t1",
        enable_query_intent=False,
    )
    await service.search(query)

    mock_classifier.classify.assert_not_called()


@pytest.mark.asyncio
async def test_search_skips_when_no_classifier_provider() -> None:
    service = HybridSearchService(
        vector_search=AsyncMock(),
        keyword_search=AsyncMock(),
        embedder=AsyncMock(),
        reranker=AsyncMock(),
        query_intent_classifier=None,
    )
    service._fan_out_search = AsyncMock(return_value=([], []))
    service._fuse_results = MagicMock(return_value=[])
    service._determine_strategy = MagicMock(return_value="vector_only")

    query = SearchQuery(
        query="anything",
        tenant_id="t1",
        enable_query_intent=True,
    )
    await service.search(query)

    # No error thrown


@pytest.mark.asyncio
async def test_search_keeps_defaults_on_classifier_failure() -> None:
    mock_classifier = AsyncMock(spec=QueryIntentClassifier)
    mock_classifier.classify.side_effect = RuntimeError("timeout")

    service = HybridSearchService(
        vector_search=AsyncMock(),
        keyword_search=AsyncMock(),
        embedder=AsyncMock(),
        reranker=AsyncMock(),
        query_intent_classifier=mock_classifier,
    )
    service._fan_out_search = AsyncMock(return_value=([], []))
    service._fuse_results = MagicMock(return_value=[])
    service._determine_strategy = MagicMock(return_value="vector_only")

    query = SearchQuery(
        query="anything",
        tenant_id="t1",
        top_k=10,
        enable_hybrid=True,
        enable_query_intent=True,
    )
    await service.search(query)

    passed_query = service._fan_out_search.call_args[0][0]
    assert passed_query.top_k == 10
    assert passed_query.enable_hybrid is True
