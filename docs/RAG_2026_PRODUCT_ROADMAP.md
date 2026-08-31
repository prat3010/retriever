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
└────────────────────────┬─────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────┐
│ PHASE I: ENTERPRISE COGNITIVE EVALUATION (M74-M78)│ ── Semantic NLI, Full-Stack OTel, Golden Dataset CI Gates
└────────────────────────┬─────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────┐
│ PHASE J: PREDICTIVE ML & NEURAL FRAMEWORK (M79-M85)│ ── ColBERT MaxSim, HDBSCAN Clustering, 3D UMAP, ML Effort Regressor
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
    1.  Implement `LeidenCommunityDetector` and `CommunitySummarizer` to construct global entity graphs, run modularity-optimized Leiden community detection, and pre-generate macro hierarchical summaries.
    2.  Connect online evaluation telemetry (`OnlineHallucinationEvaluator`) directly to `ConfigurationService` and `SelfTuningEngine` to automatically calibrate `reranking_threshold`, `top_k`, and `rrf_k` values based on continuous scoring.
*   **Status:** **Completed** (Phase H Completed)

---

### Phase I: Enterprise Cognitive Evaluation & Deep Observability Hardening (M74 – M78) — **ACTIVE NEXT**


#### Milestone M74: Semantic NLI & SLM-as-a-Judge Online Hallucination Engine
*   **Objective:** Replace naive keyword overlap checks with semantic Natural Language Inference (NLI) and async Small Language Model judges to eliminate false-positive faithfulness scores.
*   **Key Deliverables:**
    1.  Semantic NLI Cross-Encoder (`nli_evaluator.py`) evaluating directional claim-premise entailment and polarity contradictions.
    2.  Structured SLM Judge Engine (`slm_judge.py`) & Celery task `tasks.evaluate_inference_nli` running claim breakdown and evidence span localization.
*   **Status:** **Completed** (Phase I)

#### Milestone M75: Full-Stack OpenTelemetry Auto-Instrumentation & Distributed Trace Graph
*   **Objective:** Provide end-to-end distributed tracing across database queries, vector similarity operations, outbound LLM APIs, and async Celery workers.
*   **Key Deliverables:**
    1.  Auto-instrumentation registry (`auto_instrumentation.py`) for SQLAlchemy pgvector queries, HTTPX outbound LLM requests, and Celery task lifecycles.
    2.  Propagate W3C standard `traceparent` headers across Next.js proxy $\rightarrow$ FastAPI Gateway $\rightarrow$ Celery workers with `X-Trace-Id` response reflection.
*   **Status:** **Completed** (Phase I)

#### Milestone M76: Real-Time Telemetry Live Aggregations & SLA Webhook Alerting Engine
*   **Objective:** Transition telemetry endpoints from static fallbacks to live multi-tenant database aggregations with automated incident webhooks.
*   **Key Deliverables:**
    1.  Live database aggregations (`SqlTelemetryRepository` & `LiveTelemetryService`) for tenant tokens, cache savings, satisfaction rates, and SLA latencies.
    2.  Multi-channel webhook alerting dispatcher (`alert_service.py` for Slack, Discord, custom HTTP JSON webhooks) with debouncing on Hallucination Index $> 30\%$, token quota $\ge 90\%$, or latency spikes.
*   **Status:** **Completed** (Phase I)

#### Milestone M77: Synthetic Golden Dataset Generation & Automated CI/CD Regression Gate
*   **Objective:** Automate continuous RAG evaluation by synthesizing benchmark datasets and enforcing PR blocking gates in CI/CD.
*   **Key Deliverables:**
    1.  Synthetic Test Generator (`synthetic_generator.py`) extracting Q&A benchmark pairs from tenant documents.
    2.  GitHub Action workflow (`eval_regression.yml`) and CLI runner (`scripts/run_eval_regression.py`) enforcing strict Ragas + DeepEval quality thresholds before canary releases.
*   **Status:** **Completed** (Phase I)

#### Milestone M78: Visual Claim-by-Claim Grounding Diff & Retriever Admin Observability Cockpit (Completed)
*   **Objective:** Deliver granular visual insight into model faithfulness and integrate deep cognitive observability natively inside the Retriever Admin Dashboard (`https://admin.rag.prateeq.in` / `retriever/apps/web`).
*   **Key Deliverables:**
    1.  Visual Claim Grounding Diff (`grounding-diff.tsx` / `tenant-hallucinations.tsx` in `retriever/apps/web`): Highlights generated responses sentence-by-sentence (green = verified in source, red = ungrounded/hallucinated, yellow = partial/neutral), with interactive side-by-side popovers showing the exact source chunk citation.
    2.  Retriever Admin Observability Cockpit (`tenant-metrics.tsx` & `tenant-telemetry.tsx`): Real-time charts for Hallucination Trends, Token Burn Rate, P99 Latency SLAs, and Active Alert Incident feeds.
    3.  Portfolio RAG Studio Claim Inspector (`src/components/rag/ChatPanel.tsx`): Real-time on-demand claim diff analysis and sentence highlighting.
*   **Status:** **Completed** (Phase I)

---

### Phase J: Machine Learning & Predictive Intelligence Framework (M79 – M85) — **IN PROGRESS**

#### Milestone M79: Sparse-Dense Hybrid Engine & Contrastive LoRA Domain Adapters (Completed)
*   **Objective:** Combine Scikit-Learn sparse vectorization with PyTorch contrastive domain adapter fine-tuning.
*   **Key Deliverables:**
    1.  Custom sublinear TF-IDF / BM25 vectorizer in `processing-core` preserving technical symbols, camelCase tokens, and custom stopwords for sub-millisecond sparse lookup.
    2.  PyTorch `MultipleNegativesRankingLoss` adapter fine-tuning script to calibrate embedding spaces to legal SOW and software architecture domains.

#### Milestone M80: PyTorch Late-Interaction ColBERT Token-Level MaxSim Engine (Completed)
*   **Objective:** Surface nuanced technical terms, serial numbers, and code identifiers where standard bi-encoders fail using token-level late interaction.
*   **Key Deliverables:**
    1.  ColBERT multi-vector token embedding model outputting token matrices $Q \in \mathbb{R}^{|Q| \times D}$ and $D \in \mathbb{R}^{|D| \times D}$.
    2.  Hardware-accelerated MaxSim operator running on Apple Silicon MPS and Oracle VPS CUDA workers for <10ms stage-2 candidate reranking.

#### Milestone M81: Scikit-Learn Unsupervised Chunk Clustering & HDBSCAN Dynamic Topic Modeling (ACTIVE NEXT)
*   **Objective:** Automate semantic topic discovery and hierarchical community node generation across tenant document libraries.
*   **Key Deliverables:**
    1.  Density-based HDBSCAN and KMeans clustering on 768-dim embeddings in `apps/api/src/domain/clustering/`.
    2.  Automatic synthesis of parent topic summary nodes and hierarchical link generation for GraphRAG.

#### Milestone M82: Scikit-Learn 2D/3D Embedding Space Projection Pipeline for SaaS Studio
*   **Objective:** Power an interactive 3D vector space visualizer in the SaaS Studio (`/rag/app`) using server-side dimensionality reduction.
*   **Key Deliverables:**
    1.  PCA + UMAP dimensionality reduction endpoint `POST /v1/tenants/{id}/embeddings/project` reducing 768D vectors to 3D coordinates $(x, y, z)$.
    2.  Interactive 3D WebGL / Three.js point cloud in SaaS Studio displaying document clusters and live query vector intersection.

#### Milestone M83: Scikit-Learn Real-Time Telemetry Anomaly Detection & Quota Abuse Guard
*   **Objective:** Deploy an unsupervised machine learning anomaly detection sentinel to safeguard tenant API keys and prevent scraping.
*   **Key Deliverables:**
    1.  Async Celery task running Scikit-Learn `IsolationForest` on streaming inference log features.
    2.  Automated quarantine downgrading suspicious traffic and firing high-priority security webhooks.

#### Milestone M84: Scikit-Learn ML Project Effort & Sprint Delivery Timeline Regression Model
*   **Objective:** Predict realistic engineering sprint hours and delivery windows with statistical confidence intervals in the Scoping Lab and Client Workspace.
*   **Key Deliverables:**
    1.  Multi-Output Gradient Boosting Regressor trained on CPQ scoping configurations predicting sprint hours ($P_{50} / P_{90}$) and complexity index.
    2.  Live interactive sprint confidence bar embedded in the Cart Drawer (`/scoping`) and Client Workspace (`/dashboard`).

#### Milestone M85: Scikit-Learn & PyTorch Visitor Persona & Lead Conversion Propensity Classifier
*   **Objective:** Segment anonymous visitors into dynamic personas and score cold outreach prospects by conversion probability.
*   **Key Deliverables:**
    1.  Zero-cookie `KMeans` clustering on GDPR-compliant telemetry to identify Enterprise Clients, SaaS Buyers, Recruiters, and Dev Peers.
    2.  Supervised lead scoring classifier in `/admin` predicting reply rate and contract value for automated outreach campaigns.

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
| **ML & Hybrid Search** | **M79** | Sparse TF-IDF & Contrastive LoRA | **Very High** (Domain vocabulary calibration) | Medium | Low | Phase J |
| **ML & Neural Rerank** | **M80** | PyTorch ColBERT MaxSim Engine | **High** (Sub-10ms token-level precision) | Medium | Medium | Phase J |
| **ML & Clustering** | **M81** | HDBSCAN Dynamic Topic Modeling | **High** (Unsupervised community synthesis) | Medium | Low | Phase J |
| **ML & SaaS Studio UI**| **M82** | 2D/3D Embedding Space Projection | **Very High** (Visual interactive point cloud) | Medium | Low | Phase J |
| **ML & Security** | **M83** | Isolation Forest Anomaly Sentinel | **High** (Automated API abuse quarantine) | Low | Low | Phase J |
| **ML & Scoping Commerce**| **M84**| SOW Effort & Timeline Regressor | **Critical** (Statistical confidence timelines) | Medium | Low | Phase J |
| **ML & Autonomous Growth**| **M85**| Visitor Persona & Lead Propensity | **Very High** (Dynamic UI & high-converting leads) | Medium | Low | Phase J |


---

### Phase J.5: Forensic Audit Remediation — Blueprint-to-Reality Parity (M85.1 – M85.4) — **PRIORITY NEXT**

> 📌 **Origin:** [FORENSIC_TECHNICAL_AUDIT_2026_08_26.md](../../Prateek_Ecosystem_Vault/FORENSIC_TECHNICAL_AUDIT_2026_08_26.md) — Section 3.3 "Vault Blueprint vs. Code Reality Gap" scored **4.0/10**. The following milestones close the gap between documented claims and actual code implementations.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  PHASE J.5: FORENSIC AUDIT REMEDIATION — BLUEPRINT-TO-REALITY PARITY (M85.1–M85.4)   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  [M85.1] True LlamaGuard 3 Model Integration (Replace Prompt Wrapper)                 │
│  [M85.2] True LongLLMLingua Perplexity-Based Context Compression                      │
│  [M85.3] Dashboard ↔ Retriever Live Integration (Zero Static Branching)                │
│  [M85.4] Autonomous Outreach Agent Completion (Phases 1, 3, 4, 5)                      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

#### 🔧 Milestone 85.1: True LlamaGuard 3 Safety Model Integration
*   **Gap Identified:** `adapters/guardrails/llm_safety_guard.py` runs a regex check followed by an OpenAI prompt referencing LlamaGuard 3 taxonomy labels (S1–S8). No actual LlamaGuard model weights are loaded or executed.
*   **Objective:** Replace the prompt-wrapper approach with a true LlamaGuard 3 model inference call, delivering genuine multi-label content safety classification.
*   **Key Deliverables:**
    1.  Deploy `meta-llama/Llama-Guard-3-8B` via Ollama on the Oracle VPS (or quantized `Q4_K_M` GGUF for memory efficiency on 24GB Ampere).
    2.  Implement `LlamaGuardAdapter` in `adapters/guardrails/` conforming to the `SafetyGuardProvider` abstract port — loading the model locally, passing user prompts through the official LlamaGuard input template, and parsing structured `safe`/`unsafe` + violated category codes.
    3.  Retain the existing regex pre-filter as a fast-path bypass (skip model inference for obviously benign queries), ensuring < 500ms P95 safety check latency.
    4.  Update `test_guardrails.py` with adversarial prompt injection test cases (jailbreak, indirect injection, role-play attacks) validating true model-level detection.
*   **Status:** **Planned (Phase J.5, Priority: P0)**

#### 🔧 Milestone 85.2: True LongLLMLingua Perplexity-Based Context Compression
*   **Gap Identified:** `adapters/cognitive/context_compressor_adapter.py` uses `FILLER_PATTERNS` regex removal and custom `IntelligentContextCompressor` sentence scoring — a heuristic approach, not the LongLLMLingua perplexity-based token importance algorithm.
*   **Objective:** Implement actual perplexity-based context compression to maximize information density within LLM context windows while preserving critical factual content.
*   **Key Deliverables:**
    1.  Integrate the `llmlingua` Python package (`LLMLingua-2` or `LongLLMLingua`) with a small local model (`microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank` or Ollama-served perplexity scorer) to compute token-level importance scores.
    2.  Implement `LongLLMLinguaAdapter` conforming to `ContextCompressorProvider` port — accepting raw retrieved chunks and returning compressed context with configurable compression ratio (target 2x–5x reduction).
    3.  Retain the existing `IntelligentContextCompressor` as a zero-dependency fallback adapter (activated when `llmlingua` is not available or for latency-sensitive paths).
    4.  Add A/B evaluation: compare faithfulness scores between heuristic compression vs. perplexity compression on the synthetic golden dataset (M77) to quantify improvement.
*   **Status:** **Planned (Phase J.5, Priority: P1)**

#### 🔧 Milestone 85.3: Dashboard ↔ Retriever Live Backend Integration
*   **Gap Identified:** `/dashboard` page (2,072 lines) makes zero HTTP calls to Retriever backend. The Client Project Copilot uses static `if/else` keyword branching instead of grounded RAG chat via the client's dedicated tenant.
*   **Objective:** Wire the Client Dashboard directly to the Retriever Cognitive Engine, replacing all static mock behaviors with live tenant-grounded interactions.
*   **Key Deliverables:**
    1.  Connect `ClientProjectCopilot.tsx` to `POST /v1/tenants/{tn_client_uuid}/chat/sessions/{id}/messages` via `rag-client.ts`, streaming grounded responses with source citations from the client's private document vault.
    2.  Wire milestone progress fetching to Retriever's tenant telemetry endpoints (`GET /v1/admin/tenants/{id}/telemetry`) for live token usage, cache hit rate, and active document count.
    3.  Display the client's Retriever Document Library directly in the Dashboard (read-only view of ingested SOW, specifications, and sprint deliverables).
    4.  Remove all hardcoded `if/else` keyword branching from the copilot and replace with genuine RAG-grounded conversational responses.
*   **Repo Scope:** `Prateek_website` (`src/app/dashboard/`, `src/lib/rag-client.ts`)
*   **Status:** **Planned (Phase J.5, Priority: P0)**

#### 🔧 Milestone 85.4: Autonomous Outreach Agent — Complete Unchecked Phases
*   **Gap Identified:** `docs/AI_OUTREACH_AGENT_ROADMAP.md` header claims "Completed M57-M58", but Phase 1 (Multi-Source Lead Discovery), Phase 3 (Automated LinkedIn/Email Dispatch), Phase 4 (Retriever-Grounded Pitch Evidence), and Phase 5 (Conversion Funnel Analytics) checkboxes remain unchecked in the document.
*   **Objective:** Either complete the unchecked phases or honestly re-scope the roadmap document to reflect actual implementation status.
*   **Key Deliverables:**
    1.  Audit `scripts/sync_tabs/outreach.py` and `/admin` routes against the roadmap Phase 1–5 checklist — mark genuinely completed items and identify remaining gaps.
    2.  For incomplete phases: implement or scope into future milestones with honest status labels (`Planned` / `Deferred`), never `Completed`.
    3.  Update `AI_OUTREACH_AGENT_ROADMAP.md` to accurately reflect the true implementation status of every checkpoint.
    4.  Wire Phase 4 (Retriever-Grounded Outreach) to the `prateeq_outreach` tenant (M58.5) for evidence-backed pitch personalization.
*   **Repo Scope:** Both (`Prateek_website` `scripts/sync_tabs/outreach.py`, `/admin` & `retriever` `prateeq_outreach` tenant)
*   **Status:** **Planned (Phase J.5, Priority: P1)**

---

#### Updated Multi-Layer Stack Delivery Matrix (Phase J.5 Additions)

| Stack Layer | Milestone | Feature | Primary Impact | Effort | Risk | Target Phase |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Safety & Guardrails** | **M85.1** | True LlamaGuard 3 Model | **Critical** (Real content safety, not prompt theater) | Medium | Medium | Phase J.5 |
| **Compression & Context** | **M85.2** | True LongLLMLingua Perplexity | **High** (2-5x context compression with quality) | Medium | Low | Phase J.5 |
| **Client Integration** | **M85.3** | Dashboard ↔ Retriever Live Wire | **Critical** (Core product claim credibility) | High | Low | Phase J.5 |
| **Growth & Outreach** | **M85.4** | Outreach Agent Phase Completion | **High** (Documentation honesty & automation) | Medium | Low | Phase J.5 |

---

### Phase J.6: Production Hardening & Engineering Credibility (M85.5 – M85.10) — **PRIORITY NEXT**

> 📌 **Origin:** Forensic Audit Seniority Radar scored **Security Hygiene at 3.0/10** and **Observability at 3.5/10**. The forensic P0 remediation ledger items remain unaddressed. Additionally, the ecosystem lacks load testing evidence, structured error tracking, and public developer advocacy — all critical for both production readiness and employability.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  PHASE J.6: PRODUCTION HARDENING & ENGINEERING CREDIBILITY (M85.5–M85.10)             │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  [M85.5] P0 Secret Rotation, Git History Purge & Crypto Key Hardening                  │
│  [M85.6] Structured Exception Handling & Production Error Tracking (Sentry)             │
│  [M85.7] Safe Deployment Pipeline (Blue/Green, Rollback, Health Gate)                   │
│  [M85.8] CI/CD Security Gate Enforcement & Full Test Coverage                           │
│  [M85.9] Dashboard God Component Decomposition & Zod Schema Validation                 │
│  [M85.10] Load Testing, Performance Benchmarks & Public Technical Writing               │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

#### 🚨 Milestone 85.5: P0 Secret Rotation, Git History Purge & Script Cleanup
*   **Gap Identified & Verification Status:**
    - ✅ **Already Fixed in Working Files:** `DEPLOYMENT.md` sanitized with `<YOUR_PROJECT_REF>`/`<YOUR_DB_PASSWORD>` placeholders; `encryption_adapter.py` now strictly raises `ValueError` if `KEY_ENCRYPTION_KEY` is absent; `config.py` enforces `@model_validator validate_production_secrets`.
    - ⚠️ **Still Pending:** Hardcoded fallback admin keys in helper scripts (`cleanup_duplicate_tenants.py:12`, `seed_demo_tenants_and_data.py:21`), rotation of active production credentials, and past commit history containing historical plaintext secrets.
*   **Objective:** Eliminate all committed secrets, rotate all compromised credentials, and enforce environment-only cryptographic key injection across all tooling.
*   **Key Deliverables:**
    1.  Clean fallback hardcoded `ADMIN_MASTER_KEY` values from helper scripts (`cleanup_duplicate_tenants.py`, `seed_demo_tenants_and_data.py`) to require environment variables.
    2.  Rotate active Supabase DB password, OpenRouter API key, and admin master key on production infrastructure.
    3.  Run `git filter-repo` or BFG Repo Cleaner to permanently scrub all secrets from git commit history.
    4.  Add `gitleaks` pre-commit hook and GitHub Action to prevent future secret commits.
*   **Status:** **Planned (Priority: P0 — IMMEDIATE)**

#### 🚨 Milestone 85.6: Structured Exception Handling & Production Error Tracking
*   **Gap Identified:** 50+ files across `apps/api/src/` contain bare `except Exception` blocks that silently swallow errors. No Sentry, Datadog, or equivalent error tracking is configured. Forensic audit scored Observability at **3.5/10**.
*   **Objective:** Replace all silent exception suppression with structured error logging and deploy a production error tracking service.
*   **Key Deliverables:**
    1.  Audit all 50+ files with bare `except Exception` — replace with specific exception types (`ValueError`, `ConnectionError`, `TimeoutError`) and add `logger.exception(...)` with structured context (tenant_id, operation, input hash).
    2.  Integrate Sentry (free tier) into both FastAPI backend and Next.js frontend — automatic exception capture, breadcrumbs, and performance monitoring.
    3.  Add custom Sentry tags: `tenant_id`, `operation_type`, `retrieval_strategy` for multi-tenant error segmentation.
    4.  Configure Sentry alerts for error rate spikes (> 5% of requests in 15-minute window).
*   **Status:** **Planned (Priority: P0)**

#### 🔧 Milestone 85.7: Safe Deployment Pipeline (Blue/Green with Rollback)
*   **Gap Identified:** Current deployment via `git reset --hard origin/main` with no rollback mechanism, no canary routing, and no pre-deploy migration verification. Forensic audit flagged this as H-7.
*   **Objective:** Implement a safe, rollback-capable deployment pipeline for the Oracle VPS.
*   **Key Deliverables:**
    1.  Replace `git reset --hard` with timestamped release directories (`/opt/retriever/releases/2026-08-31T12-00/`) and a `current` symlink.
    2.  Pre-deploy: run Alembic migration check (`alembic check`) and verify no pending migrations before service restart.
    3.  Post-deploy: automated health gate — if `/health/readiness` fails 3 consecutive checks within 60s, auto-rollback to previous release by re-pointing `current` symlink and restarting services.
    4.  Add `deploy-api.yml` workflow step to persist previous release hash for 1-click manual rollback via `gh workflow run deploy-rollback`.
*   **Status:** **Planned (Priority: P1)**

#### 🔧 Milestone 85.8: CI/CD Security Gate Enforcement & Full Test Coverage
*   **Gap Identified:** `security.yml` has 3x `continue-on-error: true` on CodeQL/Trivy scans (security failures are silently ignored). `ci.yml` excludes integration tests (`-m "not integration"`) and omits `mypy` type checking.
*   **Objective:** Make CI gates fail-blocking, not advisory. Ensure security scans, type checking, and integration tests are enforced before merge.
*   **Key Deliverables:**
    1.  Remove all `continue-on-error: true` from `security.yml` — CodeQL and Trivy failures must block PR merges.
    2.  Add `mypy --strict` to CI pipeline with incremental adoption (start with `--ignore-missing-imports`, tighten over time).
    3.  Re-enable integration test markers in CI (move `integration` tests to a separate job with Docker Compose for PostgreSQL + Redis + RabbitMQ).
    4.  Add CORS origin allowlist validation test — assert that `allow_origins` never contains `"*"` when `allow_credentials=True`.
*   **Status:** **Planned (Priority: P1)**

#### 🔧 Milestone 85.9: Dashboard God Component Decomposition & Runtime Validation
*   **Gap Identified:** `src/app/dashboard/page.tsx` is a 2,072-line god component. `src/app/api/client/*/route.ts` routes lack runtime Zod schema validation on incoming JSON bodies. Forensic audit flagged both as P2.
*   **Objective:** Decompose the dashboard into focused modules and add runtime type safety to all API routes.
*   **Key Deliverables:**
    1.  Extract dashboard into focused custom hooks (`useScopeManager`, `useInvoiceLedger`, `useMilestoneTracker`) and modular widget components (`ScopeCard`, `InvoiceTable`, `MilestoneTimeline`, `CopilotPanel`).
    2.  Target: no single file > 400 lines, each component with a clear single responsibility.
    3.  Add Zod schema validation to all `src/app/api/client/*/route.ts` endpoints — parse and validate request bodies before processing.
    4.  Migrate `/api/revalidate` from `?secret=` query parameter to `x-api-key` header authentication (forensic P3).
*   **Repo Scope:** `Prateek_website`
*   **Status:** **Planned (Priority: P2)**

#### 🎯 Milestone 85.10: Load Testing, Performance Benchmarks & Public Technical Writing
*   **Gap Identified:** Zero load testing evidence for a SaaS product. No public technical blog posts or OSS contributions demonstrating engineering depth to potential employers/clients.
*   **Objective:** Establish quantitative performance baselines and build public developer credibility through technical writing and open-source contributions.
*   **Key Deliverables:**
    1.  **Load Testing Suite:** Write k6 / Locust scripts targeting core Retriever endpoints (`/v1/chat`, `/v1/search`, `/v1/documents`) with 50/100/500 concurrent users. Document P50/P95/P99 latencies, max throughput, and breaking points.
    2.  **Performance Regression CI Gate:** Add load test baseline assertions to CI — fail if P95 latency regresses > 20% from baseline.
    3.  **Public Architecture Deep-Dives:** Publish 3–5 technical blog posts (on personal blog + dev.to/Hashnode cross-post) covering:
        - "Building a Multi-Tenant RAG Platform with Hexagonal Architecture"
        - "How I Implemented ColBERT MaxSim Late-Interaction Reranking"
        - "Safari ITP vs OAuth: Engineering a Multi-Cookie Chunking Auth Adapter"
        - "Forensic Self-Auditing: How I Caught My Own Technical Debt"
    4.  **Strategic OSS Contributions:** Submit 3–5 meaningful PRs to established projects (FastAPI, LangChain, pgvector, Ollama) to build external engineering credibility.
*   **Status:** **Planned (Priority: P1 — Career Critical)**

---

#### Updated Multi-Layer Stack Delivery Matrix (Phase J.6 Additions)

| Stack Layer | Milestone | Feature | Primary Impact | Effort | Risk | Target Phase |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Security P0** | **M85.5** | Secret Rotation & Git Purge | **Critical** (Active credential exposure) | Low | High | Phase J.6 |
| **Observability** | **M85.6** | Exception Handling & Sentry | **Critical** (Blind production failures) | Medium | Low | Phase J.6 |
| **Deployment** | **M85.7** | Safe Deploy & Rollback | **High** (Zero-downtime resilience) | Medium | Low | Phase J.6 |
| **CI/CD** | **M85.8** | Security Gates & Full Tests | **High** (Silent vulnerability bypass) | Low | Low | Phase J.6 |
| **Frontend** | **M85.9** | Dashboard Decomp & Zod | **Medium** (Maintainability & runtime safety) | Medium | Low | Phase J.6 |
| **Career & SaaS** | **M85.10** | Load Tests & Tech Writing | **Critical** (Employability & SaaS credibility) | Medium | Low | Phase J.6 |

---

## **Related Architecture & Cross-References**

- [Unified Master Roadmap (SSoT)](../../Prateek_website/docs/UNIFIED_MASTER_ROADMAP.md)
- [RAG App Studio PRD](../../Prateek_website/docs/24_RAG_App_Studio_PRD.md)
- [Scoping Dogfooding Tenant (`prateeq_scoping`)](../../Prateek_website/docs/25_SOTA_Scoping_Engine_PRD.md)
- [Logical Architecture Blueprint](architecture.md)
- [Physical System Design](implementation/system-design.md)
