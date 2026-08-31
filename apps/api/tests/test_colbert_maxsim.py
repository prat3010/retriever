"""Unit tests for Milestone 70: Late-Interaction (ColBERT) Token-Level MaxSim Reranker."""
from unittest.mock import MagicMock, patch

import pytest

from src.adapters.cognitive.local_reranker_adapter import (
    ColBertMaxSimRerankerAdapter,
)
from src.adapters.cognitive.tei_reranker_adapter import TeiRerankerAdapter
from src.domain.abstractions.retrieval import SearchResult
from src.domain.retrieval.colbert_engine import (
    compute_colbert_maxsim,
    score_colbert_maxsim,
    tokenize_technical_terms,
)


def test_tokenize_technical_terms() -> None:
    """Verify tokenizer decomposes camelCase, snake_case, and technical identifiers."""
    tokens = tokenize_technical_terms("calcQuote tenant_id ORD-2026-X1 v0.55.0")
    assert "calcquote" in tokens
    assert "calc" in tokens
    assert "quote" in tokens
    assert "tenant_id" in tokens
    assert "tenant" in tokens
    assert "id" in tokens
    assert "ord" in tokens


def test_compute_colbert_maxsim_exact_match() -> None:
    """Verify exact token match produces high MaxSim similarity."""
    q_tokens = ["calc", "quote", "pricing"]
    d_tokens = ["function", "calc", "quote", "computes", "pricing", "tier"]

    score = compute_colbert_maxsim(q_tokens, d_tokens)
    assert score == 1.0


def test_compute_colbert_maxsim_partial_and_empty() -> None:
    """Verify empty and partial token match behavior."""
    assert compute_colbert_maxsim([], ["any"]) == 0.0
    assert compute_colbert_maxsim(["any"], []) == 0.0

    score = compute_colbert_maxsim(["quantum", "teleportation"], ["apple", "banana"])
    assert 0.0 <= score < 1.0


def test_score_colbert_maxsim_boosts_technical_identifiers() -> None:
    """Verify candidate with exact technical identifiers is boosted over generic candidates."""
    query = "calcQuote algorithm pricing"

    cand_generic = SearchResult(
        chunk_id="chk-1",
        document_id="doc-1",
        content="General commercial pricing structures and billing rates.",
        score=0.85,  # High dense vector score initially
    )
    cand_exact_code = SearchResult(
        chunk_id="chk-2",
        document_id="doc-1",
        content="The calcQuote function resolves dependencies and calculates quote totals.",
        score=0.65,  # Lower dense score initially
    )

    results = score_colbert_maxsim(
        query=query,
        candidates=[cand_generic, cand_exact_code],
        top_n=2,
        initial_weight=0.3,
        maxsim_weight=0.7,
    )

    # After ColBERT MaxSim reranking, candidate 2 (with calcQuote) is ranked #1
    assert len(results) == 2
    assert results[0].chunk_id == "chk-2"
    assert results[0].score > results[1].score


@pytest.mark.asyncio
async def test_colbert_maxsim_adapter_async() -> None:
    """Verify ColBertMaxSimRerankerAdapter reranks and filters by threshold."""
    adapter = ColBertMaxSimRerankerAdapter(initial_weight=0.4, maxsim_weight=0.6)

    query = "tenant_id postgres isolation"
    cands = [
        SearchResult(chunk_id="c1", document_id="d1", content="Tenant isolation via tenant_id in postgres.", score=0.6),
        SearchResult(chunk_id="c2", document_id="d1", content="Unrelated garden recipe.", score=0.2),
    ]

    reranked = await adapter.rerank(query=query, candidates=cands, top_n=2, threshold=0.4)
    assert len(reranked) >= 1
    assert reranked[0].chunk_id == "c1"


@pytest.mark.asyncio
async def test_tei_reranker_adapter_success() -> None:
    """Verify TeiRerankerAdapter successfully parses HTTP response."""
    adapter = TeiRerankerAdapter(endpoint_url="http://tei-reranker:8080")

    cands = [
        SearchResult(chunk_id="c1", document_id="d1", content="Text 1", score=0.5),
        SearchResult(chunk_id="c2", document_id="d1", content="Text 2", score=0.4),
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = [
        {"index": 1, "score": 0.95},
        {"index": 0, "score": 0.82},
    ]

    async def _mock_post(*args, **kwargs):
        return mock_resp

    with patch("httpx.AsyncClient.post", side_effect=_mock_post):
        reranked = await adapter.rerank("test query", cands, top_n=2, threshold=0.5)
        assert len(reranked) == 2
        assert reranked[0].chunk_id == "c2"
        assert reranked[0].score == 0.95


@pytest.mark.asyncio
async def test_tei_reranker_adapter_fallback_to_colbert() -> None:
    """Verify TeiRerankerAdapter falls back to local ColBERT MaxSim on network failure."""
    adapter = TeiRerankerAdapter(endpoint_url="http://unreachable-tei:8080")

    cands = [
        SearchResult(chunk_id="c1", document_id="d1", content="General docs", score=0.7),
        SearchResult(chunk_id="c2", document_id="d1", content="Specialized calcQuote logic", score=0.5),
    ]

    async def _mock_post_fail(*args, **kwargs):
        raise RuntimeError("Connection refused")

    with patch("httpx.AsyncClient.post", side_effect=_mock_post_fail):
        reranked = await adapter.rerank("calcQuote", cands, top_n=2, threshold=0.0)
        assert len(reranked) == 2
        assert reranked[0].chunk_id == "c2"


def test_batch_colbert_maxsim_engine() -> None:
    """Verify BatchColbertMaxSimEngine computes batch tensor MaxSim scores across multiple documents."""
    from src.domain.retrieval.colbert_engine import BatchColbertMaxSimEngine

    engine = BatchColbertMaxSimEngine(dim=128)
    q_tokens = ["postgres", "rls", "security"]
    doc_batches = [
        ["unrelated", "cooking", "recipe"],
        ["postgres", "database", "rls", "row", "level", "security"],
        ["general", "software", "development"],
    ]

    scores = engine.batch_maxsim(q_tokens, doc_batches)
    assert len(scores) == 3
    # Doc 2 has exact matches for all 3 query tokens -> 1.0
    assert scores[1] == 1.0
    # Doc 1 and Doc 3 have lower scores
    assert scores[1] > scores[0]
    assert scores[1] > scores[2]

