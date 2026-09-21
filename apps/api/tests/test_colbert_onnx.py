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
