# RAG System Audit Report

**Date:** 2026-07-15  
**Auditor:** RAG Systems Auditor  
**System:** Retriever (monorepo at `/Users/prateeksharma/Developer/retriever`)  
**Maturity:** Advanced RAG (Production-Ready, with gaps toward Agentic)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Component-by-Component Analysis](#2-component-by-component-analysis)
   - 2.1 [Data Ingestion & Chunking Strategy](#21-data-ingestion--chunking-strategy)
   - 2.2 [Retrieval Precision & Recall](#22-retrieval-precision--recall)
   - 2.3 [Context Management & Generation Quality](#23-context-management--generation-quality)
   - 2.4 [Pipeline Dynamics & Architecture](#24-pipeline-dynamics--architecture)
   - 2.5 [Evaluation & Metrics Metricity](#25-evaluation--metrics-metricity)
3. [Actionable Optimization Roadmap](#3-actionable-optimization-roadmap)
   - 3.1 [Quick Wins](#31-quick-wins)
   - 3.2 [Structural Upgrades](#32-structural-upgrades)
4. [Agent Execution Guide](#4-agent-execution-guide)
5. [Appendix: File Reference Map](#5-appendix-file-reference-map)
6. [Appendix: Cross-Reference with Existing Docs](#6-appendix-cross-reference-with-existing-docs)

---

## 1. Executive Summary

**Maturity Level: Advanced RAG** — well-architected hexagonal system with hybrid search, self-query, reranking, semantic caching, history compression, citation validation, model failover, and corrective retrieval. Closer to Agentic/Adaptive than Naive.

**Critical vulnerabilities resolved.** All 3 critical findings are now addressed: evaluation framework (E-1), query rewriting (R-4/P-1), and corrective retrieval (P-2).

**Summary of counts across all severity levels:**

| Severity | Total | Completed | Pending | Key Theme |
|----------|-------|-----------|---------|-----------|
| Critical | 3 | 3 | 0 | All resolved: eval + HyDE + Self-RAG 🟢 |
| High | 8 | 8 | 0 | All resolved: chunker bugs, BM25, MMR, stale cache, token estimation, passive citations, search metrics 🟢 |
| Medium | 9 | 9 | 0 | All resolved: + adaptive retrieval + query routing 🟢 |
| Low | 5 | 5 | 0 | All resolved: default flags, warm caches, budget alerts, no-op tasks + overlap fix + context format 🟢 |
| **Total** | **33** | **33** | **0** | **All findings resolved 🟢** |

**Overall progress:** 33 of 33 findings completed. All findings resolved 🟢. No remaining findings.

---

## 2. Component-by-Component Analysis

### 2.1 Data Ingestion & Chunking Strategy

**Files involved:**
- `packages/processing-core/src/processing_core/chunker.py` — all 3 chunker implementations
- `packages/processing-core/src/processing_core/pdf_parser.py` — PDF text extraction
- `workers/src/tasks/__init__.py` — worker orchestration, vision fallback
- `apps/api/src/adapters/cognitive/tiktoken_chunker.py` — API-side chunker
- `apps/api/src/domain/abstractions/config.py` — `ChunkingSettings`, `MetadataExtractorConfig`

#### [+] Strengths

- Three chunking strategies (`fixed_window`, `recursive`, `semantic`) with per-tenant configurability via `ChunkingSettings`
- Vision fallback for zero-text PDFs and images via GPT-4o (`_describe_with_vision`)
- Metadata extraction (regex + LLM) with per-tenant extractor config
- File dedup via SHA-256, event-driven pipeline (Celery + RabbitMQ)
- Chunk size/overlap/strategy configurable per tenant via `ChunkingSettings`

#### [-] Gaps & Vulnerabilities

| # | Finding | File:Line | Severity | Status | Description |
|---|---------|-----------|----------|--------|-------------|
| C-1 | **Semantic chunker naive sentence split regex** | `chunker.py:165` | **High** | 🟢 Completed | Improved regex to handle abbreviations, decimals, URLs. Uses `(?<=[.?!])\s+(?=[A-Z"\'(])` to only split when the next char is uppercase, quote, or paren. |
| C-2 | **Semantic chunker double-trigger (size AND similarity)** | `chunker.py:182-224` | **High** | 🟢 Completed | Made size split and similarity split mutually exclusive via `did_split` flag. Both triggers now share consistent overlap logic using `chunk_overlap` parameter instead of single-sentence carry. |
| C-3 | **No hierarchical (parent-child) chunking** | (missing feature) | **Medium** | 🟢 Completed | `build_hierarchy()` groups N child chunks into parent sections, sets `parent_chunk_id`. Opt-in per tenant. |
| C-4 | **No OCR — scanned PDFs fail silently** | `workers/src/tasks/__init__.py:201-204` | **Medium** | 🟢 Completed | Tesseract OCR fallback + multi-page vision. Chain: pdfplumber → tesseract → vision (all pages). |
| C-5 | **No table/chart structural extraction** | (missing feature) | **Low** | 🟢 Completed | `extract_tables_from_pdf()` via pdfplumber built-in extract_tables. Stored in chunk metadata as structured JSON. |
| C-6 | **Recursive chunker overlap walks backward** | `chunker.py:116-125` | **Low** | 🟢 Completed | Now uses forward tail-slicing — O(n) instead of O(n²), carries correct tail content. |

### 2.2 Retrieval Precision & Recall

**Files involved:**
- `apps/api/src/domain/retrieval/search_service.py` — `HybridSearchService` (all fusion + reranking + web fallback logic)
- `apps/api/src/adapters/vector/vector_repository.py` — `PgVectorSearchAdapter`
- `apps/api/src/adapters/vector/keyword_repository.py` — `PgKeywordSearchAdapter`
- `apps/api/src/adapters/vector/filter_builder.py` — `build_filter_clause`
- `apps/api/src/adapters/cognitive/reranker_adapter.py` — `CohereRerankerAdapter`
- `apps/api/src/adapters/cognitive/self_query_adapter.py` — `LLMSelfQueryAdapter`
- `apps/api/src/adapters/database/semantic_cache.py` — `PgSemanticCacheAdapter`
- `apps/api/src/adapters/cognitive/tavily_adapter.py` — web search fallback
- `apps/api/src/domain/abstractions/retrieval.py` — ports and models

#### [+] Strengths

- Hybrid search: dense (pgvector cosine) + sparse (Postgres tsvector full-text)
- RRF fusion with configurable `rrf_k`
- Cohere `rerank-v3.5` with threshold filtering
- Self-query (NL → metadata filters via LLM)
- Semantic cache (pgvector, 24h TTL, cosine < 0.01 threshold)
- Web search fallback (Tavily) with decaying score injection
- Metadata filter compiler with 10 operators + tag array containment
- Every external call wrapped in try/except — zero hard failures

#### [-] Gaps & Vulnerabilities

| # | Finding | File:Line | Severity | Status | Description |
|---|---------|-----------|----------|--------|-------------|
| R-1 | **Keyword leg uses `plainto_tsquery`** | `keyword_repository.py:31,37` | **High** | 🟢 Completed | Switched to `websearch_to_tsquery` — supports `"..."` phrases, `-` excludes, `OR` operators. |
| R-2 | **No BM25 scoring** | `keyword_repository.py:29-31` | **High** | 🟢 Completed | Two-stage: `ts_rank_cd` for fast DB-side retrieval, in-app pure-Python BM25 for precise Stage 2 re-ranking. |
| R-3 | **Reranker only operates on provided top-K** | `reranker_adapter.py:44` | **High** | 🟢 Completed | Added `rerank_candidate_multiplier` (default 5). Fan-out retrieves `top_k * multiplier` candidates before reranking to `top_k`. |
| R-4 | **No query expansion** | (missing feature) | **Critical** | 🟢 Completed | HyDE implemented: LLM generates hypothetical document, used for embedding. Wire via `QueryRewriterProvider` + `LLMQueryRewriterAdapter`. |
| R-5 | **No MMR diversity sampling** | `search_service.py:98-99` | **Medium** | 🟢 Completed | TF-IDF cosine MMR between reranker and trim. Configurable lambda, per-tenant flag. |
| R-6 | **Self-query uses the same LLM as generation** | `self_query_adapter.py:28-29` | **Medium** | 🟢 Completed | Defaults to `gemini-1.5-flash` (cheaper, faster) independently of generation model. |
| R-7 | **Self-query defaults to disabled** | `config.py:12` | **Low** | 🟢 Completed | Flipped `enable_self_query` to `True` by default. |
| R-8 | **Semantic cache has no invalidation on data update** | `semantic_cache.py` | **High** | 🟢 Completed | Worker `DELETE FROM semantic_cache WHERE tenant_id = :tenant_id` on successful document re-index. |
| R-9 | **Web search fallback defaults to disabled** | `config.py:11` | **Low** | 🟢 Completed | Flipped `enable_web_search` to `True` by default. |

### 2.3 Context Management & Generation Quality

**Files involved:**
- `apps/api/src/domain/inference/orchestrator.py` — `InferenceOrchestrator`
- `apps/api/src/domain/inference/prompt_builder.py` — `PromptBuilder`
- `apps/api/src/domain/inference/citation_validator.py` — `CitationValidator`
- `apps/api/src/domain/inference/cost_calculator.py` — cost tracking

#### [+] Strengths

- Token budget compression: trims oldest history first, then prunes lowest-scoring context chunks
- History summarization after configurable turn count (default 15)
- Citation validation via `[Source: chunk_id]` regex — invalid citations flagged with warning
- Structured context header with per-chunk source tags
- SSE streaming with citation validation on stream completion
- Per-tenant named prompt templates via `PromptTemplateRegistry`

#### [-] Gaps & Vulnerabilities

| # | Finding | File:Line | Severity | Status | Description |
|---|---------|-----------|----------|--------|-------------|
| G-1 | **Token estimation uses `len(text) // 4`** | `prompt_builder.py:18-21` | **High** | 🟢 Completed | Replaced with actual `tiktoken.get_encoding("cl100k_base").encode(text)` for accurate token counts. |
| G-2 | **No "lost in the middle" mitigation** | `prompt_builder.py:57` | **Medium** | 🟢 Completed | Added instruction to `CONTEXT_HEADER`: "all chunks are equally important, order does not indicate priority". |
| G-3 | **Citation validation is passive** | `orchestrator.py:245-250` | **High** | 🟢 Completed | Strip invalid `[Source: X]` from response instead of appending warning. |
| G-4 | **Context block is flat text** | `prompt_builder.py:76-90` | **Low** | 🟢 Completed | Grouped by `document_id`, section-aware headings, parent chunk grouping. |
| G-5 | **No structured output in generation** | `orchestrator.py:232-238` | **Medium** | 🟢 Completed | `json_schema` wired from `RetrievalSettings` → `InferenceRequest` in orchestrator. |

### 2.4 Pipeline Dynamics & Architecture

**Files involved:**
- `apps/api/src/main.py` — DI wiring, routes, guardrails, SSE
- `apps/api/src/domain/retrieval/search_service.py` — search pipeline
- `apps/api/src/domain/inference/orchestrator.py` — generation pipeline
- `apps/api/src/adapters/cognitive/routing_provider.py` — `RoutingLLMProvider`
- `workers/src/tasks/__init__.py` — ingestion pipeline

#### [+] Strengths

- **Advanced RAG** with pre-retrieval (self-query) and post-retrieval (reranking) optimization steps
- Hexagonal architecture — domain logic has zero infrastructure imports
- Model failover with exponential backoff + fallback provider (`RoutingLLMProvider`)
- Event-driven ingestion (Celery tasks, RabbitMQ events, staggered queues)
- Graceful degradation on all external dependencies
- Per-tenant configuration with Redis cache + env fallback chain
- Industry config presets (legal, medical, finance, hr)

#### [-] Gaps & Vulnerabilities

| # | Finding | File:Line | Severity | Status | Description |
|---|---------|-----------|----------|--------|-------------|
| P-1 | **No query rewriting** | (missing feature) | **Critical** | 🟢 Completed | HyDE via `QueryRewriterProvider` port + `LLMQueryRewriterAdapter`. Replaces query for embedding, keeps original for keyword leg. |
| P-2 | **No Self-RAG / corrective retrieval** | (missing feature) | **Critical** | 🟢 Completed | CorrectiveRetrievalProvider port + LLMCorrectiveRetrievalAdapter. LLM-as-judge evaluates confidence, reformulates query, re-retrieves and re-generates. Opt-in per tenant. Max 2 rounds. |
| P-3 | **No adaptive retrieval** | `config.py:57-68` | **Medium** | 🟢 Completed | `top_k`, search flags dynamically set by `LLMQueryIntentAdapter`. |
| P-4 | **No query routing** | `search_service.py` | **Medium** | 🟢 Completed | Combined classifier routes factoids to vector-only, complex queries to full hybrid. |
| P-5 | **Self-query adds serial latency** | `search_service.py:54-56` | **Medium** | 🟢 Completed | Added `asyncio.wait_for(..., timeout=2.0)` gating in self-query adapter; returns `[]` on timeout. |

### 2.5 Evaluation & Metrics Metricity

**Files involved:**
- `apps/api/src/adapters/telemetry/prometheus_metrics.py` — metrics
- `apps/api/src/adapters/telemetry/otel_tracer.py` — tracing
- `apps/api/src/adapters/telemetry/logger.py` — structlog config
- `apps/api/src/adapters/database/feedback_repository.py` — feedback
- `workers/src/tasks/__init__.py` — `warm_caches` (no-op), `cleanup_expired_data`

#### [+] Strengths

- Prometheus counters for token consumption, cost spend, request latency
- Per-session inference logs stored in DB
- Sentry error tracking
- OpenTelemetry tracing spans
- Feedback repository (thumbs up/down)
- Structured JSON logging via structlog

#### [-] Gaps & Vulnerabilities

| # | Finding | File:Line | Severity | Status | Description |
|---|---------|-----------|----------|--------|-------------|
| E-1 | **No RAG evaluation framework** | (missing feature) | **Critical** | 🟢 Completed | RAGAS + DeepEval integrated via admin API + Celery nightly. |
| E-2 | **No search quality metrics** | (missing feature) | **High** | 🟢 Completed | Citation-based nDCG@10, MRR, hit_rate@10 emitted as Prometheus observations per request from orchestrator. |
| E-3 | **Feedback is binary** | `inference.py:190-198` | **Medium** | 🟢 Completed | Added per-dimension `scores: dict[str, int]` alongside existing `rating`. JSONB column + API + analytics. |
| E-4 | **No ground-truth test set** | (missing feature) | **High** | 🟢 Completed | `eval_datasets` + `eval_questions` tables + admin CRUD API for per-tenant datasets. |
| E-5 | **No A/B testing infrastructure** | (missing feature) | **Medium** | 🟢 Completed | Minimal in-memory experiment framework: `ExperimentConfig` on `TenantConfiguration`, hash-based variant assignment, override application, experiment logging in `InferenceLog.notes`. |
| E-6 | **No budget alerts** | (missing feature) | **Low** | 🟢 Completed | `BudgetSettings` + `NotificationProvider` port + `LoggingNotificationAdapter`. In-memory daily/monthly check in orchestrator. |
| E-7 | **`warm_caches` is a no-op** | `workers/src/tasks/__init__.py:607-609` | **Low** | 🟢 Completed | Removed the no-op task and its beat schedule entry in `celery_app.py`. |

---

## 3. Actionable Optimization Roadmap

### 3.1 Quick Wins

Items in this section are low effort (minutes to a few hours), high impact, and safe to implement immediately.

| Priority | ID | Fix | File(s) | Effort | Impact | Status |
|----------|----|-----|---------|--------|--------|--------|
| P0 | G-1 | **Replace `len//4` with actual tiktoken** in `_estimate_tokens` | `prompt_builder.py:18-21` | 10 min | Prevents false-positive compression | 🟢 Completed |
| P0 | R-7 | **Enable self-query by default** (`enable_self_query: True`) | `config.py:12` | 5 min | Major recall improvement | 🟢 Completed |
| P0 | R-9 | **Enable web search by default** (`enable_web_search: True`) | `config.py:11` | 5 min | Zero-effort hallucination guardrail | 🟢 Completed |
| P1 | R-3 | **Increase candidate pool for reranker** — retrieve `top_k * multiplier`, rerank to `top_k` | `search_service.py`, `config.py`, `retrieval.py` | 30 min | Fixes missed-recall ceiling | 🟢 Completed |
| P1 | C-1 | **Fix semantic chunker sentence-split regex** | `chunker.py:165` | 30 min | Reduces garbage chunk boundaries | 🟢 Completed |
| P1 | C-2 | **Fix semantic chunker double-trigger** — make size/similarity splits mutually exclusive | `chunker.py:182-224` | 1 hr | Eliminates tiny fragment chunks | 🟢 Completed |
| P1 | G-2 | **Add "lost in the middle" system prompt instruction** | `prompt_builder.py` | 5 min | Better context utilization | 🟢 Completed |
| P2 | R-1 | **Switch keyword leg to `websearch_to_tsquery`** | `keyword_repository.py:31,37` | 30 min | Better sparse retrieval | 🟢 Completed |
| P2 | E-7 | **Remove `warm_caches` no-op** | `workers/src/tasks/__init__.py`, `celery_app.py` | 5 min | Cleanup | 🟢 Completed |

### 3.2 Structural Upgrades

Items in this section are higher effort (days to weeks) and may require new ports, adapters, infrastructure, or testing.

| Priority | ID | Fix | File(s) | Effort | Impact | Status |
|----------|----|-----|---------|--------|--------|--------|
| P0 | E-1 | **Add RAG evaluation framework** — integrate RAGAS or DeepEval | New `evaluation` context, scheduled batch task | 1-2 weeks | **Highest impact** | 🟢 Completed |
| P0 | R-4 / P-1 | **Add query rewriting/expansion** — HyDE, multi-query, or synonym expansion | New `QueryRewriter` port + adapter | 3-5 days | Major recall boost | 🟢 Completed |
| P0 | P-2 | **Add Self-RAG / corrective retrieval** — evaluate & re-retrieve on insufficient context | `CorrectiveRetrievalService` + `LLMCorrectiveRetrievalAdapter` | 1 week | Direct hallucination reduction | 🟢 Completed |
| P1 | E-4 | **Build a ground-truth test set** — 100-200 Q&A pairs per tenant | New `eval_datasets` table + admin API | 2 weeks | Enables A/B testing and regression prevention | 🟢 Completed |
| P1 | E-2 | **Add search quality metrics** — nDCG, MRR, Hit Rate | `Orchestrator._emit_search_quality_metrics` using citation proxy | 1 day | Enables quantitative tuning | 🟢 Completed |
| P1 | R-5 | **Add MMR diversity sampling** — post-reranker diversity bonus | New `MMRDiversityProvider` port | 1-2 days | Broader coverage, less redundancy | 🟢 Completed |
| P1 | R-8 | **Cache invalidation on data update** — clear affected cache on re-index | `semantic_cache.py` + worker event handler | 2 hr | Eliminates stale cache poisoning | 🟢 Completed |
| P2 | C-3 | **Add hierarchical chunking** — `parent_chunk_id` + section summary | `chunker.py`, worker, prompt builder | 1 week | Better context for large documents | 🟢 Completed |
| P2 | R-2 | **Replace keyword leg with proper BM25** — `ts_rank_cd` or dedicated search engine | `keyword_repository.py` | 1 week | Normalized, comparable scores | 🟢 Completed |
| P2 | P-3 | **Add adaptive retrieval** — dynamic `top_k` based on query complexity | `search_service.py`, `query_intent_adapter.py` | 3-5 days | Right-sized latency/recall | 🟢 Completed |
| P2 | P-4 | **Add query routing** — classify query type, select strategy | `query_intent_adapter.py`, `search_service.py` | 3-5 days | Reduced latency for simple queries | 🟢 Completed |
| P2 | P-5 | **Add self-query timeout gating** — proceed without filters after 300ms | `self_query_adapter.py`, `search_service.py` | 1 day | Reduces worst-case latency | 🟢 Completed |
| P2 | R-6 | **Self-query uses cheaper/faster model** | `self_query_adapter.py:28-29` | 1 day | Reduces search latency | 🟢 Completed |
| P2 | C-4 | **Add OCR for scanned PDFs** — `pytesseract` + multi-page vision | `workers/src/tasks/__init__.py` | 3-5 days | Scanned docs no longer empty | 🟢 Completed |
| P2 | C-5 | **Add table extraction** — pdfplumber `extract_tables` | `pdf_parser.py`, worker | 3-5 days | Tables as structured data | 🟢 Completed |
| P3 | G-5 | **Wire structured output through orchestrator** | `orchestrator.py`, `config.py` | 1 day | Guaranteed JSON output | 🟢 Completed |
| P3 | G-3 | **Make citation validation active** — strip or regenerate on mismatch | `orchestrator.py:245-250`, `citation_validator.py` | 1 day | No hallucinated citations | 🟢 Completed |

---

## 4. Agent Execution Guide

This section is for AI agents implementing the fixes above. Follow this process for each item.

### 4.1 Before Starting Any Fix

1. Read `docs/engineering/agent-context.md` for repository conventions
2. Read `docs/engineering/engineering-playbook.md` for code style rules
3. Read `apps/api/src/domain/abstractions/` for the relevant port(s) before writing any adapter
4. Run `test_architecture.py` before and after changes to verify hexagonal boundaries
5. Run the full test suite after each change: `cd apps/api && poetry run pytest -x`

### 4.2 Quick Fix Checklist

For items tagged "Quick Win":

- [ ] Read the target file fully before editing
- [ ] Check for existing tests for the function being modified
- [ ] Make the minimal change (one function, one file where possible)
- [ ] Verify with `pytest -x` (all existing tests pass)
- [ ] Update `AGENTS.md` if the fix introduces a new pattern or configuration

### 4.3 Structural Upgrade Checklist

For items tagged "Structural Upgrade":

- [ ] Design phase: verify the new port fits the existing abstraction pattern in `domain/abstractions/`
- [ ] Write the port (ABC) and domain model first — zero infrastructure imports
- [ ] Write the adapter(s) in `adapters/`
- [ ] Wire into DI in `main.py`
- [ ] Write tests: unit test the port contract, integration test the adapter
- [ ] Write an Alembic migration if new columns/tables are needed
- [ ] Verify with `pytest -x` and `ruff check .`
- [ ] Update `TECH_DEBT.md` if any deferred work is resolved

### 4.4 When to Ask for Clarification

- **Adding a new dependency** — stop and ask before adding any third-party library to `pyproject.toml` or `package.json`
- **Changing a port/abstraction** — existing adapters must not break; confirm the refactoring approach
- **Adding a new evaluation framework (E-1)** — confirm which framework (RAGAS vs DeepEval vs TruLens)
- **Ground-truth dataset (E-4)** — confirm format, storage, and whether to collect from production or from manual labeling
- **Query expansion strategy (R-4)** — confirm HyDE vs multi-query vs synonym expansion (or all three)

### 4.5 Precedence Among Fixes

Some items block others. Use this order:

```
E-4 (ground truth) ──► E-1 (evaluation) ──► E-2 (search metrics)
        │                                        │
        └── Needed to validate ──────────────────┘
                │
                ▼
R-4 / P-1 (query rewriting) ──► P-2 (Self-RAG) — 🟢 completed
        │                              │
        └── Feeds corrective ──────────┘
                │
                ▼
R-3 (rerank candidate pool) ──► R-5 (MMR)
C-2 (semantic chunker fix) ──► C-1 (sentence split fix)
R-1 (websearch_to_tsquery) ──► R-2 (BM25)
Quick Wins (P0-P1) ──► can be done independently, any order
G-3 (active citation validation) ──► G-5 (structured output) — both 🟢 completed
```

---

## 5. Appendix: File Reference Map

| Component | Key Files | Lines |
|-----------|-----------|-------|
| Chunking (3 strategies) | `packages/processing-core/src/processing_core/chunker.py` | 238 |
| PDF parsing | `packages/processing-core/src/processing_core/pdf_parser.py` | ~60 |
| Embedding retry | `packages/processing-core/src/processing_core/embedding.py` | ~40 |
| Worker ingestion pipeline | `workers/src/tasks/__init__.py` | 664 |
| Worker Celery config | `workers/src/celery_app.py` | ~60 |
| Hybrid search service | `apps/api/src/domain/retrieval/search_service.py` | 279 |
| Vector search adapter | `apps/api/src/adapters/vector/vector_repository.py` | 50 |
| Keyword search adapter | `apps/api/src/adapters/vector/keyword_repository.py` | 52 |
| Filter builder | `apps/api/src/adapters/vector/filter_builder.py` | 63 |
| Cohere reranker | `apps/api/src/adapters/cognitive/reranker_adapter.py` | 57 |
| Self-query (NL→filters) | `apps/api/src/adapters/cognitive/self_query_adapter.py` | 50 |
| Semantic cache | `apps/api/src/adapters/database/semantic_cache.py` | 78 |
| Web search (Tavily) | `apps/api/src/adapters/cognitive/tavily_adapter.py` | ~70 |
| Inference orchestrator | `apps/api/src/domain/inference/orchestrator.py` | 326 |
| Prompt builder | `apps/api/src/domain/inference/prompt_builder.py` | 138 |
| Citation validator | `apps/api/src/domain/inference/citation_validator.py` | 40 |
| Cost calculator | `apps/api/src/domain/inference/cost_calculator.py` | ~30 |
| Config models (tenant, pricing, flags) | `apps/api/src/domain/abstractions/config.py` | 168 |
| Retrieval ports + models | `apps/api/src/domain/abstractions/retrieval.py` | 133 |
| Inference ports + models | `apps/api/src/domain/abstractions/inference.py` | 212 |
| API routes + DI wiring | `apps/api/src/main.py` | 1620 |
| Auth/security | `apps/api/src/adapters/api/security.py` | ~150 |
| DB models (all ORM) | `apps/api/src/adapters/database/models.py` | ~300 |
| Prometheus metrics | `apps/api/src/adapters/telemetry/prometheus_metrics.py` | ~80 |
| Feedback repository | `apps/api/src/adapters/database/feedback_repository.py` | ~50 |
| Config presets (legal/medical/etc) | `apps/api/src/domain/config/presets.py` | ~100 |
| Routing LLM provider | `apps/api/src/adapters/cognitive/routing_provider.py` | ~100 |
| OpenAI adapter | `apps/api/src/adapters/cognitive/openai_adapter.py` | ~150 |
| Anthropic adapter | `apps/api/src/adapters/cognitive/anthropic_adapter.py` | ~130 |
| Config service | `apps/api/src/domain/config/config_service.py` | ~120 |
| DB connection + RLS | `apps/api/src/adapters/database/connection.py` | ~80 |
| Architecture doc | `docs/architecture.md` | 822 |
| Engineering playbook | `docs/engineering/engineering-playbook.md` | ~200 |
| Agent context | `docs/engineering/agent-context.md` | 74 |

---

## 6. Appendix: Cross-Reference with Existing Docs

### Already Tracked In

These findings overlap with items already in `TECH_DEBT.md` or `ROADMAP.md`:

| Finding | Already In | Notes | Status |
|---------|------------|-------|--------|
| C-4 (first-page-only vision) | `TECH_DEBT.md:255-258` | Resolved — multi-page vision + tesseract OCR | 🟢 Completed |
| C-4 (no local OCR) | `TECH_DEBT.md:250-253` | Resolved — tesseract OCR fallback | 🟢 Completed |
| R-3 (web result citation validation) | `TECH_DEBT.md:221-224` | Already deferred | ⚪ Pending |
| E-6 (budget alerts) | `TECH_DEBT.md:211-214` | M25 scope | 🟢 Completed |
| E-5 (dashboard cost charts) | `TECH_DEBT.md:216-219` | Already deferred | ⚪ Pending |
| G-5 (no JSON schema validation) | `TECH_DEBT.md:228-231` | Already deferred | ⚪ Pending |
| E-3 (no extraction streaming) | `TECH_DEBT.md:243-246` | Already deferred | ⚪ Pending |
| R-8 (no Anthropic vision in worker) | `TECH_DEBT.md:260-263` | Already deferred | ⚪ Pending |
| R-8 (worker vision not tenant-aware) | `TECH_DEBT.md:265-268` | Already deferred | ⚪ Pending |
| P-5 (per-tenant web search keys) | `TECH_DEBT.md:201-204` | Already deferred | ⚪ Pending |
| P-5 (Brave Search adapter) | `TECH_DEBT.md:196-199` | Already deferred | ⚪ Pending |
| E-2 (per-message token_count) | `TECH_DEBT.md:191-194` | Already deferred | ⚪ Pending |
| C-4 (embedding/chunking web results) | `TECH_DEBT.md:206-209` | Already deferred | ⚪ Pending |
| E-7 (Anthropic JSON mode) | `TECH_DEBT.md:238-241` | Already deferred | ⚪ Pending |

### Not Yet Tracked — Should Be Added

These are new findings not present in `TECH_DEBT.md`, `ROADMAP.md`, or `PROJECT_STATUS.md`:

| ID | Finding | Suggested Location | Status |
|----|---------|-------------------|--------|
| C-1 | Semantic chunker naive sentence split | `TECH_DEBT.md` | 🟢 Completed |
| C-2 | Semantic chunker double-trigger bug | `TECH_DEBT.md` | 🟢 Completed |
| C-3 | No hierarchical chunking | `TECH_DEBT.md` | 🟢 Completed |
| C-5 | No table extraction | `TECH_DEBT.md` | 🟢 Completed |
| C-6 | Recursive chunker overlap walks backward | `TECH_DEBT.md` | 🟢 Completed |
| R-1 | `plainto_tsquery` without operators | `TECH_DEBT.md` | 🟢 Completed |
| R-2 | No BM25 | `TECH_DEBT.md` | 🟢 Completed |
| R-3 | Reranker candidate pool too narrow | `TECH_DEBT.md` | 🟢 Completed |
| R-4 | No query expansion | This report only | 🟢 Completed |
| R-5 | No MMR diversity | `TECH_DEBT.md` | 🟢 Completed |
| R-6 | Self-query same model as generation | `TECH_DEBT.md` | 🟢 Completed |
| R-7 | Self-query disabled by default | Fix immediately | 🟢 Completed |
| R-8 | Semantic cache no invalidation | `TECH_DEBT.md` | 🟢 Completed |
| R-9 | Web search disabled by default | Fix immediately | 🟢 Completed |
| G-1 | `len//4` token estimation | Fix immediately | 🟢 Completed |
| G-2 | No lost-in-middle mitigation | Fix immediately | 🟢 Completed |
| G-3 | Passive citation validation | `TECH_DEBT.md` | 🟢 Completed |
| G-4 | Flat context block | `TECH_DEBT.md` | 🟢 Completed |
| G-5 | No structured output in orchestrator | `TECH_DEBT.md` | 🟢 Completed |
| P-1 | No query rewriting | This report only | 🟢 Completed |
| P-2 | No Self-RAG | This report only | 🟢 Completed |
| P-3 | No adaptive retrieval | `ROADMAP.md` (future milestone) | 🟢 Completed |
| P-4 | No query routing | `ROADMAP.md` (future milestone) | 🟢 Completed |
| P-5 | Self-query serial latency | `TECH_DEBT.md` | 🟢 Completed |
| E-1 | No RAG evaluation framework | This report only | 🟢 Completed |
| E-2 | No search quality metrics | This report only | 🟢 Completed |
| E-3 | Binary feedback only | `TECH_DEBT.md` | 🟢 Completed |
| E-4 | No ground-truth test set | This report only | 🟢 Completed |
| E-5 | No A/B testing | `ROADMAP.md` M28 (planned full platform) | 🟢 Completed (minimal) |
| E-6 | No budget alerts | Already in `TECH_DEBT.md` | 🟢 Completed |
| E-7 | `warm_caches` no-op | Fix immediately | 🟢 Completed |
