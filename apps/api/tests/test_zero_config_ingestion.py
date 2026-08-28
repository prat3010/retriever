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


def _create_mock_docx() -> bytes:
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
            <w:body>
                <w:p><w:r><w:t>This is a master services agreement.</w:t></w:r></w:p>
                <w:p><w:r><w:t>Section 1: Termination clause.</w:t></w:r></w:p>
            </w:body>
        </w:document>"""
        z.writestr("word/document.xml", xml)
    return buf.getvalue()


def _create_mock_xlsx() -> bytes:
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        sst = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="3" uniqueCount="3">
            <si><t>Month</t></si>
            <si><t>Revenue</t></si>
            <si><t>Jan</t></si>
        </sst>"""
        z.writestr("xl/sharedStrings.xml", sst)
        sheet = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
            <sheetData>
                <row r="1">
                    <c r="A1" t="s"><v>0</v></c>
                    <c r="B1" t="s"><v>1</v></c>
                </row>
                <row r="2">
                    <c r="A2" t="s"><v>2</v></c>
                    <c r="B2"><v>10000</v></c>
                </row>
            </sheetData>
        </worksheet>"""
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_zero_config_docx_ingestion() -> None:
    """Verify Microsoft Word (.docx) files are parsed and ingested with contextual prefix."""
    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    filename = "contract.docx"
    docx_content = _create_mock_docx()

    embedder = AsyncMock()
    embedder.embed_batch.side_effect = lambda texts: [[0.15] * 1536 for _ in texts]

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
            file_content=docx_content,
            file_hash="hash_docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            embedder=embedder,
        )

        assert chunk_count > 0
        texts_embedded = embedder.embed_batch.call_args[0][0]
        assert any("master services agreement" in t.lower() for t in texts_embedded)
        assert all(t.startswith("[Document: contract.docx]\n") for t in texts_embedded)


@pytest.mark.asyncio
async def test_zero_config_xlsx_ingestion() -> None:
    """Verify Microsoft Excel (.xlsx) files are parsed into markdown tables and ingested."""
    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    filename = "financial_model.xlsx"
    xlsx_content = _create_mock_xlsx()

    embedder = AsyncMock()
    embedder.embed_batch.side_effect = lambda texts: [[0.25] * 1536 for _ in texts]

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
            file_content=xlsx_content,
            file_hash="hash_xlsx",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            embedder=embedder,
        )

        assert chunk_count > 0
        texts_embedded = embedder.embed_batch.call_args[0][0]
        assert any("Month" in t and "Revenue" in t for t in texts_embedded)
        assert all(t.startswith("[Document: financial_model.xlsx]\n") for t in texts_embedded)
