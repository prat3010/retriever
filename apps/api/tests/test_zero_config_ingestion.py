"""Unit test suite for Zero-Config Self-Adaptive Ingestion Pipeline."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.ingestion.sync_ingestion_service import ingest_file_sync


@pytest.mark.asyncio
async def test_zero_config_python_ast_ingestion() -> None:
    """Verify python code files automatically use AST chunker and get contextual prefix."""
    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    filename = "service.py"
    code_content = b"def process_data(x):\n    return x * 2\n\nclass DataHandler:\n    pass\n"

    embedder = AsyncMock()
    embedder.embed_batch.side_effect = lambda texts: [[0.1] * 1536 for _ in texts]

    mock_doc = MagicMock()
    mock_doc.collection_id = None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_doc

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    with patch("src.adapters.ingestion.sync_ingestion_service.tenant_session") as mock_tenant_session:
        mock_tenant_session.return_value.__aenter__.return_value = mock_session

        chunk_count = await ingest_file_sync(
            tenant_id=tenant_id,
            document_id=doc_id,
            filename=filename,
            file_content=code_content,
            file_hash="hash123",
            mime_type="text/x-python",
            embedder=embedder,
        )

        assert chunk_count > 0
        assert embedder.embed_batch.called
        texts_embedded = embedder.embed_batch.call_args[0][0]
        assert len(texts_embedded) == chunk_count
        assert all(t.startswith("[Document: service.py]\n") for t in texts_embedded)


@pytest.mark.asyncio
async def test_zero_config_markdown_ingestion() -> None:
    """Verify markdown files automatically use header-bounded chunking."""
    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    filename = "README.md"
    md_content = b"# Introduction\nWelcome to Retriever.\n\n## Features\n- Zero config RAG\n"

    embedder = AsyncMock()
    embedder.embed_batch.side_effect = lambda texts: [[0.2] * 1536 for _ in texts]

    mock_doc = MagicMock()
    mock_doc.collection_id = None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_doc

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    with patch("src.adapters.ingestion.sync_ingestion_service.tenant_session") as mock_tenant_session:
        mock_tenant_session.return_value.__aenter__.return_value = mock_session

        chunk_count = await ingest_file_sync(
            tenant_id=tenant_id,
            document_id=doc_id,
            filename=filename,
            file_content=md_content,
            file_hash="hash456",
            mime_type="text/markdown",
            embedder=embedder,
        )

        assert chunk_count >= 2
        texts_embedded = embedder.embed_batch.call_args[0][0]
        assert all(t.startswith("[Document: README.md]\n") for t in texts_embedded)


@pytest.mark.asyncio
async def test_zero_config_hierarchical_document_ingestion() -> None:
    """Verify standard document uploads use Hierarchical parent-child chunking with linked parent_chunk_id."""
    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    filename = "company_policy.txt"
    text_content = b"Paragraph 1. " * 300  # Multi-paragraph document text

    embedder = AsyncMock()
    embedder.embed_batch.side_effect = lambda texts: [[0.3] * 1536 for _ in texts]

    mock_doc = MagicMock()
    mock_doc.collection_id = None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_doc

    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    with patch("src.adapters.ingestion.sync_ingestion_service.tenant_session") as mock_tenant_session:
        mock_tenant_session.return_value.__aenter__.return_value = mock_session

        chunk_count = await ingest_file_sync(
            tenant_id=tenant_id,
            document_id=doc_id,
            filename=filename,
            file_content=text_content,
            file_hash="hash789",
            mime_type="text/plain",
            embedder=embedder,
        )

        assert chunk_count > 0
        added_chunks = [
            call.args[0]
            for call in mock_session.add.call_args_list
            if hasattr(call.args[0], "parent_chunk_id")
        ]
        assert len(added_chunks) == chunk_count
        child_chunks = [c for c in added_chunks if c.parent_chunk_id is not None]
        parent_chunks = [c for c in added_chunks if c.parent_chunk_id is None]

        assert len(child_chunks) > 0
        assert len(parent_chunks) > 0
        parent_ids = {p.chunk_id for p in parent_chunks}
        assert all(c.parent_chunk_id in parent_ids for c in child_chunks)
