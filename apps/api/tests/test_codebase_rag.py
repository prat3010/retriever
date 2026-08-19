"""Unit tests for AST Code Chunker and RagIgnore Security Filtering."""

from pathlib import Path

from src.adapters.cognitive.ast_code_chunker import AstCodeChunker
from src.domain.ingestion.ragignore import RagIgnoreFilter


def test_ragignore_security_filter(tmp_path: Path):
    """Verify RagIgnoreFilter blocks sensitive files and secrets."""
    (tmp_path / ".ragignore").write_text("*.secret\nprivate_config.json\n", encoding="utf-8")

    filter_obj = RagIgnoreFilter(root_dir=tmp_path)

    # Compulsory blacklists must be ignored
    assert filter_obj.is_ignored(tmp_path / ".env.local") is True
    assert filter_obj.is_ignored(tmp_path / "server.key") is True
    assert filter_obj.is_ignored(tmp_path / "id_rsa") is True
    assert filter_obj.is_ignored(tmp_path / "node_modules" / "express" / "index.js") is True

    # Custom .ragignore rules must be ignored
    assert filter_obj.is_ignored(tmp_path / "app.secret") is True
    assert filter_obj.is_ignored(tmp_path / "private_config.json") is True

    # Safe files must NOT be ignored
    assert filter_obj.is_ignored(tmp_path / "docs" / "readme.md") is False
    assert filter_obj.is_ignored(tmp_path / "src" / "main.py") is False


def test_ast_python_chunker():
    """Verify AstCodeChunker extracts class and function nodes without breaking syntax."""
    sample_code = '''
class PaymentProcessor:
    """Processes online customer payments."""

    def __init__(self, key: str):
        self.key = key

    async def charge(self, amount: float) -> bool:
        """Charge the given amount."""
        return True
'''
    chunker = AstCodeChunker()
    chunks = chunker.chunk_python_ast(sample_code, filename="processor.py")

    assert len(chunks) >= 1
    class_chunk = chunks[0]
    assert class_chunk["metadata"]["symbol_name"] == "PaymentProcessor"
    assert "class PaymentProcessor" in class_chunk["content"]


def test_markdown_section_chunker():
    """Verify Markdown chunking splits headers correctly."""
    sample_md = '''# Architecture Overview
This is the architecture description.

## Section 1: Ingestion
Ingestion processes PDF files.

## Section 2: Retrieval
Retrieval uses HNSW index.
'''
    chunker = AstCodeChunker()
    chunks = chunker.chunk_markdown(sample_md, filename="arch.md")

    assert len(chunks) == 3
    assert chunks[0]["metadata"]["section_title"] == "Architecture Overview"
    assert chunks[1]["metadata"]["section_title"] == "Section 1: Ingestion"
    assert chunks[2]["metadata"]["section_title"] == "Section 2: Retrieval"
