# Docling Layout-Aware OCR & Multi-Column Document Parsing

**Milestone:** M72 (v0.58.0)  
**System Layer:** Multimodal Document Ingestion & Layout Understanding (Platform Battery #4)  
**Architecture:** Docling v2 Deep Layout Parsing + Multi-Column Reading Order Heuristics + Tabular HTML/Markdown Reconstruction + RapidOCR Fallback  

---

## 1. Executive Summary

Milestone 72 delivers **Platform Battery #4: `docling_layout_ocr`**, establishing structural and multimodal document ingestion for Retriever.

Naively extracting text from complex enterprise PDFs (such as financial statements, legal contracts, patents, and multi-column academic papers) with basic text extractors (e.g. `pypdf`, `pdfminer`) leads to severe structural degradation:
- Multi-column text is concatenated horizontally, interleaving unrelated sentences.
- Multi-cell tables are flattened into unstructured word soup, destroying row-column relationships.
- Embedded charts, footnotes, and headers contaminate primary narrative flow.

Platform Battery #4 deploys the Docling v2 deep layout engine. It segments raw PDF rendering pages into hierarchical visual objects (headings, paragraphs, multi-column blocks, tables, captions), computes true reading order, and synthesizes structured markdown representations with explicit markdown tables.

---

## 2. Technical Architecture & Parsing Pipeline

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DOCLING MULTIMODAL INGESTION PIPELINE                           │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   [ Scanned or Digital PDF Document ]                                                  │
│            │                                                                           │
│            ▼                                                                           │
│   ┌──────────────────────────────────────────────────────────────────────────┐         │
│   │ 1. Visual Object Segmentation & Bounding Box Detection                   │         │
│   │    - Detects text boxes, image areas, and tabular boundaries             │         │
│   └────────────────────────────────────┬─────────────────────────────────────┘         │
│                                        │                                               │
│                                        ▼                                               │
│   ┌──────────────────────────────────────────────────────────────────────────┐         │
│   │ 2. RapidOCR Fallback Layer (For Scanned / Non-Selectable Pages)          │         │
│   │    - Runs on-device optical character recognition                        │         │
│   └────────────────────────────────────┬─────────────────────────────────────┘         │
│                                        │                                               │
│                                        ▼                                               │
│   ┌──────────────────────────────────────────────────────────────────────────┐         │
│   │ 3. Table Structure Recognition & HTML/Markdown Synthesis                 │         │
│   │    - Reconstructs merged cells, column headers, and numeric values       │         │
│   └────────────────────────────────────┬─────────────────────────────────────┘         │
│                                        │                                               │
│                                        ▼                                               │
│   ┌──────────────────────────────────────────────────────────────────────────┐         │
│   │ 4. Reading-Order Graph Topological Sort                                  │         │
│   │    - Connects multi-column flows, eliminates header/footer noise         │         │
│   └────────────────────────────────────┬─────────────────────────────────────┘         │
│                                        │                                               │
│                                        ▼                                               │
│   ┌──────────────────────────────────────────────────────────────────────────┐         │
│   │ Output: Clean Hierarchical Markdown (Preserving Tables & Section Headers)│         │
│   └──────────────────────────────────────────────────────────────────────────┘         │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Key Capabilities

1. **Table Structure Preservation:** Complex financial ledgers and matrices are serialized directly into GitHub-flavored Markdown tables or structured JSON arrays, enabling precise LLM numerical reasoning.
2. **Multi-Column De-Interleaving:** Resolves two-column and three-column research publications without cross-column textual bleeding.
3. **Artifact Stripping:** Automatically removes recurring page headers, page numbers, and running footers that dilute vector similarity.
4. **Latency Profile:** $\sim 250\text{ms}$ per page on commodity CPU infrastructure.

---

## 4. Implementation Details

- **Adapter:** `apps/api/src/adapters/cognitive/pdf_parser.py` (`DoclingPdfParser`)
- **Supported Formats:** PDF, DOCX, PPTX, Scanned PNG/TIFF images.
- **Active Parameters:**
  - `enable_table_extraction`: `true`
  - `enable_ocr`: `true`
  - `output_format`: `markdown`
- **Health Check Endpoint:** `GET /v1/documents/parse-status`

---

## 5. Non-Negotiable Invariants

1. **Deterministic Markdown Serialization:** The same document parsed multiple times must produce identical markdown tokens and whitespace hashes.
2. **Table Boundary Integrity:** Cells with multiple lines must be escaped with `<br>` tags rather than raw newlines to prevent breaking markdown table row layouts.
3. **Memory Ceiling:** PDF page rendering buffers must be cleared between pages to prevent worker OOM exceptions during processing of 500+ page enterprise manuals.
