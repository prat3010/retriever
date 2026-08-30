"""Unit tests for Milestone 71: Corrective RAG (CRAG) & Agentic Reflection Loop."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.cognitive.corrective_retrieval_adapter import (
    LLMCorrectiveRetrievalAdapter,
)
from src.domain.abstractions.config import (
    CorrectiveRetrievalSettings,
    TenantConfiguration,
)
from src.domain.abstractions.retrieval import (
    CorrectiveRetrievalDecision,
    SearchQuery,
    SearchResult,
)
from src.domain.retrieval.corrective_retrieval_service import (
    CorrectiveRetrievalService,
)
from src.domain.retrieval.document_refiner import (
    refine_document_content,
    refine_search_results,
    split_into_sentences,
)


def _make_result(chunk_id: str, content: str, score: float = 0.8) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        document_id=str(uuid.uuid4()),
        content=content,
        score=score,
        metadata={},
    )


def test_document_refiner_sentence_splitting_and_filtering() -> None:
    """Verify document refiner extracts high-relevance sentences answering the query."""
    text = (
        "Welcome to the portal. This is standard header text. "
        "The calcQuote engine computes total costs and discounts for client projects. "
        "Please read our privacy terms carefully. Thank you for your business."
    )
    query = "calcQuote discounts"

    sentences = split_into_sentences(text)
    assert len(sentences) >= 3

    refined = refine_document_content(query, text, max_sentences=2)
    assert "calcQuote" in refined
    assert "discounts" in refined
    # Noisy footer was filtered out
    assert "Thank you for your business" not in refined


def test_refine_search_results_metadata() -> None:
    """Verify refine_search_results sets is_refined metadata tag."""
    cands = [
        _make_result("c1", "Sentence 1 is long enough to split. Sentence 2 has pricing details."),
    ]
    refined = refine_search_results("pricing", cands)
    assert len(refined) == 1
    assert refined[0].metadata.get("is_refined") is True


@pytest.mark.asyncio
async def test_crag_prepare_context_correct_branch() -> None:
    """Verify CORRECT branch refines documents without secondary search."""
    mock_search = AsyncMock()
    initial_chunks = [
        _make_result("c1", "Exact information about project escrow milestone releases.", score=0.9),
    ]
    resp = MagicMock()
    resp.results = initial_chunks
    mock_search.search = AsyncMock(return_value=resp)

    mock_provider = AsyncMock()
    mock_provider.evaluate_candidates = AsyncMock(
        return_value=CorrectiveRetrievalDecision(
            status="CORRECT",
            confidence_score=0.95,
            needs_re_retrieval=False,
            needs_web_search=False,
        )
    )

    mock_orch = AsyncMock()
    svc = CorrectiveRetrievalService(
        search_service=mock_search,
        orchestrator=mock_orch,
        corrective_provider=mock_provider,
    )

    tc = TenantConfiguration(tenant_id="test-tenant")
    tc.corrective_retrieval_settings = CorrectiveRetrievalSettings(
        enable_corrective_retrieval=True,
        confidence_threshold=0.75,
    )
    sq = SearchQuery(query="escrow milestone", tenant_id="test-tenant")

    results, decision = await svc.prepare_crag_context(
        tenant_id="test-tenant",
        query="escrow milestone",
        search_query=sq,
        tenant_config=tc,
    )

    assert decision.status == "CORRECT"
    assert len(results) == 1
    assert mock_search.search.call_count == 1


@pytest.mark.asyncio
async def test_crag_prepare_context_ambiguous_branch() -> None:
    """Verify AMBIGUOUS branch triggers secondary search and fuses evidence."""
    mock_search = AsyncMock()
    initial_chunks = [
        _make_result("c1", "Partial local notes on topic.", score=0.5),
    ]
    web_chunks = [
        _make_result("w1", "External web search results with fresh details.", score=0.85),
    ]

    resp1 = MagicMock(results=initial_chunks)
    resp2 = MagicMock(results=web_chunks)
    mock_search.search = AsyncMock(side_effect=[resp1, resp2])

    mock_provider = AsyncMock()
    mock_provider.evaluate_candidates = AsyncMock(
        return_value=CorrectiveRetrievalDecision(
            status="AMBIGUOUS",
            confidence_score=0.55,
            needs_re_retrieval=True,
            needs_web_search=True,
            reformulated_query="reformulated query",
        )
    )

    mock_orch = AsyncMock()
    svc = CorrectiveRetrievalService(
        search_service=mock_search,
        orchestrator=mock_orch,
        corrective_provider=mock_provider,
    )

    tc = TenantConfiguration(tenant_id="test-tenant")
    sq = SearchQuery(query="initial query", tenant_id="test-tenant")

    results, decision = await svc.prepare_crag_context(
        tenant_id="test-tenant",
        query="initial query",
        search_query=sq,
        tenant_config=tc,
    )

    assert decision.status == "AMBIGUOUS"
    assert len(results) == 2
    assert mock_search.search.call_count == 2


@pytest.mark.asyncio
async def test_crag_prepare_context_incorrect_branch() -> None:
    """Verify INCORRECT branch suppresses internal chunks and returns web results."""
    mock_search = AsyncMock()
    internal_irrelevant = [
        _make_result("c1", "Irrelevant recipe book content.", score=0.2),
    ]
    web_fallback = [
        _make_result("w1", "Accurate web answer about the query.", score=0.9),
    ]

    resp1 = MagicMock(results=internal_irrelevant)
    resp2 = MagicMock(results=web_fallback)
    mock_search.search = AsyncMock(side_effect=[resp1, resp2])

    mock_provider = AsyncMock()
    mock_provider.evaluate_candidates = AsyncMock(
        return_value=CorrectiveRetrievalDecision(
            status="INCORRECT",
            confidence_score=0.15,
            needs_re_retrieval=True,
            needs_web_search=True,
            reformulated_query="corrected query",
        )
    )

    mock_orch = AsyncMock()
    svc = CorrectiveRetrievalService(
        search_service=mock_search,
        orchestrator=mock_orch,
        corrective_provider=mock_provider,
    )

    tc = TenantConfiguration(tenant_id="test-tenant")
    sq = SearchQuery(query="query", tenant_id="test-tenant")

    results, decision = await svc.prepare_crag_context(
        tenant_id="test-tenant",
        query="query",
        search_query=sq,
        tenant_config=tc,
    )

    assert decision.status == "INCORRECT"
    assert len(results) == 1
    assert results[0].chunk_id == "w1"


@pytest.mark.asyncio
async def test_llm_corrective_adapter_evaluate_candidates_heuristic() -> None:
    """Verify LLMCorrectiveRetrievalAdapter heuristic fallback on LLM failure."""
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

    adapter = LLMCorrectiveRetrievalAdapter(llm=mock_llm)
    cands = [
        _make_result("c1", "Good text", score=0.85),
    ]

    decision = await adapter.evaluate_candidates(
        query="test query",
        candidates=cands,
        upper_threshold=0.75,
        lower_threshold=0.40,
    )

    assert decision.status == "CORRECT"
    assert decision.confidence_score >= 0.75
