"""Unit and integration tests for Milestone 69: Pre-Chunk Contextual Retrieval Ingestion Engine."""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.cognitive.contextual_header_adapter import (
    ContextualHeaderGeneratorAdapter,
)
from src.domain.abstractions.contextual_retrieval import (
    ContextualChunk,
    ContextualHeaderGeneratorPort,
)


def test_contextual_domain_abstractions():
    """Verify domain abstractions and data structures."""
    chunk = ContextualChunk(
        chunk_id="chk-1",
        document_id="doc-1",
        tenant_id="tenant-1",
        raw_content="Baseline engineering deliverable scope.",
        context_header="[Context: SOW contract scope]",
        contextualized_content="[Context: SOW contract scope]\nBaseline engineering deliverable scope.",
        token_count=15,
        chunk_index=0,
        meta_data={"key": "val"},
    )
    assert chunk.chunk_id == "chk-1"
    assert chunk.context_header == "[Context: SOW contract scope]"
    assert issubclass(ContextualHeaderGeneratorAdapter, ContextualHeaderGeneratorPort)


@pytest.mark.asyncio
async def test_contextual_header_single_success():
    """Verify single chunk situational context generation via LLM."""
    adapter = ContextualHeaderGeneratorAdapter(api_key="mock-key")

    mock_chat_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "This document is a technical architecture specification for the Retriever engine."
    mock_chat_completion.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_chat_completion)

    with patch.object(adapter, "_get_client", return_value=mock_client):
        header = await adapter.generate_context_header_single(
            document_text="Full architecture specification for high-scale RAG systems.",
            chunk_content="The pgvector HNSW index configuration.",
            tenant_id="tn_test_1",
            doc_metadata={"filename": "arch_spec.pdf", "doc_type": "Technical Specification"},
        )

        assert header == "[Context: This document is a technical architecture specification for the Retriever engine.]"
        mock_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_contextual_header_strips_hallucinated_brackets():
    """Verify adapter cleans up redundant bracket syntax if returned by model."""
    adapter = ContextualHeaderGeneratorAdapter(api_key="mock-key")

    mock_chat_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "[Context: Financial statements for Q3 2026]"
    mock_chat_completion.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_chat_completion)

    with patch.object(adapter, "_get_client", return_value=mock_client):
        header = await adapter.generate_context_header_single(
            document_text="Q3 2026 Earnings Report...",
            chunk_content="Net profit rose by 14% year over year.",
            tenant_id="tn_test_1",
            doc_metadata={"filename": "earnings.pdf"},
        )

        assert header == "[Context: Financial statements for Q3 2026]"


@pytest.mark.asyncio
async def test_contextual_header_fallback_on_llm_exception():
    """Verify graceful fallback to document metadata header on LLM timeout or error."""
    adapter = ContextualHeaderGeneratorAdapter(api_key="mock-key")

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("LLM API Timeout"))

    with patch.object(adapter, "_get_client", return_value=mock_client):
        header = await adapter.generate_context_header_single(
            document_text="Q3 2026 Earnings Report...",
            chunk_content="Net profit rose by 14% year over year.",
            tenant_id="tn_test_1",
            doc_metadata={
                "filename": "earnings.pdf",
                "doc_type": "Financial Report",
                "topics": ["Revenue", "Earnings", "Growth"],
            },
        )

        assert header == "[Context: earnings.pdf (Financial Report regarding Revenue, Earnings, Growth)]"


@pytest.mark.asyncio
async def test_contextual_header_batch_generation():
    """Verify concurrent batch generation across multiple chunks."""
    adapter = ContextualHeaderGeneratorAdapter(api_key="mock-key", max_concurrent=3)

    mock_chat_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Summary of Section"
    mock_chat_completion.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_chat_completion)

    with patch.object(adapter, "_get_client", return_value=mock_client):
        headers = await adapter.generate_context_headers(
            document_text="Full Document Text...",
            chunks=["Chunk 1 content", "Chunk 2 content", "Chunk 3 content"],
            tenant_id="tn_test_1",
            doc_metadata={"filename": "doc.pdf"},
        )

        assert len(headers) == 3
        assert all(h == "[Context: Summary of Section]" for h in headers)
        assert mock_client.chat.completions.create.call_count == 3


@pytest.mark.asyncio
@patch("workers.src.tasks._publish_event", autospec=True)
@patch("workers.src.tasks.create_async_engine", autospec=True)
@patch("workers.src.tasks.extract_text_from_file", return_value="Paragraph 1 about system architecture. Paragraph 2 about database indexes.")
async def test_worker_ingestion_with_contextual_retrieval(
    mock_extract, mock_create_engine, mock_publish_event
):
    """Verify Celery document processing worker enriches chunks with contextual headers."""
    from workers.src.tasks import process_document_async

    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    mock_create_engine.return_value = mock_engine

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_engine.begin.return_value = mock_ctx

    mock_result = MagicMock()
    config_row = (json.dumps({
        "chunking_settings": {
            "enable_contextual_retrieval": True,
            "strategy": "fixed_window",
            "chunk_size": 200,
            "chunk_overlap": 20,
        },
        "ai_provider": {
            "api_key": "mock-ai-key",
            "default_model": "gemini-1.5-flash",
        }
    }),)
    mock_result.fetchone.return_value = config_row
    mock_conn.execute = AsyncMock(return_value=mock_result)

    with patch(
        "src.adapters.cognitive.contextual_header_adapter.ContextualHeaderGeneratorAdapter.generate_context_headers",
        new=AsyncMock(return_value=["[Context: Engineering Architecture Spec]"]),
    ):
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "Test content"
            await process_document_async(doc_id, tenant_id, "/tmp/test_spec.pdf", "application/pdf")

    # Verify that database execute was called with enriched chunk parameters
    executed_sql_calls = mock_conn.execute.call_args_list
    assert len(executed_sql_calls) >= 2

    # Find the chunk insert call
    insert_call = None
    for call in executed_sql_calls:
        args = call[0]
        if len(args) > 1 and isinstance(args[1], list) and len(args[1]) > 0 and "chunk_id" in args[1][0]:
            insert_call = args[1]
            break

    assert insert_call is not None
    chunk_record = insert_call[0]
    assert chunk_record["content"].startswith("[Context:")
    meta = json.loads(chunk_record["meta_data"])
    assert meta.get("is_contextualized") is True
    assert "raw_content" in meta
    assert meta.get("context_header") == "[Context: Engineering Architecture Spec]"


@pytest.mark.asyncio
async def test_contextual_header_empty_choices_handled():
    """Verify adapter falls back to metadata header when LLM returns empty choices array."""
    adapter = ContextualHeaderGeneratorAdapter(api_key="mock-key")

    mock_chat_completion = MagicMock()
    mock_chat_completion.choices = []  # Empty choices

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_chat_completion)

    with patch.object(adapter, "_get_client", return_value=mock_client):
        header = await adapter.generate_context_header_single(
            document_text="Sample system document...",
            chunk_content="Sample paragraph content.",
            tenant_id="tn_test_1",
            doc_metadata={"filename": "system.md", "doc_type": "Markdown Spec"},
        )
        assert header == "[Context: system.md (Markdown Spec)]"


@pytest.mark.asyncio
async def test_contextual_header_content_filter_safety():
    """Verify adapter handles finish_reason == 'content_filter' with None content gracefully."""
    adapter = ContextualHeaderGeneratorAdapter(api_key="mock-key")

    mock_chat_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = None  # None content due to safety filter
    mock_choice.finish_reason = "content_filter"
    mock_chat_completion.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_chat_completion)

    with patch.object(adapter, "_get_client", return_value=mock_client):
        header = await adapter.generate_context_header_single(
            document_text="Sample text content...",
            chunk_content="Restricted or filtered content.",
            tenant_id="tn_test_1",
            doc_metadata={"filename": "doc.pdf", "doc_type": "PDF Guide"},
        )
        assert header == "[Context: doc.pdf (PDF Guide)]"
