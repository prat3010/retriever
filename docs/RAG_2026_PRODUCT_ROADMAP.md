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

## 3. Product Roadmap & Strategic Horizons (Cross-Platform Alignment)

```
ROADMAP EXECUTION HORIZONS:
┌──────────────────────────────────────────────────┐
│ PHASE G: COMMERCIAL SCOPING & DASHBOARD (M63-M68)│ ── Scoping V2, Embed Widget, 7-Day Trial Auto-Onboard
└────────────────────────┬─────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────┐
│ PHASE H1: COGNITIVE INGESTION & RERANK (M69-M70) │ ── Anthropic Contextual Ingestion, ColBERT Late-Interaction
└────────────────────────┬─────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────┐
│ PHASE H2: AGENTIC CRAG & KNOWLEDGE GRAPHS(M71-M73)│ ── CRAG Reflection, RLM Studio Tab, Leiden Community RAG
└──────────────────────────────────────────────────┘
```

### Phase G: Commercial Scoping V2 & Dashboard Integration (Active Next)
* **Milestone M63–M68:** Documented in detail in [`Prateek_website/docs/UNIFIED_MASTER_ROADMAP.md`](../../Prateek_website/docs/UNIFIED_MASTER_ROADMAP.md).
  - Authentic dogfooding tenant (`prateeq_scoping`) configured via Retriever Admin.
  - Scoping chatbox powered by the public 1-line `<script src="https://prateeq.in/widget.js" ...>` embed widget.
  - Auto-onboarding 7-day trial tenant creation upon Google OAuth sign-in with permanent non-deletable scope document indexing (`is_system: true`).

---

### Phase H: SOTA Cognitive RAG Algorithm R&D (Retriever Engine Upgrades)

#### Milestone M69: Pre-Chunk Contextual Retrieval Ingestion Engine (Anthropic Method)
*   **Objective:** Eliminate ambiguous standalone chunks by pre-pending document-level context during ingestion.
*   **Key Deliverables:**
    1.  Build an asynchronous worker step in `ingestion_service.py` using a fast LLM (`gemini-3.6-flash` / `claude-3-5-haiku`) to prepend 50-word document context headers to every chunk before vector embedding generation.
    2.  Reduces top-20 retrieval failure rates by up to $49\%$.

#### Milestone M70: Late-Interaction (ColBERT) Token-Level Reranker
*   **Objective:** Surface nuanced technical terms, serial numbers, and code identifiers where standard bi-encoders fail.
*   **Key Deliverables:**
    1.  Implement `ColBertRerankerAdapter` (`tei_reranker_adapter.py`) computing token-level MaxSim operations on top-50 candidate sets.
    2.  Support local TEI containers and cloud API fallbacks.

#### Milestone M71: Corrective RAG (CRAG) & Agentic Reflection Loop
*   **Objective:** Enable autonomous self-reflection and query correction.
*   **Key Deliverables:**
    1.  Wire `agentic.py` router into inference loop to assess candidate relevance scores.
    2.  If confidence drops below threshold, automatically trigger query reformulations or web search fallback before LLM generation.

#### Milestone M72: Interactive RLM Python REPL Sandbox Studio
*   **Objective:** Productize Recursive Language Models into an interactive developer workspace.
*   **Key Deliverables:**
    1.  Productize `/v1/rlm` into a dedicated SaaS Studio tab (`/rag/app/rlm`) where users can observe the model writing and executing Python code to recursively inspect, filter, and summarize document vaults.

#### Milestone M73: GraphRAG Leiden Community Detection & Closed-Loop Self-Tuning
*   **Objective:** Unlock macro-level dataset reasoning and automated quality self-tuning.
*   **Key Deliverables:**
    1.  Upgrade `graph_extraction_service.py` to construct global entity graphs, run Leiden community detection, and pre-generate macro hierarchical summaries.
    2.  Connect M50 online evaluation telemetry (`OnlineHallucinationEvaluator`) directly to `config_service` to automatically calibrate `reranking_threshold`, `top_k`, and `rrf_k` values based on continuous Ragas scoring.

---

### Phase I: Enterprise Cognitive Evaluation & Deep Observability Hardening (M74 – M78)

#### Milestone M74: Semantic NLI & SLM-as-a-Judge Online Hallucination Engine
*   **Objective:** Replace naive keyword overlap checks with semantic Natural Language Inference (NLI) and async Small Language Model judges to eliminate false-positive faithfulness scores.
*   **Key Deliverables:**
    1.  DeBERTa NLI Cross-Encoder (`nli_evaluator.py`) evaluating claim-premise entailment probabilities.
    2.  Async Celery task `tasks.evaluate_inference_nli` running a local Ollama judge (`qwen2.5:3b` / `llama3.2:3b`) with structured reasoning and span localization.

#### Milestone M75: Full-Stack OpenTelemetry Auto-Instrumentation & Distributed Trace Graph
*   **Objective:** Provide end-to-end distributed tracing across database queries, vector similarity operations, outbound LLM APIs, and async Celery workers.
*   **Key Deliverables:**
    1.  Auto-instrument SQLAlchemy, HTTPX, and Celery worker queues.
    2.  Propagate W3C standard `traceparent` headers across Next.js proxy $\rightarrow$ FastAPI Gateway $\rightarrow$ Celery workers.

#### Milestone M76: Real-Time Telemetry Live Aggregations & SLA Webhook Alerting Engine
*   **Objective:** Transition telemetry endpoints from static fallbacks to live multi-tenant database aggregations with automated incident webhooks.
*   **Key Deliverables:**
    1.  Live database aggregations for tenant tokens, cache savings, and quality metrics.
    2.  Multi-channel webhook alerting dispatcher (Slack, Discord, Resend email) on Hallucination Index $> 30\%$ or token quota $\ge 90\%$.

#### Milestone M77: Synthetic Golden Dataset Generation & Automated CI/CD Regression Gate
*   **Objective:** Automate continuous RAG evaluation by synthesizing benchmark datasets and enforcing PR blocking gates in CI/CD.
*   **Key Deliverables:**
    1.  Synthetic Test Generator (`synthetic_dataset_generator.py`) extracting Q&A benchmark pairs from tenant documents.
    2.  GitHub Action workflow enforcing strict Ragas + DeepEval quality thresholds before canary releases.

#### Milestone M78: Visual Claim-by-Claim Grounding Diff & Synchronizer Observability Cockpit
*   **Objective:** Deliver granular visual insight into model faithfulness and integrate backend observability into the local Synchronizer desktop control center.
*   **Key Deliverables:**
    1.  Visual sentence-by-sentence grounding inspector in Retriever Admin and SaaS Studio.
    2.  Local Streamlit Synchronizer analytics tab overhaul with live Retriever telemetry and active alert feeds.

---

## 4. Multi-Layer Stack Delivery Matrix

| Stack Layer | Milestone | Feature | Primary Impact | Effort | Risk | Target Phase |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Commercial & Client** | **M63–M68** | Scoping V2 & Dashboard 7-Day Trial | **Critical** (Live revenue & client conversion) | High | Low | Phase G (Active Next) |
| **Ingestion & Chunking** | **M69** | Contextual Pre-Chunking | **Very High** (49% error reduction) | Medium | Low | Phase H |
| **Reranking & Precision** | **M70** | ColBERT Late-Interaction | **High** (Unmatched technical recall) | Medium | Medium | Phase H |
| **Reasoning & Agentic** | **M71** | Corrective RAG (CRAG) | **High** (Self-correcting search) | High | Medium | Phase H |
| **Reasoning & Agentic** | **M72** | RLM Python REPL Studio | **Very High** (Programmatic context) | High | Medium | Phase H |
| **Knowledge Graph** | **M73** | Leiden Community Summaries | **High** (Global vault Q&A) | High | Medium | Phase H |
| **Evaluation & Ops** | **M73** | Closed-Loop Self-Tuning | **Very High** (Auto-calibrating engine) | High | High | Phase H |
| **Evaluation & Quality**| **M74** | Semantic NLI & SLM Judge | **Critical** (Eliminates false faithfulness) | Medium | Low | Phase I |
| **Observability & Infra**| **M75** | Full-Stack OTel Auto-Instrumentation | **Very High** (End-to-end DB/LLM tracing) | Low | Low | Phase I |
| **Observability & Alerts**| **M76**| Real-Time Webhook Alerting | **High** (Instant SLA breach notification) | Low | Low | Phase I |
| **Evaluation & CI/CD** | **M77** | Synthetic Dataset & CI Gate | **Very High** (Zero-regression release gate) | Medium | Low | Phase I |
| **Observability & UI** | **M78** | Visual Grounding & Sync Cockpit | **High** (Granular UI trust & local ops) | Medium | Low | Phase I |

---

## **Related Architecture & Cross-References**

- [Unified Master Roadmap (SSoT)](../../Prateek_website/docs/UNIFIED_MASTER_ROADMAP.md)
- [RAG App Studio PRD](../../Prateek_website/docs/24_RAG_App_Studio_PRD.md)
- [Scoping Dogfooding Tenant (`prateeq_scoping`)](../../Prateek_website/docs/25_SOTA_Scoping_Engine_PRD.md)
- [Logical Architecture Blueprint](architecture.md)
- [Physical System Design](implementation/system-design.md)
