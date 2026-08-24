# Retriever RAG Platform — 2026 Architecture & Engine Specification

> 📌 **Master Cross-Platform Roadmap (SSoT):** For the active sequential timeline (M1 to M68) connecting `retriever` and the `prateeq.in` control plane, see: [`Prateek_website/docs/UNIFIED_MASTER_ROADMAP.md`](../../Prateek_website/docs/UNIFIED_MASTER_ROADMAP.md).

**System:** Retriever Enterprise RAG Platform  
**Repository:** `retriever`  
**Document Version:** `v0.52.0`  
**Target Audience:** Platform Architects, System Engineers & Product Leadership  

---

## 1. Master Architectural Vision & System Separation

Retriever is designed as an enterprise-grade, highly modular Retrieval-Augmented Generation (RAG) platform based on a strict **Ports and Adapters (Hexagonal)** architecture.

```
                                SYSTEM BOUNDARY MATRIX

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   CLIENT FRONTEND LAYER                                 │
│                                (Prateek_website / UI Apps)                              │
│                                                                                         │
│   • Presentation & UI Component Rendering (`/rag`, `/rag/app`)                         │
│   • Client State & Lenis Smooth Scroll Management                                       │
│   • `RetrieverClient` (`src/lib/rag-client.ts`) HTTP/SSE API Adapter                    │
└────────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             │ REST API / SSE Event Streams (/v1/...)
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                     RETRIEVER ENGINE                                    │
│                                    (retriever Repo)                                     │
│                                                                                         │
│   • 100% Core RAG Domain Logic & Data Ingestion Pipelines                               │
│   • Hybrid Search (HNSW Dense + BM25 Sparse), Reciprocal Rank Fusion & Reranking        │
│   • HyDE Query Expansion, Self-Querying & Intent Classification                         │
│   • GraphRAG Entity Extraction, Neo4j/Pg Triples & Community Summaries                  │
│   • Recursive Language Model (RLM) Python REPL Execution Sandbox                        │
│   • Context Compression (LongLLMLingua) & Zero-Trust Field Encryption                   │
│   • Multi-Tenant Row-Level Security (RLS) & Compliance Purge (GDPR/SOC2)                 │
│   • Real-Time Online Hallucination Tracing (Faithfulness & Relevance Scoring)           │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 2026 Best-in-Class RAG Baseline Architecture

By 2026, standard enterprise RAG has evolved into a modular, multi-stage cognitive pipeline:

```
[User Query] ──> [Query Intent Classifier] ──> [Self-Query Parser]
                                                     │
      ┌──────────────────────────────────────────────┴──────────────────────────────────────────────┐
      │ Parallel Speculative Candidate Retrieval                                                    │
      ├───────────────────────────────────────┬──────────────────────────────────────┬──────────────┤
      │ Dense Vector (HNSW MRL)               │ Sparse BM25 / SPLADE                 │ GraphRAG Hop │
      └───────────────────┬───────────────────┴───────────────────┬──────────────────┴──────┬───────┘
                          │                                       │                         │
                          └───────────────────────────────┬───────┴─────────────────────────┘
                                                          ▼
                                              [Reciprocal Rank Fusion]
                                                          │
                                                          ▼
                                             [Cross-Encoder Reranker]
                                                          │
                                                          ▼
                                         [LongLLMLingua Context Compression]
                                                          │
                                                          ▼
                                            [LLM Generation + Streaming]
                                                          │
                                                          ▼
                                       [Real-Time Faithfulness Guardrail]
```

### RAG vs. Recursive Language Models (RLMs)

| Feature | Modern RAG (2026) | Recursive Language Models (RLM) |
| :--- | :--- | :--- |
| **Primary Goal** | Fast, high-precision fact lookup across large vaults | Deep, programmatic, multi-stage reasoning |
| **Context Handling** | Retrieved chunks inserted into static prompt | Context as an interactive Python REPL variable |
| **Constraint** | Dependent on retrieval recall | Dependent on code execution / reasoning capacity |
| **Best Use Case** | Factoid Q&A, regulatory lookup, knowledge search | Complex multi-document synthesis & data verification |

---

## 3. Product Roadmap (Milestones M54–M60)

```
ROADMAP EXECUTION HORIZONS:
┌──────────────────────────────────────┐
│ PHASE 1: MUST-HAVE BASELINE (M54-M55)│ ── SDK Parity, Speculative Parallel Search, Parent-Child Hydration
└──────────────────┬───────────────────┘
                   │
┌──────────────────▼───────────────────┐
│ PHASE 2: OPTIMIZATIONS (M56-M58)    │ ── Contextual Ingestion, ColBERT Reranking, CRAG Agentic Loops
└──────────────────┬───────────────────┘
                   │
┌──────────────────▼───────────────────┐
│ PHASE 3: STRATEGIC BETS (M59-M60)    │ ── RLM REPL Studio, GraphRAG Community Summaries, Self-Tuning RAG
└──────────────────────────────────────┘
```

### Phase 1: Must-Have Baseline Enhancements

#### Milestone M54: SDK Parity & Speculative Parallel Retrieval
*   **Objective:** Achieve 100% API capability parity in the client SDK and optimize retrieval latency.
*   **Key Deliverables:**
    1.  Update client SDK (`RetrieverClient`) with support for Context Compression, Consensus score inspection, Guardrail alert status, and RLM mode.
    2.  Refactor `HybridSearchService.search()` to execute Self-Query parsing, HyDE expansion, and raw vector embedding concurrently via `asyncio.gather()`, cutting $300-600\text{ms}$ off search latency.

#### Milestone M55: Enforced Parent-Child Hydration & Citation Span Validation
*   **Objective:** Maximize context quality while ensuring strict, verifiable grounding.
*   **Key Deliverables:**
    1.  Enforce automatic parent (800-token) and child (150-token) chunk creation during document ingestion, dynamically hydrating parent context in `PromptBuilder`.
    2.  Expand `CitationValidator` to perform exact string-span matching between generated quotes and retrieved context, flagging ungrounded claims with visual warnings.

---

### Phase 2: High-Leverage Optimizations

#### Milestone M56: Pre-Chunk Contextual Retrieval Ingestion Engine (Anthropic Method)
*   **Objective:** Eliminate ambiguous standalone chunks by pre-pending document-level context during ingestion.
*   **Key Deliverables:**
    1.  Build an asynchronous worker step in `ingestion_service.py` using a fast LLM (`gemini-3.6-flash` / `claude-3-5-haiku`) to prepend 50-word document context headers to every chunk before vector embedding generation.
    2.  Reduces top-20 retrieval failure rates by up to $49\%$.

#### Milestone M57: Late-Interaction (ColBERT) Token-Level Reranker
*   **Objective:** Surface nuanced technical terms, serial numbers, and code identifiers where standard bi-encoders fail.
*   **Key Deliverables:**
    1.  Implement `ColBertRerankerAdapter` (`tei_reranker_adapter.py`) computing token-level MaxSim operations on top-50 candidate sets.
    2.  Support local TEI containers and cloud API fallbacks.

#### Milestone M58: Corrective RAG (CRAG) & Agentic Reflection Loop
*   **Objective:** Enable autonomous self-reflection and query correction.
*   **Key Deliverables:**
    1.  Wire `agentic.py` router into inference loop to assess candidate relevance scores.
    2.  If confidence drops below threshold, automatically trigger query reformulations or web search fallback before LLM generation.

---

### Phase 3: Strategic Long-Term Bets

#### Milestone M59: Interactive RLM Python REPL Sandbox Studio
*   **Objective:** Productize Recursive Language Models into an interactive developer workspace.
*   **Key Deliverables:**
    1.  Productize `/v1/rlm` into a dedicated SaaS Studio tab (`/rag/app/rlm`) where users can observe the model writing and executing Python code to recursively inspect, filter, and summarize document vaults.

#### Milestone M60: GraphRAG Leiden Community Detection & Closed-Loop Self-Tuning
*   **Objective:** Unlock macro-level dataset reasoning and automated quality self-tuning.
*   **Key Deliverables:**
    1.  Upgrade `graph_extraction_service.py` to construct global entity graphs, run Leiden community detection, and pre-generate macro hierarchical summaries.
    2.  Connect M50 online evaluation telemetry (`OnlineHallucinationEvaluator`) directly to `config_service` to automatically calibrate `reranking_threshold`, `top_k`, and `rrf_k` values based on continuous Ragas scoring.

---

## 4. Multi-Layer Stack Delivery Matrix

| Stack Layer | Milestone | Feature | Primary Impact | Effort | Risk | Target Phase |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Ingestion & Chunking** | **M56** | Contextual Pre-Chunking | **Very High** (49% error reduction) | Medium | Low | Phase 2 |
| **Retrieval & Hybrid** | **M54** | Speculative Parallel Fan-Out | **High** (300–600ms latency reduction) | Medium | Low | Phase 1 |
| **Context Assembly** | **M55** | Parent-Child Hydration | **High** (Rich context retention) | Low | Low | Phase 1 |
| **Grounding & Citations** | **M55** | Exact Span Citation Matcher | **High** (Zero hallucinated citations) | Medium | Low | Phase 1 |
| **Reranking & Precision** | **M57** | ColBERT Late-Interaction | **High** (Unmatched technical recall) | Medium | Medium | Phase 2 |
| **Reasoning & Agentic** | **M58** | Corrective RAG (CRAG) | **High** (Self-correcting search) | High | Medium | Phase 2 |
| **Reasoning & Agentic** | **M59** | RLM Python REPL Studio | **Very High** (Programmatic context) | High | Medium | Phase 3 |
| **Knowledge Graph** | **M60** | Leiden Community Summaries | **High** (Global vault Q&A) | High | Medium | Phase 3 |
| **Evaluation & Ops** | **M60** | Closed-Loop Self-Tuning | **Very High** (Auto-calibrating engine) | High | High | Phase 3 |

---

## **Related Architecture & Cross-References**

- [Unified Master Roadmap (SSoT)](../../Prateek_website/docs/UNIFIED_MASTER_ROADMAP.md)
- [RAG App Studio PRD](../../Prateek_website/docs/24_RAG_App_Studio_PRD.md)
- [Scoping Dogfooding Tenant (`prateeq_scoping`)](../../Prateek_website/docs/25_SOTA_Scoping_Engine_PRD.md)
- [Logical Architecture Blueprint](architecture.md)
- [Physical System Design](implementation/system-design.md)
