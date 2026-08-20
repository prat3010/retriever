"""Unit tests for Phase 1 RAG Modernization components."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.cognitive.query_rewriter_adapter import LLMQueryRewriterAdapter
from src.domain.abstractions.retrieval import SearchResult
from src.domain.inference.citation_validator import CitationValidator
from src.domain.ingestion.chunker_factory import (
    ChunkerFactory,
    ContextualChunker,
    SlidingChunker,
)
from src.domain.retrieval.search_service import HybridSearchService


def test_contextual_chunker_prepending():
    """Verify ContextualChunker prepends document context header to every chunk."""
    base_chunker = SlidingChunker()
    chunker = ContextualChunker(base_chunker=base_chunker, context_prefix="Q3 Financial Audit")

    text = "Revenue grew by 24% year-over-year in the enterprise segment."
    chunks = chunker.split_text_with_offsets(text, chunk_size=100, chunk_overlap=10)

    assert len(chunks) > 0
    assert "[Context: Q3 Financial Audit]" in chunks[0]["content"]
    assert chunks[0]["meta_data"]["context_prepended"] is True
    assert chunks[0]["meta_data"]["context_prefix"] == "Q3 Financial Audit"


def test_chunker_factory_contextual_strategy():
    """Verify ChunkerFactory instantiates ContextualChunker when requested."""
    chunker = ChunkerFactory.get_chunker(strategy="contextual", context_prefix="API Reference")
    assert isinstance(chunker, ContextualChunker)


def test_normalized_rrf_hybrid_fusion():
    """Verify normalized RRF score fusion balances vector and keyword search results."""
    vec_results = [
        SearchResult(chunk_id="c1", document_id="d1", content="Vec 1", score=0.95),
        SearchResult(chunk_id="c2", document_id="d1", content="Vec 2", score=0.60),
    ]
    kw_results = [
        SearchResult(chunk_id="c2", document_id="d1", content="Kw 2", score=5.0),
        SearchResult(chunk_id="c3", document_id="d2", content="Kw 3", score=1.0),
    ]

    search_svc = HybridSearchService(
        vector_search=MagicMock(),
        keyword_search=MagicMock(),
        embedder=MagicMock(),
        reranker=MagicMock(),
    )

    fused = search_svc._fuse_normalized_hybrid(vec_results, kw_results, rrf_k=60)
    assert len(fused) == 3
    chunk_ids = [r.chunk_id for r in fused]
    assert "c1" in chunk_ids and "c2" in chunk_ids and "c3" in chunk_ids


@pytest.mark.asyncio
async def test_multi_query_decomposition():
    """Verify LLMQueryRewriterAdapter generates sub-queries for multi-query decomposition."""
    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(return_value=MagicMock(content="Subquery 1\nSubquery 2\nSubquery 3"))

    rewriter = LLMQueryRewriterAdapter(llm=mock_llm)
    subqueries = await rewriter.rewrite_multi_query("Compare compliance risks")

    assert len(subqueries) == 3
    assert subqueries[0] == "Subquery 1"


def test_sentence_attribution_verification():
    """Verify CitationValidator validates sentence claims against chunk content."""
    validator = CitationValidator()
    validator.set_valid_ids(["c1", "c2"])

    chunk_contents = {
        "c1": "The company reported revenue growth of 25% in Q4 2025.",
        "c2": "Unrelated paragraph about office locations.",
    }

    claim = "The company reported 25% revenue growth [Source: c1]"
    attribution = validator.validate_sentence_attribution(claim, chunk_contents)

    assert attribution.get("c1") is True
