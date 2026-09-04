# ADR-011: Multi-Modal Ingestion Pipeline (Docling AST & Baidu RapidOCR)

## Status
Accepted

## Context
Enterprise documents (contracts, financial reports, technical papers) frequently contain complex multi-column layouts, embedded tabular grids, headers/footers, and scanned image pages. Naive raw text extractors (such as `pypdf` or regex splitters) destroy spatial structure, merging table cells and headers into incoherent text strings that cripple retrieval accuracy.

## Problem
We need an ingestion engine that:
1. Reconstructs full document hierarchy (sections, subsections, paragraphs, code blocks).
2. Converts complex financial and technical tables into structured markdown tables without column merging.
3. Provides fast, local OCR for scanned PDFs without relying on costly external Vision LLM APIs.

## Decision
Adopt a **Two-Tier Multi-Modal Parsing Architecture**:
1. **Layout & AST Extraction:** Utilize **IBM Docling** to parse documents into semantic ASTs, preserving table coordinates and bounding boxes.
2. **Local Scanned OCR:** Integrate **Baidu RapidOCR (PP-OCRv4 ONNX)** running locally for high-speed, zero-cloud-fee text extraction on scanned image pages.
3. For environments without GPU acceleration, provide a resilient, pure-Python fallback pipeline.

## Consequences
* **Accurate Table Retrieval:** Tabular context is embedded as structured Markdown tables, allowing LLMs to perform accurate numerical and column reasoning.
* **Cost Efficiency:** Running PP-OCRv4 via ONNX runtime eliminates third-party OCR API charges.
* **Package Overhead:** Docling and ONNX dependencies increase Python environment build footprint (~800MB).

## Future Review Criteria
* Audit OCR latency on 100+ page scanned legal PDFs.
