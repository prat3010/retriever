"""Unit tests for Milestone 28: Interactive Chunking Auditor."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.domain.ingestion.chunker_factory import (
    ChunkerFactory,
    HierarchicalChunker,
    SemanticChunker,
    SlidingChunker,
)
from src.main import app

client = TestClient(app)


# ── 1. Sliding Window Chunker Character Offsets ──────────────────────────────


def test_sliding_chunker_character_offsets() -> None:
    """Verify SlidingChunker calculates start_char_idx and end_char_idx."""
    sample_text = (
        "Retrieval-Augmented Generation (RAG) is an AI framework for retrieving "
        "facts from an external knowledge base to ground Large Language Models."
    )
    chunker = SlidingChunker()
    chunks = chunker.split_text_with_offsets(sample_text, chunk_size=15, chunk_overlap=3)

    assert len(chunks) > 0
    for chunk in chunks:
        start = chunk["start_char_idx"]
        end = chunk["end_char_idx"]
        assert 0 <= start <= len(sample_text)
        assert start <= end <= len(sample_text) + 20
        assert chunk["token_count"] > 0
        assert chunk["char_count"] == len(chunk["content"])


# ── 2. Semantic Chunker Paragraph Boundaries ─────────────────────────────────


def test_semantic_chunker_boundaries() -> None:
    """Verify SemanticChunker preserves paragraph and structural boundaries."""
    sample_text = "Paragraph One about Python RAG.\n\nParagraph Two about PostgreSQL Vector Store."
    chunker = SemanticChunker()
    chunks = chunker.split_text_with_offsets(sample_text, chunk_size=8, chunk_overlap=0)

    assert len(chunks) == 2
    assert "Paragraph One" in chunks[0]["content"]
    assert "Paragraph Two" in chunks[1]["content"]


# ── 3. Hierarchical Chunker Parent-Child Relationships ────────────────────────


def test_hierarchical_chunker_parent_child() -> None:
    """Verify HierarchicalChunker attaches parent_chunk_index to child metadata."""
    sample_text = (
        "Parent Section Title.\n\nFirst detailed sentence explaining RAG architecture. "
        "Second detailed sentence explaining vector embeddings and pgvector storage."
    )
    chunker = HierarchicalChunker()
    chunks = chunker.split_text_with_offsets(sample_text, chunk_size=30, chunk_overlap=5)

    assert len(chunks) > 0
    for chunk in chunks:
        assert "parent_chunk_index" in chunk["meta_data"]
        assert chunk["meta_data"]["strategy"] == "hierarchical"


# ── 4. Chunker Factory Resolution ─────────────────────────────────────────────


def test_chunker_factory_resolution() -> None:
    """Verify ChunkerFactory resolves chunkers by strategy name."""
    assert isinstance(ChunkerFactory.get_chunker("sliding"), SlidingChunker)
    assert isinstance(ChunkerFactory.get_chunker("semantic"), SemanticChunker)
    assert isinstance(ChunkerFactory.get_chunker("hierarchical"), HierarchicalChunker)
    assert isinstance(ChunkerFactory.get_chunker("unknown"), SlidingChunker)


# ── 5. Admin Preview API Endpoint ──────────────────────────────────────────────


@patch("src.config.settings.ADMIN_MASTER_KEY", "test-admin-secret-key")
def test_admin_chunk_preview_endpoint() -> None:
    """Verify POST /v1/admin/tenants/{tenantId}/documents/chunk-preview endpoint."""
    headers = {"X-Admin-Master-Key": "test-admin-secret-key"}
    payload = {
        "text": "Antigravity RAG Platform audit sandbox test string.",
        "chunk_size": 20,
        "chunk_overlap": 2,
        "strategy": "sliding",
    }

    response = client.post(
        "/v1/admin/tenants/tenant_123/documents/chunk-preview",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert "totalChunks" in body
    assert "totalTokens" in body
    assert "chunks" in body
    assert body["totalChunks"] > 0
    first_chunk = body["chunks"][0]
    assert "startCharIdx" in first_chunk
    assert "endCharIdx" in first_chunk
    assert "charCount" in first_chunk
    assert "tokenCount" in first_chunk
