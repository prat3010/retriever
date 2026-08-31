from src.domain.retrieval.sparse_vectorizer import SublinearSparseEngine


def test_sparse_vectorizer_tokenization():
    engine = SublinearSparseEngine()
    tokens = engine.tokenize("async function parseIntent(tenant_id: string, models.py)")

    assert "async" in tokens
    assert "parseintent" in tokens
    assert "parse" in tokens
    assert "intent" in tokens
    assert "tenant_id" in tokens
    assert "tenant" in tokens
    assert "id" in tokens
    assert "models.py" in tokens
    assert "models" in tokens
    assert "py" in tokens


def test_sparse_vectorizer_bm25_scoring():
    engine = SublinearSparseEngine(sublinear_tf=True)

    docs = [
        ("doc-1", "FastAPI microservices architecture with pgvector similarity search."),
        ("doc-2", "Commercial legal escrow contracts and milestone deliverables SOW."),
        ("doc-3", "PostgreSQL database indexing and sublinear BM25 ranking algorithm."),
    ]

    engine.index_documents(docs)

    results_code = engine.score_query_bm25("FastAPI pgvector microservices", top_k=5)
    assert len(results_code) > 0
    assert results_code[0].chunk_id == "doc-1"
    assert "fastapi" in results_code[0].matched_terms

    results_legal = engine.score_query_bm25("escrow deliverables SOW", top_k=5)
    assert len(results_legal) > 0
    assert results_legal[0].chunk_id == "doc-2"
    assert "escrow" in results_legal[0].matched_terms


def test_sparse_vectorizer_empty_and_oov():
    engine = SublinearSparseEngine()
    engine.index_documents([])
    assert engine.score_query_bm25("any query") == []

    docs = [("c1", "sample text content")]
    engine.index_documents(docs)
    assert engine.score_query_bm25("completely_unmatched_term_xyz") == []
