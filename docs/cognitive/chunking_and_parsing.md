---
id: DeepDive_Chunking_Parsing_Docling
title: "Cognitive Deep-Dive: Hierarchical Chunking, Vision OCR & Docling Ingestion"
tier: 6_retriever_cognitive
platform: retriever
tags:
  - cognitive/chunking
  - cognitive/docling-ocr
  - cognitive/parent-child
  - cognitive/code-ast
  - platform/retriever
blast_radius: HIGH
invariants:
  - "Parent chunks MUST preserve complete section context (1024–2048 tokens)."
  - "Child chunks MUST be bounded to 256–512 tokens with parent_chunk_id foreign key."
---

# Cognitive Deep-Dive: Hierarchical Chunking, Vision OCR & Docling Ingestion

#cognitive #chunking #docling #ocr #parentchild #ast #retriever

> **Technical architecture, layout parsing strategies, and hierarchical chunking algorithms in Retriever.**

---

## 1. Chunking Strategy Taxonomy

Retriever provides 6 specialized chunking engines tailored to different document modalities:

```mermaid
graph TD
    File[Uploaded File Stream] --> Detect{File Modality Detector}
    
    Detect -->|PDF / Scanned Paper| Docling[Docling Layout OCR & Table Extractor]
    Detect -->|Prose / Articles| Recursive[Recursive Character Token Chunker]
    Detect -->|Complex Reports| ParentChild[Hierarchical Parent-Child Chunker]
    Detect -->|Dense Books| Semantic[Semantic Cosine Similarity Boundary Chunker]
    Detect -->|Codebase / Scripts| AST[Tree-Sitter Code AST Chunker]
    Detect -->|CSV / Tabular| Tabular[Row-wise Semantic JSON Serializer]
    
    Docling & Recursive & ParentChild & Semantic & AST & Tabular --> Embed[pgvector HNSW Store]
```

---

## 2. Chunking Engines Deep-Dive

### 2.1 Hierarchical Parent-Child Chunking
- **Parent Chunk (1536 tokens):** Contains complete section or article context.
- **Child Chunks (256 tokens):** Granular sub-passages embedded into pgvector for high-precision search.
- **Retrieval Mechanism:** When a child chunk matches a query, Retriever injects the **Parent Chunk** into the LLM prompt, providing broad contextual grounding without token bloat.

```mermaid
classDiagram
    class ParentChunk {
        +UUID parent_id
        +string section_title
        +string full_content (1536 tokens)
    }
    class ChildChunk {
        +UUID child_id
        +UUID parent_id
        +vector embedding (768d)
        +string granular_text (256 tokens)
    }
    ParentChunk "1" *-- "many" ChildChunk : contains
```

---

### 2.2 Semantic Similarity Boundary Chunking
Computes sentence-level embeddings using a lightweight local model. When the cosine distance between sentence \(s_i\) and sentence \(s_{i+1}\) exceeds a threshold \(\theta_{\text{split}} = 0.35\), a new chunk boundary is placed dynamically at the topical shift.

---

### 2.3 Docling Vision OCR & Layout Extraction
Uses IBM Docling to reconstruct multi-column academic papers, extract complex financial tables into Markdown/JSON format, and retain visual bounding boxes for UI rendering.

---

## 🔗 Related Architecture & Cross-References
- [Document API Specification](../api/document.md)
- [Hybrid Search & Fusion](hybrid_search_and_fusion.md)
- [Storage & Zero-Trust Encryption](../infrastructure/storage_and_encryption.md)
