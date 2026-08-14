"""Tests for Milestone 42: Layout-Aware Vision OCR & Table Parsing."""

import pytest
from processing_core.pdf_parser import (
    convert_table_to_markdown,
    extract_layout_from_pdf,
)


def test_convert_table_to_markdown_basic() -> None:
    headers = ["Quarter", "Revenue", "Growth"]
    rows = [
        ["Q1", "$100K", "+10%"],
        ["Q2", "$150K", "+50%"],
    ]
    md = convert_table_to_markdown(headers, rows)
    assert "| Quarter | Revenue | Growth |" in md
    assert "| --- | --- | --- |" in md
    assert "| Q1 | $100K | +10% |" in md
    assert "| Q2 | $150K | +50% |" in md


def test_convert_table_to_markdown_empty() -> None:
    assert convert_table_to_markdown([], []) == ""


def test_convert_table_to_markdown_padding() -> None:
    headers = ["Col A", "Col B"]
    rows = [["Val 1"], ["Val 2", "Val 3", "Extra"]]
    md = convert_table_to_markdown(headers, rows)
    lines = md.split("\n")
    assert len(lines) == 4
    # Padded row
    assert "| Val 1 |  |" in lines[2]
    # Truncated extra cell row
    assert "| Val 2 | Val 3 |" in lines[3]


def test_extract_layout_from_nonexistent_pdf_raises() -> None:
    with pytest.raises(Exception):
        extract_layout_from_pdf("/tmp/nonexistent_file_12345.pdf")
