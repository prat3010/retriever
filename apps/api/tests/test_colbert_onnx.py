"""Tests for Neural ColBERT ONNX Engine with Late-Interaction MaxSim & Fallback."""

from unittest.mock import MagicMock

import pytest

from src.domain.abstractions.retrieval import SearchResult
from src.domain.retrieval.colbert_onnx_engine import NeuralColbertEngine


def test_neural_colbert_fallback_score_pair() -> None:
    """Verify fallback token MaxSim computes accurate scores without external fastembed dependencies."""
    engine = NeuralColbertEngine(neural_model=None)

    query = "tenant_id postgres rls"
    doc_match = "Enforcing tenant_id row level security in postgres tables."
    doc_other = "Apples and oranges fruit salad recipes."

    score_match = engine.score_pair(query, doc_match)
    score_other = engine.score_pair(query, doc_other)

    assert score_match > score_other
    assert 0.0 <= score_match <= 1.0


def test_neural_colbert_rerank_candidates() -> None:
    """Verify rerank_candidates reorders candidate results according to token MaxSim."""
    engine = NeuralColbertEngine(neural_model=None)

    query = "database connection pooling timeout"

    cand_generic = SearchResult(
        chunk_id="c1",
        document_id="d1",
        content="General guidelines for web application microservices.",
        score=0.85,
    )
    cand_relevant = SearchResult(
        chunk_id="c2",
        document_id="d2",
        content="Configuring database connection pooling timeout and max connections.",
        score=0.60,
    )

    reranked = engine.rerank_candidates(query, [cand_generic, cand_relevant], top_k=2)

    assert len(reranked) == 2
    # The relevant candidate should be boosted to the top
    assert reranked[0].chunk_id == "c2"
    assert reranked[0].score >= reranked[1].score


def test_neural_colbert_with_neural_model() -> None:
    """Verify neural model pathway when FastEmbed TextEmbedding is provided."""
    mock_model = MagicMock()
    # Mock embed() yielding embeddings
    # query: 2 tokens, doc: 3 tokens, dim: 4
    q_emb = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]]
    d_emb = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]]

    mock_model.embed = MagicMock(side_effect=[iter([q_emb]), iter([d_emb])])

    engine = NeuralColbertEngine(neural_model=mock_model)
    assert engine.is_neural is True

    score = engine.score_pair("test query", "test doc")
    # For query token 1: max dot product with doc is 1.0 (token 1)
    # For query token 2: max dot product with doc is 1.0 (token 2)
    # Mean max sim: 1.0
    assert pytest.approx(score, rel=1e-3) == 1.0


def test_neural_colbert_threshold_filtering() -> None:
    """Verify that rerank_candidates filters out candidates below the score threshold."""
    engine = NeuralColbertEngine(neural_model=None)

    cand_high = SearchResult(
        chunk_id="c1",
        document_id="d1",
        content="PostgreSQL pgvector row level security isolation",
        score=0.9,
    )
    cand_low = SearchResult(
        chunk_id="c2",
        document_id="d2",
        content="Banana strawberry blueberry smoothie recipe",
        score=0.1,
    )

    # With high threshold, low-scoring candidate should be dropped
    reranked = engine.rerank_candidates(
        query="PostgreSQL pgvector isolation",
        candidates=[cand_high, cand_low],
        top_k=5,
        threshold=0.6,
    )

    assert len(reranked) == 1
    assert reranked[0].chunk_id == "c1"


@pytest.mark.asyncio
async def test_hybrid_search_integration_with_colbert_engine() -> None:
    """Verify HybridSearchService delegates to NeuralColbertEngine when enable_colbert_rerank=True."""
    from unittest.mock import AsyncMock

    from src.domain.abstractions.retrieval import SearchQuery, SearchResponse
    from src.domain.retrieval.search_service import HybridSearchService

    mock_vector = MagicMock()
    mock_vector.search_similar = AsyncMock(
        return_value=[
            SearchResult(chunk_id="c1", document_id="d1", content="Postgres RLS", score=0.8)
        ]
    )
    mock_keyword = MagicMock()
    mock_keyword.search_keywords = AsyncMock(return_value=[])

    mock_embedder = MagicMock()
    mock_embedder.embed_text = AsyncMock(return_value=[0.1] * 768)

    mock_reranker = MagicMock()

    service = HybridSearchService(
        vector_search=mock_vector,
        keyword_search=mock_keyword,
        embedder=mock_embedder,
        reranker=mock_reranker,
    )

    query = SearchQuery(
        tenant_id="test_tenant",
        query="Postgres RLS",
        top_k=5,
        enable_hybrid=False,
        enable_bm25=False,
        enable_colbert_rerank=True,
    )

    resp: SearchResponse = await service.search(query)
    assert "_colbert_maxsim" in resp.search_meta.strategy
    assert len(resp.results) >= 1
