"""Unit tests for CitationValidator sentence span verification."""

from src.domain.inference.citation_validator import CitationValidator


def test_citation_validator_exact_spans():
    validator = CitationValidator()
    validator.set_valid_ids(["chunk_101", "chunk_102"])

    chunk_contents = {
        "chunk_101": "Retriever is built on a hexagonal architecture with PostgreSQL and pgvector.",
        "chunk_102": "It supports hybrid search with reciprocal rank fusion and Cohere reranking.",
    }

    text = "Retriever uses PostgreSQL and pgvector. [Source: chunk_101] It also supports hybrid search. [Source: chunk_102]"
    results = validator.validate_sentence_spans(text, chunk_contents)

    assert len(results) == 2
    assert results[0]["is_grounded"] is True
    assert "chunk_101" in results[0]["cited_chunk_ids"]
    assert results[1]["is_grounded"] is True
    assert "chunk_102" in results[1]["cited_chunk_ids"]


def test_citation_validator_unverified_claim():
    validator = CitationValidator()
    validator.set_valid_ids(["chunk_101"])

    chunk_contents = {
        "chunk_101": "Retriever is built on a hexagonal architecture with PostgreSQL.",
    }

    text = "The application uses quantum computing for retrieval. [Source: chunk_101]"
    results = validator.validate_sentence_spans(text, chunk_contents)

    assert len(results) == 1
    assert results[0]["is_grounded"] is False
