"""Tests for M21: Web Search Grounding."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.abstractions.retrieval import SearchQuery, SearchResult
from src.domain.abstractions.web_search import WebSearchResult


# ── Step 1: WebSearchProvider port + WebSearchResult model ──────────────────


def test_web_search_result_defaults() -> None:
    r = WebSearchResult()
    assert r.title == ""
    assert r.url == ""
    assert r.content == ""
    assert r.score == 1.0


def test_web_search_result_full() -> None:
    r = WebSearchResult(title="T", url="https://x.com", content="hello", score=0.9)
    assert r.title == "T"
    assert r.url == "https://x.com"
    assert r.content == "hello"
    assert r.score == 0.9


# ── Step 2: Tavily adapter ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tavily_adapter_no_key_returns_empty() -> None:
    from src.adapters.cognitive.tavily_adapter import TavilySearchAdapter

    adapter = TavilySearchAdapter(api_key="")
    results = await adapter.search("test")
    assert results == []


@pytest.mark.asyncio
async def test_tavily_adapter_success() -> None:
    from src.adapters.cognitive.tavily_adapter import TavilySearchAdapter

    adapter = TavilySearchAdapter(api_key="sk-test")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {"title": "Result 1", "url": "https://example.com/1", "content": "Content 1"},
            {"title": "Result 2", "url": "https://example.com/2", "content": "Content 2"},
        ]
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_response

        results = await adapter.search("test query", max_results=3)

    assert len(results) == 2
    assert results[0].title == "Result 1"
    assert results[0].url == "https://example.com/1"
    assert results[0].content == "Content 1"
    assert results[1].title == "Result 2"

    # Verify request payload
    call_kwargs = mock_client.post.call_args[1]
    assert call_kwargs["json"]["query"] == "test query"
    assert call_kwargs["json"]["max_results"] == 3


# ── Step 3: Config fields ───────────────────────────────────────────────────


def test_feature_flags_has_web_search() -> None:
    from src.domain.abstractions.config import FeatureFlags

    f = FeatureFlags()
    assert f.enable_web_search is False


def test_retrieval_settings_has_web_search_fields() -> None:
    from src.domain.abstractions.config import RetrievalSettings

    s = RetrievalSettings()
    assert s.web_search_threshold == 0.65
    assert s.web_search_provider == "tavily"
    assert s.web_search_max_results == 5


def test_search_query_has_web_search_fields() -> None:
    q = SearchQuery(query="test", tenant_id="t1")
    assert q.enable_web_search is False
    assert q.web_search_threshold == 0.65
    assert q.web_search_max_results == 5


# ── Step 4: Web search fallback in HybridSearchService ──────────────────────


def _make_result(chunk_id: str, score: float, content: str = "text") -> SearchResult:
    return SearchResult(chunk_id=chunk_id, document_id="d1", content=content, score=score, metadata={})


@pytest.mark.asyncio
async def test_web_search_triggers_on_low_scores() -> None:
    from src.domain.retrieval.search_service import HybridSearchService

    mock_web = AsyncMock()
    mock_web.search.return_value = [
        WebSearchResult(title="Web1", url="https://w.com/1", content="Web content 1"),
    ]

    mock_vector = AsyncMock()
    mock_vector.search_similar.return_value = [_make_result("local_1", 0.45)]

    service = HybridSearchService(
        vector_search=mock_vector,
        keyword_search=MagicMock(),
        embedder=AsyncMock(),
        reranker=MagicMock(),
        web_search=mock_web,
    )

    query = SearchQuery(
        query="test",
        tenant_id="t1",
        top_k=10,
        enable_hybrid=False,
        enable_reranking=False,
        enable_web_search=True,
        web_search_threshold=0.65,
    )

    response = await service.search(query)

    assert len(response.results) == 2
    web_results = [r for r in response.results if r.document_id == "__web__"]
    assert len(web_results) == 1
    assert "Web1" in web_results[0].content
    # Web result should have score below threshold
    assert web_results[0].score < 0.65
    # Local result should still rank first
    assert response.results[0].chunk_id == "local_1"


@pytest.mark.asyncio
async def test_web_search_skips_when_scores_above_threshold() -> None:
    from src.domain.retrieval.search_service import HybridSearchService

    mock_web = AsyncMock()

    mock_vector = AsyncMock()
    mock_vector.search_similar.return_value = [_make_result("local_1", 0.85)]

    service = HybridSearchService(
        vector_search=mock_vector,
        keyword_search=MagicMock(),
        embedder=AsyncMock(),
        reranker=MagicMock(),
        web_search=mock_web,
    )

    query = SearchQuery(
        query="test",
        tenant_id="t1",
        top_k=10,
        enable_hybrid=False,
        enable_reranking=False,
        enable_web_search=True,
        web_search_threshold=0.65,
    )

    response = await service.search(query)

    assert len(response.results) == 1
    assert response.results[0].chunk_id == "local_1"
    mock_web.search.assert_not_called()


@pytest.mark.asyncio
async def test_web_search_skips_when_flag_is_off() -> None:
    from src.domain.retrieval.search_service import HybridSearchService

    mock_web = AsyncMock()
    mock_vector = AsyncMock()
    mock_vector.search_similar.return_value = [_make_result("local_1", 0.3)]

    service = HybridSearchService(
        vector_search=mock_vector,
        keyword_search=MagicMock(),
        embedder=AsyncMock(),
        reranker=MagicMock(),
        web_search=mock_web,
    )

    query = SearchQuery(
        query="test",
        tenant_id="t1",
        top_k=10,
        enable_hybrid=False,
        enable_reranking=False,
        enable_web_search=False,
        web_search_threshold=0.65,
    )

    response = await service.search(query)

    assert len(response.results) == 1
    mock_web.search.assert_not_called()


@pytest.mark.asyncio
async def test_web_search_graceful_degradation() -> None:
    from src.domain.retrieval.search_service import HybridSearchService

    mock_web = AsyncMock()
    mock_web.search.side_effect = RuntimeError("API down")

    mock_vector = AsyncMock()
    mock_vector.search_similar.return_value = [_make_result("local_1", 0.3)]

    service = HybridSearchService(
        vector_search=mock_vector,
        keyword_search=MagicMock(),
        embedder=AsyncMock(),
        reranker=MagicMock(),
        web_search=mock_web,
    )

    query = SearchQuery(
        query="test",
        tenant_id="t1",
        top_k=10,
        enable_hybrid=False,
        enable_reranking=False,
        enable_web_search=True,
        web_search_threshold=0.65,
    )

    response = await service.search(query)

    # Should still return local results even when web search fails
    assert len(response.results) == 1
    assert response.results[0].chunk_id == "local_1"


@pytest.mark.asyncio
async def test_web_search_no_web_provider_configured() -> None:
    from src.domain.retrieval.search_service import HybridSearchService

    mock_vector = AsyncMock()
    mock_vector.search_similar.return_value = [_make_result("local_1", 0.3)]

    service = HybridSearchService(
        vector_search=mock_vector,
        keyword_search=MagicMock(),
        embedder=AsyncMock(),
        reranker=MagicMock(),
        web_search=None,
    )

    query = SearchQuery(
        query="test",
        tenant_id="t1",
        top_k=10,
        enable_hybrid=False,
        enable_reranking=False,
        enable_web_search=True,
        web_search_threshold=0.65,
    )

    response = await service.search(query)
    assert len(response.results) == 1
    assert response.results[0].chunk_id == "local_1"
