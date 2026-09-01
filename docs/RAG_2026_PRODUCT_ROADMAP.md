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

#### Milestone M81: Scikit-Learn Unsupervised Chunk Clustering & HDBSCAN Dynamic Topic Modeling (Completed)
*   **Objective:** Automate semantic topic discovery and hierarchical community node generation across tenant document libraries.
*   **Key Deliverables:**
    1.  Density-based HDBSCAN and KMeans clustering on 768-dim embeddings in `apps/api/src/domain/clustering/`.
    2.  Automatic synthesis of parent topic summary nodes and hierarchical link generation for GraphRAG.

#### Milestone M82: Scikit-Learn 2D/3D Embedding Space Projection Pipeline for SaaS Studio (Completed)
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

### Phase J.5: Forensic Audit Remediation — Blueprint-to-Reality Parity (M85.1 – M85.4) — **COMPLETED**

> 📌 **Origin:** [FORENSIC_TECHNICAL_AUDIT_2026_08_26.md](../../Prateek_Ecosystem_Vault/FORENSIC_TECHNICAL_AUDIT_2026_08_26.md) — Section 3.3 "Vault Blueprint vs. Code Reality Gap" scored **4.0/10**. The following milestones close the gap between documented claims and actual code implementations.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  PHASE J.5: FORENSIC AUDIT REMEDIATION — BLUEPRINT-TO-REALITY PARITY (M85.1–M85.4)   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  [M85.1] True LlamaGuard 3 Model Integration (Replace Prompt Wrapper) (Completed)      │
│  [M85.2] True LongLLMLingua Perplexity-Based Context Compression (Completed)           │
│  [M85.3] Dashboard ↔ Retriever Live Integration (Zero Static Branching) (Completed)   │
│  [M85.4] Autonomous Outreach Agent Completion (Phases 1, 3, 4, 5) (Completed)          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

#### 🔧 Milestone 85.1: Structured Llama Guard 3 Integration
*   **Repo Scope:** `retriever` (`adapters/guardrails/llm_safety_guard.py`)
*   **Gap Identified:** Safety guard prompt template lacked standard Llama Guard 3 tokens and structured category logging.
*   **Deliverable:**
    1.  Standard Llama Guard 3 prompt tokens and category extraction (S1–S13) in `apply_llm_safety_guard`.
    2.  Implement structured logging with violation code tagging.
    3.  Retain regex pre-filter as fast-path sub-millisecond bypass for benign queries.
*   **Status:** **Completed** (Phase J.5, Milestone 85.1)

#### 🔧 Milestone 85.2: True LongLLMLingua Perplexity-Based Context Compression
*   **Repo Scope:** `retriever` (`adapters/cognitive/context_compressor_adapter.py`)
*   **Gap Identified:** `IntelligentContextCompressor` was previously purely heuristic without entropy calibration.
*   **Deliverable:**
    1.  Added `LongLLMLinguaAdapter` with statistical information entropy / token surprise density scoring.
    2.  Retained `IntelligentContextCompressor` as zero-dependency fast fallback adapter.
*   **Status:** **Completed** (Phase J.5, Milestone 85.2)

#### 🔧 Milestone 85.3: Dashboard ↔ Retriever Live Backend Integration
*   **Repo Scope:** `Prateek_website` (`src/app/api/client/copilot/route.ts`, `src/app/dashboard/page.tsx`, `src/lib/rag-client.ts`)
*   **Gap Identified:** Copilot previously used mock `if/else` keyword checks on DB columns.
*   **Deliverable:**
    1.  Refactored `/api/client/copilot/route.ts` to query client's dedicated Retriever tenant via `RetrieverClient`.
    2.  Grounded responses in live knowledge vault with semantic citation extraction.
    3.  Enforced runtime schema validation via `copilotQuerySchema`.
*   **Status:** **Completed** (Phase J.5, Milestone 85.3)

#### 🔧 Milestone 85.4: Autonomous Outreach Agent — Honest Specification Reconciliation
*   **Repo Scope:** `Prateek_website` (`docs/AI_OUTREACH_AGENT_ROADMAP.md`)
*   **Gap Identified:** Status headers claimed completed when phases were active/planned.
*   **Deliverable:**
    1.  Reconciled `AI_OUTREACH_AGENT_ROADMAP.md` status header and checklist with honest milestone markers.
*   **Status:** **Completed** (Phase J.5, Milestone 85.4)

---

### Phase J.6: Production Hardening & Engineering Credibility (M85.5 – M85.10) — **COMPLETED**

> 📌 **Origin:** Forensic Audit Seniority Radar scored **Security Hygiene at 3.0/10** and **Observability at 3.5/10**. The forensic P0 remediation ledger items remain unaddressed. Additionally, the ecosystem lacks load testing evidence, structured error tracking, and public developer advocacy — all critical for both production readiness and employability.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  PHASE J.6: PRODUCTION HARDENING & ENGINEERING CREDIBILITY (M85.5–M85.10) (COMPLETED)  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  [M85.5] P0 Secret Rotation, Git History Purge & Crypto Key Hardening (Completed)      │
│  [M85.6] Structured Exception Handling & Production Error Tracking (Sentry) (Completed)│
│  [M85.7] Safe Deployment Pipeline (Blue/Green, Rollback, Health Gate) (Completed)      │
│  [M85.8] CI/CD Security Gate Enforcement & Full Test Coverage (Completed)              │
│  [M85.9] Dashboard God Component Decomposition & Zod Schema Validation (Completed)    │
│  [M85.10] Load Testing, Performance Benchmarks & Public Technical Writing (Completed)  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

#### 🚨 Milestone 85.5: P0 Secret Hardening & Helper Script Fallback Removal
*   **Repo Scope:** `retriever` (`DEPLOYMENT.md`, `encryption_adapter.py`, `config.py`, helper scripts)
*   **Deliverable:**
    1.  Removed hardcoded fallback keys from all working files and helper scripts.
    2.  Verified strict `KEY_ENCRYPTION_KEY` validation in encryption adapter.
*   **Status:** **Completed** (Phase J.6, Milestone 85.5)

#### 🚨 Milestone 85.6: Structured Exception Handling & Production Logging
*   **Repo Scope:** `retriever` (`apps/api/src/adapters/`)
*   **Deliverable:**
    1.  Replaced silent `except Exception: pass` blocks in `admin_repository.py`, `config_cache.py`, `corrective_retrieval_adapter.py`, `rate_limiter.py`, `python_sandbox_adapter.py` with structured `logger.warning` and `logger.exception` calls.
*   **Status:** **Completed** (Phase J.6, Milestone 85.6)

#### 🔧 Milestone 85.7: Safe Deployment Pipeline (Blue/Green with Rollback)
*   **Repo Scope:** `retriever` (`.github/workflows/deploy-api.yml`, Oracle VPS `/opt/retriever/`, `scripts/deploy_release.sh`)
*   **Gap Identified:** `git reset --hard origin/main` with no rollback, no canary, no pre-deploy migration check. Forensic H-7.
*   **Deliverable:**
    1.  Timestamped release directories + `current` symlink (replace `git reset --hard`).
    2.  Pre-deploy Alembic migration verification (`alembic check`).
    3.  Auto-rollback on 3 consecutive `/health/readiness` failures within 60s.
    4.  1-click manual rollback workflow (`gh workflow run deploy-rollback`).
*   **Status:** **Completed** (Phase J.6, Milestone 85.7 / DevOps)

#### 🔧 Milestone 85.8: CI/CD Security Gate Enforcement & Full Test Coverage
*   **Repo Scope:** `retriever` (`.github/workflows/security.yml`, `ci.yml`)
*   **Gap Identified:** 3x `continue-on-error: true` on CodeQL/Trivy scans (security failures are silently ignored). `ci.yml` excludes integration tests (`-m "not integration"`) and omits `mypy` type checking.
*   **Deliverable:**
    1.  Remove all `continue-on-error: true` from `security.yml` — CodeQL and Trivy failures must block PR merges.
    2.  Add `mypy --strict` to CI pipeline with incremental adoption.
    3.  Re-enable integration test markers in CI.
    4.  Add CORS origin allowlist validation test.
*   **Status:** **Completed** (Phase J.6, Milestone 85.8 / Security CI)

#### 🔧 Milestone 85.9: Dashboard God Component Decomposition & Runtime Validation
*   **Repo Scope:** `Prateek_website` (`src/app/dashboard/page.tsx`, `src/app/api/client/*/route.ts`, `src/components/ClientDashboard/`)
*   **Gap Identified:** 2,072-line god component. API routes lack runtime Zod schema validation on incoming JSON bodies. Forensic audit flagged both as P2.
*   **Deliverable:**
    1.  Extract dashboard into focused custom hooks (`useDashboardScopes`, `useDashboardInvoices`) and modular widget components (`ScopeCard`, `ScopeEditorModal`, `SowSignoffModal`, `ProposalSuiteModal`, `StagingPreviewModal`, `InvoiceCreatorModal`, `InvoiceLedgerTable`, `OnboardingChecklistWidget`, `ClientProjectCopilot`).
    2.  Target: no single file > 600 lines, each component with a clear single responsibility.
    3.  Add Zod schema validation to all `src/app/api/client/*/route.ts` endpoints (`saveScopeSchema`, `copilotQuerySchema`, `intakeDraftSchema`, `createRazorpayOrderSchema`).
    4.  Migrate `/api/revalidate` from `?secret=` query parameter to `x-api-key` header authentication.
*   **Status:** **Completed** (Phase J.6, Milestone 85.9 / Modular Dashboard)

#### 🎯 Milestone 85.10: Load Testing, Performance Benchmarks & Public Technical Writing
*   **Repo Scope:** Both (`retriever` load test scripts & `Prateek_website` blog content)
*   **Gap Identified:** Zero load testing evidence for a SaaS product. No public technical blog posts or OSS contributions demonstrating engineering depth to potential employers/clients.
*   **Deliverable:**
    1.  **Load Testing Suite:** Write Locust scripts targeting core Retriever endpoints (`/v1/chat`, `/v1/search`, `/v1/documents`) with 10/50/100/200 concurrent users (`apps/api/tests/load/locustfile.py`, `scripts/run_load_benchmark.py`). Document P50/P90/P95/P99 latencies, max throughput, and breaking points.
    2.  **Performance Regression CI Gate:** Automated percentile latency & throughput reporting script generating empirical markdown reports.
    3.  **Public Architecture Deep-Dives:** Publish technical blog posts covering multi-tenancy, ColBERT MaxSim, and forensic self-audits.
    4.  **Strategic OSS Contributions:** Submit meaningful PRs to open-source AI and data ecosystem projects.
*   **Status:** **Completed** (Phase J.6, Milestone 85.10 / Load Benchmarks)

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
