"""Tests for M24: Self-Querying Retrieval."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.abstractions.inference import (
    InferenceResponse,
    LlmProvider,
    Usage,
)
from src.domain.abstractions.retrieval import (
    MetadataFilter,
    SearchQuery,
    SelfQueryProvider,
)
from src.domain.retrieval.search_service import HybridSearchService

# ── Step 1: SelfQueryProvider abstraction ─────────────────────────────


def test_self_query_provider_abstract() -> None:
    assert hasattr(SelfQueryProvider, "parse_query")


# ── Step 2: LLMSelfQueryAdapter ───────────────────────────────────────


@pytest.mark.asyncio
async def test_adapter_parses_filters() -> None:
    from src.adapters.cognitive.self_query_adapter import LLMSelfQueryAdapter

    mock_llm = AsyncMock(spec=LlmProvider)
    mock_llm.generate.return_value = InferenceResponse(
        content='[{"field": "doc_type", "operator": "eq", "value": "invoice"}, {"field": "date_reference", "operator": "eq", "value": "2025"}]',
        usage=Usage(input_tokens=30, output_tokens=15),
    )

    adapter = LLMSelfQueryAdapter(llm=mock_llm, model="gemini-1.5-flash")
    result = await adapter.parse_query("invoices from 2025")

    assert len(result) == 2
    assert result[0].field == "doc_type"
    assert result[0].operator == "eq"
    assert result[0].value == "invoice"
    assert result[1].field == "date_reference"
    assert result[1].value == "2025"


@pytest.mark.asyncio
async def test_adapter_returns_empty_on_no_match() -> None:
    from src.adapters.cognitive.self_query_adapter import LLMSelfQueryAdapter

    mock_llm = AsyncMock(spec=LlmProvider)
    mock_llm.generate.return_value = InferenceResponse(
        content="[]",
        usage=Usage(input_tokens=10, output_tokens=3),
    )

    adapter = LLMSelfQueryAdapter(llm=mock_llm, model="gemini-1.5-flash")
    result = await adapter.parse_query("what is the budget?")

    assert result == []


@pytest.mark.asyncio
async def test_adapter_graceful_on_invalid_json() -> None:
    from src.adapters.cognitive.self_query_adapter import LLMSelfQueryAdapter

    mock_llm = AsyncMock(spec=LlmProvider)
    mock_llm.generate.return_value = InferenceResponse(
        content="not json at all",
        usage=Usage(input_tokens=5, output_tokens=2),
    )

    adapter = LLMSelfQueryAdapter(llm=mock_llm, model="gemini-1.5-flash")
    result = await adapter.parse_query("some random query")

    assert result == []


@pytest.mark.asyncio
async def test_adapter_graceful_on_llm_error() -> None:
    from src.adapters.cognitive.self_query_adapter import LLMSelfQueryAdapter

    mock_llm = AsyncMock(spec=LlmProvider)
    mock_llm.generate.side_effect = RuntimeError("LLM unavailable")

    adapter = LLMSelfQueryAdapter(llm=mock_llm, model="gemini-1.5-flash")
    result = await adapter.parse_query("any query")

    assert result == []


# ── Step 3: HybridSearchService integration ───────────────────────────


@pytest.mark.asyncio
async def test_search_injects_parsed_filters_when_enabled() -> None:
    mock_self_query = AsyncMock(spec=SelfQueryProvider)
    mock_self_query.parse_query.return_value = [
        MetadataFilter(field="doc_type", operator="eq", value="invoice"),
    ]

    service = HybridSearchService(
        vector_search=AsyncMock(),
        keyword_search=AsyncMock(),
        embedder=AsyncMock(),
        reranker=AsyncMock(),
        self_query=mock_self_query,
    )
    service._fan_out_search = AsyncMock(return_value=([], []))  # type: ignore
    service._fuse_results = MagicMock(return_value=[])
    service._determine_strategy = MagicMock(return_value="vector_only")

    query = SearchQuery(
        query="invoices from 2025",
        tenant_id="t1",
        enable_self_query=True,
    )
    await service.search(query)

    mock_self_query.parse_query.assert_called_once_with("invoices from 2025")
    passed_query = service._fan_out_search.call_args[0][0]
    assert len(passed_query.filters) == 1
    assert passed_query.filters[0].field == "doc_type"


@pytest.mark.asyncio
async def test_search_skips_self_query_when_disabled() -> None:
    mock_self_query = AsyncMock(spec=SelfQueryProvider)

    service = HybridSearchService(
        vector_search=AsyncMock(),
        keyword_search=AsyncMock(),
        embedder=AsyncMock(),
        reranker=AsyncMock(),
        self_query=mock_self_query,
    )
    service._fan_out_search = AsyncMock(return_value=([], []))  # type: ignore
    service._fuse_results = MagicMock(return_value=[])
    service._determine_strategy = MagicMock(return_value="vector_only")

    query = SearchQuery(query="invoices from 2025", tenant_id="t1", enable_self_query=False)
    await service.search(query)

    mock_self_query.parse_query.assert_not_called()


@pytest.mark.asyncio
async def test_search_skips_when_no_provider() -> None:
    service = HybridSearchService(
        vector_search=AsyncMock(),
        keyword_search=AsyncMock(),
        embedder=AsyncMock(),
        reranker=AsyncMock(),
        self_query=None,
    )
    service._fan_out_search = AsyncMock(return_value=([], []))  # type: ignore
    service._fuse_results = MagicMock(return_value=[])
    service._determine_strategy = MagicMock(return_value="vector_only")

    query = SearchQuery(query="invoices from 2025", tenant_id="t1", enable_self_query=True)
    await service.search(query)

    # No error thrown — gracefully skips


@pytest.mark.asyncio
async def test_search_merges_parsed_with_existing_filters() -> None:
    mock_self_query = AsyncMock(spec=SelfQueryProvider)
    mock_self_query.parse_query.return_value = [
        MetadataFilter(field="date_reference", operator="eq", value="2025"),
    ]

    service = HybridSearchService(
        vector_search=AsyncMock(),
        keyword_search=AsyncMock(),
        embedder=AsyncMock(),
        reranker=AsyncMock(),
        self_query=mock_self_query,
    )
    service._fan_out_search = AsyncMock(return_value=([], []))  # type: ignore
    service._fuse_results = MagicMock(return_value=[])
    service._determine_strategy = MagicMock(return_value="vector_only")

    query = SearchQuery(
        query="invoices from 2025",
        tenant_id="t1",
        enable_self_query=True,
        filters=[MetadataFilter(field="doc_type", operator="eq", value="invoice")],
    )
    await service.search(query)

    passed_query = service._fan_out_search.call_args[0][0]
    assert len(passed_query.filters) == 2
    assert passed_query.filters[0].field == "doc_type"
    assert passed_query.filters[1].field == "date_reference"
