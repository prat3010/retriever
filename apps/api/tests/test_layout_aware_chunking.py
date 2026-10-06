"""Unit tests for 2026 Layout-Aware / Structured Document Processing & Chunking."""

from processing_core.pdf_parser import (
    extract_form_fields,
    extract_structured_blocks,
)

from src.domain.ingestion.chunker_factory import ChunkerFactory, LayoutAwareChunker


def test_extract_form_fields_basic():
    text = """
    Invoice Number: INV-2026-9921
    Billing Date: 2026-10-06
    Total Amount: $4,850.00
    Customer ID = CUST-774
    Status: Approved
    """
    fields = extract_form_fields(text)
    assert fields["Invoice Number"] == "INV-2026-9921"
    assert fields["Billing Date"] == "2026-10-06"
    assert fields["Total Amount"] == "$4,850.00"
    assert fields["Customer ID"] == "CUST-774"
    assert fields["Status"] == "Approved"


def test_extract_structured_blocks_mixed_document():
    doc = """# Financial Quarterly Report

The following report covers performance in Q3.

| Quarter | Revenue | EBITDA | Margin |
| --- | --- | --- | --- |
| Q1 | $10M | $2.5M | 25% |
| Q2 | $12M | $3.2M | 26.6% |
| Q3 | $15M | $4.1M | 27.3% |

Invoice Details:
Vendor: Acme Global Inc.
Tax ID: US-99201928
Payment Terms: Net 30
    """
    blocks = extract_structured_blocks(doc)
    types = [b["type"] for b in blocks]
    assert "heading" in types
    assert "paragraph" in types
    assert "table" in types
    assert "form" in types

    table_block = next(b for b in blocks if b["type"] == "table")
    assert table_block["metadata"]["headers"] == ["Quarter", "Revenue", "EBITDA", "Margin"]
    assert table_block["metadata"]["rows_count"] == 3

    form_block = next(b for b in blocks if b["type"] == "form")
    assert form_block["metadata"]["fields"]["Vendor"] == "Acme Global Inc."
    assert form_block["metadata"]["fields"]["Tax ID"] == "US-99201928"


def test_layout_aware_chunker_preserves_table_atomicity():
    chunker = LayoutAwareChunker()
    doc = """# Executive Summary

Here is the operational breakdown for current services:

| Service | SLA | Tier | Monthly Cost |
| --- | --- | --- | --- |
| Search API | 99.95% | Enterprise | $1,200 |
| Ingestion Worker | 99.90% | Standard | $800 |
| Vector Cache | 99.99% | Critical | $2,000 |

All services meet our enterprise latency budget.
"""
    chunks = chunker.split_text_with_offsets(doc, chunk_size=500, chunk_overlap=50)

    table_chunks = [c for c in chunks if c["meta_data"].get("is_table")]
    assert len(table_chunks) == 1
    t_chunk = table_chunks[0]
    assert "| Service | SLA | Tier | Monthly Cost |" in t_chunk["content"]
    assert "| Vector Cache | 99.99% | Critical | $2,000 |" in t_chunk["content"]
    assert t_chunk["meta_data"]["headers"] == ["Service", "SLA", "Tier", "Monthly Cost"]
    assert t_chunk["meta_data"]["rows_count"] == 3
    assert t_chunk["meta_data"]["section_path"] == "Executive Summary"


def test_layout_aware_chunker_oversized_table_row_split_retains_headers():
    chunker = LayoutAwareChunker()
    header = "| Transaction ID | Customer | Timestamp | Status | Value |\n| --- | --- | --- | --- | --- |"
    rows = [
        f"| TXN-{i:04d} | Corp Client Alpha {i} | 2026-10-06T12:00:{i%60:02d}Z | Settled | ${100 + i * 25}.00 |"
        for i in range(25)
    ]
    long_table = header + "\n" + "\n".join(rows)

    # Use very small chunk_size to force row partitioning
    chunks = chunker.split_text_with_offsets(long_table, chunk_size=80, chunk_overlap=10)

    assert len(chunks) > 1
    for idx, chunk in enumerate(chunks):
        assert chunk["meta_data"]["is_table"] is True
        # Every single chunk must carry the header row!
        assert "| Transaction ID | Customer | Timestamp | Status | Value |" in chunk["content"]
        assert "| --- | --- | --- | --- | --- |" in chunk["content"]
        if idx > 0:
            assert chunk["meta_data"]["table_continuation"] is True


def test_layout_aware_chunker_form_preservation():
    chunker = LayoutAwareChunker()
    form_text = """# Employment Form

Employee Name: Jordan Vance
Role: Principal Cognitive Systems Architect
Clearance Level: Top Secret / Tier 1
Department: Cognitive Infrastructure
Hire Date: 2026-03-15
"""
    chunks = chunker.split_text_with_offsets(form_text, chunk_size=300, chunk_overlap=50)
    form_chunks = [c for c in chunks if c["meta_data"].get("is_form")]
    assert len(form_chunks) == 1
    f_chunk = form_chunks[0]
    assert "Jordan Vance" in f_chunk["content"]
    assert f_chunk["meta_data"]["fields"]["Employee Name"] == "Jordan Vance"
    assert f_chunk["meta_data"]["fields"]["Clearance Level"] == "Top Secret / Tier 1"
    assert f_chunk["meta_data"]["section_path"] == "Employment Form"


def test_layout_aware_chunker_heading_breadcrumbs():
    chunker = LayoutAwareChunker()
    doc = """# Security Architecture

## Multi-Tenancy Engine

### Row-Level Security

PostgreSQL enforces RLS at the connection session level via tenant_session.
All vector tables shard records with tenant_id foreign keys.
"""
    chunks = chunker.split_text_with_offsets(doc, chunk_size=300, chunk_overlap=50)
    assert len(chunks) >= 1
    assert any("Security Architecture > Multi-Tenancy Engine > Row-Level Security" in c["meta_data"].get("section_path", "") for c in chunks)


def test_chunker_factory_layout_aware_instantiation():
    chunker = ChunkerFactory.get_chunker("layout_aware")
    assert isinstance(chunker, LayoutAwareChunker)

    structured_chunker = ChunkerFactory.get_chunker("structured")
    assert isinstance(structured_chunker, LayoutAwareChunker)


def test_layout_aware_chunker_consecutive_headings_preserved():
    chunker = LayoutAwareChunker()
    doc = """# Executive Report
## Section 1: Overview
This is the overview paragraph explaining system capabilities."""
    chunks = chunker.split_text_with_offsets(doc, chunk_size=300, chunk_overlap=50)
    assert len(chunks) == 1
    content = chunks[0]["content"]
    assert "# Executive Report" in content
    assert "## Section 1: Overview" in content
    assert "This is the overview paragraph" in content
    assert chunks[0]["start_char_idx"] == 0


def test_layout_aware_chunker_table_continuation_accurate_offsets():
    chunker = LayoutAwareChunker()
    header = "| Col A | Col B |\n| --- | --- |"
    rows = [f"| Data {i:02d} | Value {i:02d} |" for i in range(20)]
    doc = header + "\n" + "\n".join(rows)

    chunks = chunker.split_text_with_offsets(doc, chunk_size=30, chunk_overlap=0)
    assert len(chunks) > 1

    for _idx, c in enumerate(chunks):
        s = c["start_char_idx"]
        e = c["end_char_idx"]
        assert s >= 0
        assert e > s
        raw_slice = doc[s:e]
        # Must start cleanly with a markdown row marker '|' rather than a chopped mid-word character
        assert raw_slice.startswith("|")

