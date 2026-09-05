# Product Roadmap (Retriever Backend)

> 📌 **Master Cross-Platform Roadmap (SSoT):** For the unified sequential timeline (M1 to M102) connecting `retriever` and the `prateeq.in` control plane, see: [`Prateek_website/docs/UNIFIED_MASTER_ROADMAP.md`](../Prateek_website/docs/UNIFIED_MASTER_ROADMAP.md).
> 
> This document tracks the backend and unified cross-platform engineering milestones (M1–M102) for the Retriever AI engine and control plane.

---

## Roadmap Overview

| Milestone | Title | Focus Area | Status |
|---|---|---|---|
| **M1** | Repository Foundation | Directory layout, configurations, CI/CD, linting, Docker environment | **Completed** |
| **M2** | Authentication & Tenant Foundation | Identity interfaces, relational schemas, Postgres RLS contexts, API keys, cache | **Completed** |
| **M3** | Configuration & Platform Infrastructure | Global/Tenant configurations, database JSONB overrides, environment fallbacks | **Completed** |
| **M4** | Document Ingestion & Storage | Parsing tasks, unstructured layouts, chunking, event broker lifecycle | **Completed** |
| **M5** | Retrieval, Fusion & Rerank | pgvector indexes, hybrid search, Reciprocal Rank Fusion, Cohere reranking | **Completed** |
| **M6** | Generative Inference & Citations | LLM adapters, prompt orchestrations, context window packing, citation audits | **Completed** |
| **M7** | Observability & Hardening | Structured logging, Prometheus metrics, OTel tracing, rate limiting | **Completed** |
| **M8** | Production Hardening | DB bootstrap fixes, worker consolidation, shared packages, architecture tests | **Completed** |
| **M9** | Client Hierarchy & Admin API | Users table, sub-client RLS, per-tenant LLM keys, admin API scoping, CRUD endpoints | **Completed** |
| **M10** | Admin Dashboard | Next.js admin UI for platform management (tenants, users, configs, onboarding, playground) | *Completed* |
| **M11** | Client SDK & API Surface | JS/TS RetrieverClient, OpenAPI 3.1 spec, pagination, rate limit headers | **Completed** |
| **M12** | Production Storage | S3/MinIO adapter, encrypted key persistence, connection pool tuning | **Completed** |
| **M13** | Multi-Industry Configurability | Per-tenant chunking, metadata extractors, guardrails, citation formatting | **Completed** |
| **M14** | Performance & Scale | HNSW tuning, semantic cache, bulk ingest, SSE lifecycle, memory profiling | **Completed** |
| **M15** | Enterprise Readiness | Audit log writer, SSO/OIDC, RBAC, data retention, backup/restore, compliance | **Completed** |
| **M16** | User Feedback & Quality Loops | Thumbs up/down endpoints, rating logs, admin dashboard analytics | **Completed** |
| **M17** | Secure Document Distribution | Client-scoped document download links, temporary presigned R2/S3 URLs | **Completed** |
| **M18** | Metadata & Tag Filtering | Tag/Collection-based search filtering, advanced boolean queries | **Completed** |
| **M19** | Smart Model Failover | Auto-retry on provider downtime, multi-LLM dynamic translation routing | **Completed** |
| **M20** | Token Cost Optimization | Long chat history summarization compression, token billing tracking | **Completed** |
| **M21** | Web Search Grounding | Tavily/Brave Search fallback APIs, dynamic internet context injections | **Completed** |
| **M22** | Structured Data Extraction | JSON Schema-based document parsing endpoints, structured LLM outputs | **Completed** |
| **M23** | Multi-Modal Processing | Image & scanned PDF OCR pipelines, vision-model page descriptors | **Completed** |
| **M24** | Self-Querying Retrieval | Natural language query translation, SQL metadata filter compilers | **Completed** |
| **M25** | Developer Console & Local Ingestion | Next.js Developer Console, local Ollama RAG ingestion, RLS verification | **Completed** |
| **M26** | SaaS Tenant Resource Quotas | Hard/soft limits on files, storage, and tokens, 402/429 status hooks | **Completed** |
| **M27** | Multi-Workspace Collections | Tenant sub-partitioning, workspace-scoped vector and GIN queries | **Completed** |
| **M28** | Interactive Chunking Auditor | Sandbox chunk-preview APIs, visual text highlight chunk dividers | **Completed** |
| **M29** | A/B Testing Platform | Create/start/stop experiments via admin API, per-variant metrics dashboard | **Completed** |
| **M30** | Production Polish | Deployment hardening, observability, CI/CD, secrets management, docs alignment | **Completed** |
| **M31** | Security Hardening & Secrets Remediation | Credential rotation, fail-safe defaults, proxy validation, port hardening | *Completed* |
| **M32** | Onboarding & Client UX Overhaul | User creation in wizard, fixed form defaults, short IDs, admin UX polish | *Completed* |
| **M33** | Code Quality & Architecture | Split main.py, shared TypeScript types, consolidate constants, clean up clients | *Completed* |
| **M34** | Production Operations & DevOps | Auto-deploy pipeline, Sentry, uptime monitoring, pagination | *Completed* |
| **M35** | Final Polish & Infrastructure Self-Detection | Server-spec auto-detection, model updates, docker infrastructure removal | *Completed* |
| **M36** | SaaS Data Connectors Framework | WebCrawler + cloud-drive connectors, admin CRUD, sync ingestion | **Completed** |
| **M37** | GraphRAG & Knowledge Graph Indexing | Entity-relationship graph extraction and hybrid graph+vector reasoning | **Completed** |
| **M38** | Critical Security Remediation | Google OAuth verification, JWT secret, SQL-injection-safe filters, file-serve traversal & HMAC hardening, upload caps, RLS coverage, error redaction | **Completed** (v0.36.0) |
| **M39** | Production Multi-Tenant Identity & Workspace Portal | Supabase Auth OIDC/JWKS resource server integration, auto-tenant provisioning, GET /v1/auth/session, and aligning with `prateeq.in` control plane | **Completed** |
| **M40** | Active Real-Time LLM Safety Guardrails | Llama Guard 3 taxonomy, pre-execution prompt injection blocks, post-execution output PII redactor | **Completed** |
| **M41** | Chunk-Level Granular Access Control (ACL) | Add allowed_roles/allowed_users to chunk metadata & enforce DB engine RLS | **Completed** (v0.39.0) |
| **M42** | Layout-Aware Vision OCR & Table Parsing | Replace PyPDF2 with Docling/Unstructured layout-aware OCR for scanned PDFs & tables | **Completed** (v0.40.0) |
| **M43** | Dynamic Multi-Embedding Vector Schemas | Dynamic vector table partitioning for variable model dimensions (768, 1536, 3072) | **Completed** (v0.41.0) |
| **M44** | GraphRAG Productionization & Retrieval Integration | Neo4j driver dependency + connectivity, graph-evidence wiring into search/chat, fix verified M37 defects | **Completed** (v0.42.0) |
| **M45** | Learned Sparse (SPLADE) & Reranker Microservice | Upgrade sparse search to SPLADE / Qdrant and offload Cross-Encoder to GPU worker | **Completed** (v0.43.0) |
| **M46** | Agentic Workflow Execution Engine | Autonomous multi-step tool calling and agent execution loops | **Completed** (v0.44.0) |
| **M47** | Recursive Language Model (RLM) Engine & REPL Sandbox | Python REPL execution sandbox, active programmatic document traversal, and recursive subroutines | **Completed** (v0.45.0) |
| **M48** | Multi-Agent Consensus & Critic Reflection | Generator vs. Critic multi-agent reflection loops for high-stakes enterprise verification | **Completed** (v0.46.0) |
| **M49** | Context Compression & Zero-Trust Encryption | Implement LongLLMLingua chunk compression and envelope encryption for vector/text storage | **Completed** (v0.47.0) |
| **M50** | Online Production Hallucination Tracing | Continuous real-time faithfulness & context relevance scoring on live API streams | **Completed** (v0.48.0) |
| **M51** | Compliance & Data Sovereignty Lifecycle | Automated GDPR vector purge, data retention schedulers, and zero-footprint PII redaction | **Completed** (v0.49.0) |
| **M52** | Commercial SaaS Quota Sync & Webhook Provisioning | Receive Razorpay/Stripe webhooks from `prateeq.in`, sync tenant quotas (`M26`), and track usage balance | **Completed** (v0.50.0) |
| **M53** | Enterprise n8n & Workflow Automation Integration | Self-hosted n8n automation connectors, inbound document auto-ingest webhooks (Gmail/GDrive/Notion), outbound event triggers (Slack/WhatsApp/Zendesk), and community node integration | **Completed** (v0.51.0) |
| **M54** | Enforced Parent-Child Hydration & Exact Citation Grounding | Small-chunk precision search with parent-chunk context expansion & exact string-span citation verification | **Completed** (v0.52.0) |
| **M55** | Embeddable Chat Widget & Public JavaScript Client | Zero-dependency standalone `widget.js` bundle & `@prat3010/retriever-client-js` streaming client | **Completed** (v0.53.0) |
| **M58.5**| Retriever Grounded Outbound (`prateeq_outreach`) | Dedicated tenant for Synchronizer pitch generation, portfolio vector indexing & evidence inspector | **Planned (Phase E)** |
| **M62.5**| Operational Hardening & Cross-Repo Security Baseline | Secrets rotation, git purge, CORS restriction, exception handler fix, bare except logging, CI gates & dual-DB API protocol | **Completed** |
| **M63** | Multimodal Discovery & Dogfooding Tenant (`prateeq_scoping`) | Onboard authentic dogfooding tenant with rate cards & embed widget chatbox | **Completed** (Phase G) |
| **M64** | Productized Architecture Cart Drawer & GraphRAG Upsells | Slide-over cart drawer, volume bundle discounts & Python REPL CPQ pricing | **Completed** (Phase G) |
| **M65** | Live Visual Architecture Topology Map & Cascade Solver | Dynamic SVG node graph visualizer & interactive dependency cascade disconnect modal | **Completed** (Phase G) |
| **M66** | Terminal Scoping CLI (`/terminal`) & Mobile QR Checkout | CLI scoping commands in `/terminal` & mobile ASCII QR code checkout | **Completed** (Phase G) |
| **M68** | Unified Persistent Copilot (Retriever RAG Stream) & Sprint Feeds | Connect dashboard copilot to private tenant session & live commit feed | **Completed** (Phase G) |
| **M69** | Pre-Chunk Contextual Retrieval Ingestion Engine | Prepend 50-word document context headers to chunks prior to vector embedding (Anthropic method) | **Completed** (Phase H) |
| **M70** | Late-Interaction (ColBERT) Token-Level Reranker | Implement token-level late interaction reranking adapter for high-precision code & technical term search | **Completed** (Phase H) |
| **M71** | Corrective RAG (CRAG) & Agentic Reflection Loop | Autonomous reflection loop evaluating retrieval confidence and triggering web search fallback | **Completed** (Phase H) |
| **M72** | Interactive RLM Python REPL Sandbox Studio | Productize `/v1/rlm` into a dedicated Client SaaS Studio workspace for programmatic document vault traversal | **Completed** (Phase H) |
| **M73** | GraphRAG Leiden Community Detection & Self-Tuning RAG | Hierarchical community entity summaries & automated pipeline tuning based on M50 evaluation telemetry | **Completed** (Phase H) |
| **M74** | Semantic NLI & SLM Online Hallucination Engine | Replace keyword matching with DeBERTa Cross-Encoder / Ollama SLM judge in Celery worker | **Completed** (Phase I) |
| **M75** | Full-Stack OpenTelemetry Auto-Instrumentation | Auto-instrument SQLAlchemy, HTTPX, Celery and propagate W3C traceparent headers | **Completed** (Phase I) |
| **M76** | Real-Time Telemetry & SLA Webhook Alerting Engine | Live SQL/Redis telemetry queries and proactive Slack/Discord/Webhook alert dispatcher | **Completed** (Phase I) |
| **M77** | Synthetic Golden Dataset Generation & CI/CD Gate | Auto-generate benchmark Q&A pairs from documents and enforce GitHub Actions regression gate | **Completed** (Phase I) |
| **M78** | Visual Grounding Diff & Retriever Admin Observability | Claim-by-claim visual grounding highlighter and dedicated Retriever Admin observability cockpit | **Completed** (Phase I) |
| **M79** | Sparse-Dense Hybrid Search & Contrastive LoRA Adapters | Domain-aware Sublinear BM25 vectorizer + Contrastive LoRA residual embedding calibration | **Completed** (Phase J) |
| **M80** | PyTorch ColBERT Late-Interaction MaxSim Engine | Token-level multi-vector representations + Apple Silicon MPS/CUDA MaxSim reranker | **Completed** (Phase J) |
| **M81** | Scikit-Learn Unsupervised Chunk Clustering & HDBSCAN | Dynamic topic modeling & hierarchical community synthesis for GraphRAG knowledge graphs | **Completed** (Phase J / v0.66.0) |
| **M82** | Scikit-Learn 2D/3D Embedding Space Projection Pipeline | PCA/UMAP projection service & Three.js interactive 3D vector space visualizer in SaaS Studio | **Completed** (Phase J / v0.67.0) |
| **M83** | Scikit-Learn Real-Time Telemetry Anomaly Detection | Isolation Forest anomaly sentinel on inference logs for anti-abuse & quota protection | **Completed** (Phase J / v0.68.0) |
| **M84** | Scikit-Learn ML Project Effort & Timeline Estimator | Multi-Output Gradient Boosting Regressor for CPQ scoping effort & sprint timeline confidence bounds | **Completed** (Phase J / v0.69.0) |
| **M85** | Scikit-Learn & PyTorch Visitor Persona & Lead Classifier | Zero-cookie telemetry clustering & autonomous outreach lead conversion propensity scorer | **Completed** (Phase J / v0.70.0) |
| **M85.1–M85.4**| Forensic Audit Remediation (Blueprint-to-Reality Parity) | LlamaGuard 3 structured safety, LongLLMLingua entropy scoring, Dashboard live wire | **Completed** (Phase J.5) |
| **M85.5–M85.6**| Security Hardening & Production Logging | Secret rotation, KEK validation, structured exception handling across 50+ files | **Completed** (Phase J.6) |
| **M85.7**| Safe Deployment Pipeline (Blue/Green with Rollback & Health Gates) | Release directory versioning (`/opt/retriever/releases`), atomic symlinks, and automatic rollback on health failure | **Completed** (Phase J.6 / DevOps) |
| **M85.8**| CI/CD Security Gate Enforcement & Full Test Coverage | Fail-blocking CodeQL & Trivy vulnerability scans with all continue-on-error flags removed | **Completed** (Phase J.6 / Security CI) |
| **M85.9**| Dashboard God Component Decomposition & Zod Validation | Decomposed dashboard into 10 modular widgets with runtime Zod request validation | **Completed** (Phase J.6 / Frontend) |
| **M85.10**| Multi-Tenant Locust Load Testing & Benchmark Reporting | Multi-tenant Locust concurrent load testing suite and automated latency & throughput report generator | **Completed** (Phase J.6 / Benchmarks) |
| **M85.11**| parse-intent Real-Retriever Structured Classification | Replace `if/else` keyword classifier in `Prateek_website` scoping with authentic Retriever chat/orchestrator structured JSON classification (archetype, features, confidence, telemetry); remove fabricated latency/model; keep labeled fallback | **Completed** (Phase J.7) |
| **M85.12**| AiScopingPromptBar AI-Theater Removal & Honest Telemetry | Remove fake default telemetry + stale "primed for prateeq-scoping-live" badge + simulated 3-step `setTimeout` progress; show real backend telemetry only | **Completed** (Phase J.7) |
| **M85.13**| Scoping PRD & Audit Docs Reconciliation | Reconcile `SCOPING_AUDIT_ROADMAP.md` §5.1 / SOTA PRD "powered by gemini-3.6-flash" claims with the real Retriever implementation | **Completed** (Phase J.7) |
| **M85.14**| CI Test Execution Gate & Coverage (Frontend) | Add `npm test` + coverage + Playwright interaction job to `Prateek_website` CI (`db_sync.yml`); tests currently never run in CI | **Completed** (Phase J.7) |
| **M85.15**| Honest Communication Pass | Reword "256-bit Encrypted" badge, un-hide reCAPTCHA, correct stale hardcoded test counts in terminal copy | **Completed** (Phase J.7) |
| **M85.16**| FDE Career Artifacts & Persona Roadmap | Rewrite `retriever/README.md` for technical interviewers; publish 2–3 case-study writeups (webhook HMAC/idempotency, GST, RLS, ColBERT/LoRA); align `21_Future_Roadmap` personae | **Completed** (Phase J.7) |
| **M86** | Edge AI Token Shield, DDoS Defense & Upstash Rate Limiting | Sliding-window token limiter & resilient SSE connection recovery protocol | **Completed** (Phase K) |
| **M86.5** | Platform Capabilities & Active Batteries Observability Cockpit | 15 platform batteries inventory and live telemetry command center | **Completed** (Phase K) |
| **M87** | Automated Cloud Database Snapshots & PITR Recovery Engine | Encrypted daily pg_dump to Cloudflare R2 / S3 with Point-in-Time Recovery | **Completed** (v0.72.0) |
| **M88** | Enterprise Compliance Vault: Presidio PII & GDPR Wipe | Microsoft Presidio PII entity redaction & cryptographic deletion certificate PDF | **Completed** (v0.73.0) |
| **M89** | Geo-Distributed Multi-Region Edge Vector Read-Replicas | Sub-30ms global edge read replicas with Geo-IP traffic routing | **Completed** (v0.74.0) |
| **M90** | Universal Ecosystem Plugins (Slack Bot, Chrome Ext, GDrive) | Native Slack workspace bot, 1-click Chrome ingestion & 2-way Google Drive sync | **Completed** (v0.75.0) |
| **M91** | LangGraph Cyclic Agentic Workflows & Multi-Agent HITL Engine | State-machine cognitive graphs, conditional routing, human-in-the-loop approvals, and checkpoint time-travel | **Completed** (v0.76.0) |
| **M92** | DSPy Declarative Prompt Compilation & Teleprompter | Metric-driven automated prompt & few-shot optimization pipeline | **Completed** (v0.77.0) |
| **M93** | Enterprise LLM Gateway & Multi-Model Smart Router | LiteLLM gateway, dynamic model failover, cost & quota management | **Completed** (v0.78.0) |
| **M94** | NVIDIA NeMo Guardrails & Conversational Safety Rails | Colang conversational safety rails, factual topic grounding & scope enforcement | **Completed** (v0.79.0) |
| **M95** | Durable Asynchronous Execution & AI Workflow Engine | Step-level memoization, resilient automatic retry backoff, and idempotent checkpoint state machines across distributed AI pipelines | **Completed** (v0.80.0) |
| **M96** | Serverless GPU Serving & Custom vLLM / LoRA Pipeline | Modal / BentoML serverless GPU auto-scaling down to zero & dynamic LoRA swapping | **Completed** (Phase L / v0.81.0) |
| **M97** | Autonomous FDE Metaprogrammer & Self-Extending Capability Studio | Natural language capability wizard, AST-verified Hexagonal code scaffolder & Platform Battery #17 | **Completed** (Phase L / v0.82.0) |
| **M98** | Sovereign Edge SQLite / Turso Vector Synchronization & Offline-First Edge Agent | Embedded SQLite 3 FTS5, binary float32 BLOB vectors, differential delta sync & Platform Battery #18 | **Completed** (Phase M / v0.83.0) |
| **M99** | Distributed Multi-Cloud Failover & Edge Turso LibSQL Replication | Active-active multi-cloud failover, LibSQL embedded replicas, quorum consensus & Platform Battery #19 | **Completed** (Phase M / v0.84.0) |
| **M100** | Sovereign Edge Voice & Local Whisper / WebRTC Speech Synthesis | Full-duplex WebRTC, local Whisper ASR, RMS/ZCR VAD endpointing, streaming neural TTS & Platform Battery #20 | **Completed** (Phase M / v0.85.0) |

> 📌 **Dashboard Architecture & Strategic 2026 RAG Roadmaps:**  
> - For the Master 2026 RAG Engine Architecture Blueprint, see **[RAG 2026 Product & Architecture Roadmap](docs/RAG_2026_PRODUCT_ROADMAP.md)**.
> - For the Platform Admin Control Panel (`apps/web`), see **[Admin Dashboard Architecture & Operational Roadmap](docs/ADMIN_DASHBOARD_ROADMAP.md)**.  
> - For the Client Portal & SaaS Studio (`prateeq.in/dashboard` & `prateeq.in/rag/app`), see **[Client Dashboard Ecosystem Roadmap](../Prateek_website/docs/CLIENT_DASHBOARD_ROADMAP.md)**.
> - For the Master Unified Cross-Platform Roadmap (M1–M102), see **[`Prateek_website/docs/UNIFIED_MASTER_ROADMAP.md`](../Prateek_website/docs/UNIFIED_MASTER_ROADMAP.md)**.
> - For the Active **Phase J.7** (M85.11–M85.16: Honest AI Wiring, Trust Hardening & FDE Hiring Credibility), see **[`Prateek_website/docs/UNIFIED_MASTER_ROADMAP.md` §Phase J.7](../Prateek_website/docs/UNIFIED_MASTER_ROADMAP.md)**.

---

## Detailed Milestone Targets

### [Completed] Milestone 1: Repository Foundation
- Establish workspace structure for FastAPI, Next.js, and background workers.
- Setup Ruff formatting and TypeScript linting boundaries.
- Automate checks with GitHub Actions.

### [Completed] Milestone 2: Authentication & Tenant Foundation
- Design abstract identity interfaces (ports) and database schemas.
- Implement thread-local transaction hooks setting PostgreSQL RLS variables.
- Hash client tokens using SHA-256 for secure API validations.
- Implement L1 caching via Redis with write-through logic.
- Configure Tenancy boundary breach checks (Revocation Kill-Switch).

### [Completed] Milestone 3: Configuration & Platform Infrastructure
- Create dynamic configuration domain entities (FeatureFlags, AI/Embedding/Storage Providers).
- Build the SQL config registry repository adapter supporting JSONB schema overrides and versioning.
- Implement ConfigurationService managing dynamic inheritance and environment falls.
- Added administrative API endpoints for configurations with credentials redaction.
- Applied Postgres RLS policies on configurations database tables.

### [Completed] Milestone 4: Document Ingestion & Storage
- Define unstructured layout parsing algorithms for PDF, Markdown, and text files.
- Implement token-aware sliding window chunkers inside background workers.
- Integrate event broker (RabbitMQ) handling document lifecycle events.
- Document upload, deduplication, listing, status, and deletion endpoints.

### [Completed] Milestone 5: Retrieval, Fusion & Rerank
- Configure pgvector extension indexes (HNSW) for semantic matching.
- Implement vector similarity query database repositories with metadata filtering.
- Implement Reciprocal Rank Fusion (RRF) logic merging semantic and keyword search hits.
- Integrate Cohere Reranking models for context refinement with graceful degradation.

### [Completed] Milestone 6: Generative Inference & Citations
- Implement LlmProvider port with OpenAI adapter (sync + streaming).
- Build PromptBuilder with template registry, context injection, and token budget compression.
- Implement CitationValidator for inline source chunk verification.
- Build InferenceOrchestrator coordinating history fetch, prompt compilation, LLM dispatch, citation validation, and telemetry logging.
- Chat session create/message endpoints with SSE streaming.

### [Completed] Milestone 7: Observability & Hardening
- Configure structured logging via structlog with OTel trace context injection.
- Implement Prometheus metrics registry (latency, tokens, queue backpressure, RLS violations).
- Implement OpenTelemetry tracer with OTLP export and FastAPI instrumentation.
- Implement Redis sliding-window rate limiter with FastAPI dependency integration.
- Telemetry middleware for request timing and structured access logs.
- `/metrics` endpoint for Prometheus scraping.

---

### [Completed] Milestone 8: Production Hardening

**Objective:** Close gaps that prevent the platform from running reliably outside development. Fix DB bootstrap crashes, consolidate worker architecture, share code properly between API and workers, and enforce architectural rules via conformance tests.

**Deliverables:**
- Celery adopted as the single worker framework; pika-based event consumer deprecated.
- Shared `processing-core` package extracted (PDF parser, chunker, embedding retry).
- CORS configurable via `CORS_ORIGINS` env var.
- Sentry integration in API lifespan + Celery worker.
- DB engine singleton lifted to injectable module-level engine (`get_engine()` / `set_engine()`).
- Architecture conformance tests: `tests/test_architecture.py` enforces hexagonal boundaries and no hardcoded prompts.
- All docs reconciled with codebase (architecture, system-design, playbook, constitution).
- Prompts fail loud with `PromptTemplateNotFoundError` instead of silent hardcoded fallback.
- 78/78 tests passing.

---

### [Completed] Milestone 9: Client Hierarchy & Admin API

**Objective:** Introduce the user/sub-client model, per-tenant LLM key management, admin API key scoping, and CRUD endpoints for platform management. This is the foundation for all downstream features.

**Prerequisites:** M8.

**Complexity:** Large

**Dependencies:** M8

**Expected Outcome:** Each client tenant can have multiple users with isolated chat data. Admin API keys can manage all tenants; client API keys are scoped to their tenant. Per-tenant LLM keys and model selection are configurable via admin API.

**Targets:**
- `users` table: `user_id`, `tenant_id`, `display_name`, `is_active`, `created_at`. RLS by `tenant_id`.
- `chat_sessions` + `chat_messages` gain `user_id` column with RLS filtering.
- Per-tenant LLM key storage: encrypted `llm_api_key` + `llm_model` fields on `TenantConfig`. Adapter resolves: request header > tenant config > env var fallback.
- API keys gain `scope` field: `admin` (full access across all tenants) vs `client` (scoped to one tenant). Multiple keys per tenant allowed (named, revocable).
- Admin CRUD endpoints: list/search tenants, create/suspend tenant, list users per tenant, list documents per tenant, create/edit prompt templates per tenant, get/set tenant config (LLM key, model, chunk params).
- `X-User-ID` header support: middleware extracts from request, sets RLS context variable `app.current_user_id`. Admin keys bypass user filter.
- Sub-client data isolation verified: a user within a tenant cannot see another user's chat history.

**Acceptance Criteria:**
- Creating a tenant + generating an API key can be done entirely through the API (no DB access needed).
- Two users in the same tenant produce isolated chat sessions with no data bleed.
- Admin API key can view all tenants; client API key is limited to its own tenant.
- Setting a per-tenant LLM key via admin API causes subsequent queries to use that key instead of the env var.

---

### [Completed] Milestone 10: Admin Dashboard

**Objective:** Build a Next.js admin UI that consumes the M9 admin API. One place to manage everything — no SQL, no terminal.

**Prerequisites:** M9.

**Complexity:** Large

**Dependencies:** M9

**Deliverables:**
- ✅ Next.js 14 scaffold: shadcn/ui + Tailwind v4, TanStack Query, Zustand, sonner toasts, next-themes
- ✅ Auth: admin master key login, sessionStorage + cookie, middleware guard
- ✅ App shell: sidebar, topbar (action slots), ErrorBoundary wrapper, theme toggle
- ✅ Domain hooks: tenants (paginated), users, API keys, config, documents, prompts (CRUD + preview)
- ✅ 9 routes: `/` dashboard, `/login`, `/onboard`, `/tenants` (search + pagination), `/tenants/[id]` (7 tabs), `/tenants/[id]/playground`, `/settings`, `/audit-log`
- ✅ Tenant detail tabs: Overview, Documents, Users, API Keys, Prompts (create/edit/delete + preview), Sandbox (RAG chat via SSE), Config
- ✅ Global config page: AI provider, embedding, retrieval, rate limits
- ✅ Audit log viewer: filterable by tenant ID and action type
- ✅ Client onboarding wizard: 3-step flow with curl examples
- ✅ API Playground: per-tenant endpoint test console
- ✅ Reference client (`apps/client-reference/`): `RetrieverClient` JS class, Chat/SSE/Search/Documents tabs
- ✅ Alert dialog confirmations for destructive actions
- ✅ Backend: admin documents list, prompts CRUD + preview, paginated tenants, audit log repository + write hooks + list endpoint
- ✅ `bypass_rls` consistency: `PromptTemplateRegistry` methods accept `bypass_rls` parameter; admin endpoints pass `True`
- ✅ `httpx` → `httpx2` migration (Starlette deprecation fix)
- ✅ 111 tests (94 → 111, +17 new admin API tests), Ruff clean, web build clean
- ✅ `docs/features/admin-dashboard.md` — full agent guide
- ✅ `DocumentRepository` port extracted (`domain/abstractions/ingestion.py` + `adapters/database/document_repository.py`), 5 inline SQLAlchemy blocks removed from `main.py`
- ✅ All M10 items complete — milestone ready for deploy

---

### [Completed] Milestone 11: Client SDK & API Surface

**Objective:** Provide a lightweight JS/TS `RetrieverClient` so frontend developers integrate in one line of config. Standardize API surface conventions.

**Prerequisites:** M9 (stable admin API, user model).

**Complexity:** Medium

**Dependencies:** M9

**Expected Outcome:** A frontend developer adds `new RetrieverClient({ apiKey, baseUrl })` and starts making RAG queries. All list endpoints support cursor-based pagination. Rate limit headers are standardized.

**Targets:**
- ✅ TypeScript SDK (`packages/retriever-client-js/`): typed fetch-based client. Methods for chat, document upload, search.
- ✅ SDK handles `X-API-Key` and `X-User-ID` headers automatically.
- ✅ Auto-generate OpenAPI 3.1 spec from FastAPI routes.
- ✅ Implement cursor-based pagination on document list, message history, tenant list (admin).
- ✅ Standardize rate limit response headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`).
- ✅ Add `Idempotency-Key` support on document upload endpoints.
- ✅ Quickstart guide: "Add Retriever to any frontend in 5 minutes."
- ✅ Integration test using the SDK against live API (verified passing).

**Acceptance Criteria:**
- ✅ SDK can execute every documented API operation.
- ✅ All list endpoints return `pagination` block with `nextCursor`, `limit`, `hasMore`.
- ✅ Integration test passes in CI.

---

### [Completed] Milestone 12: Production Storage

**Objective:** Replace local filesystem storage with S3/MinIO. Encrypt persisted LLM keys. Tune connection pools for production traffic.

**Prerequisites:** M9 (per-tenant config foundation).

**Complexity:** Medium

**Dependencies:** M9

**Expected Outcome:** All document storage goes through S3/MinIO with tenant-prefixed buckets. LLM keys are encrypted at rest. Connection pooling is auto-tuned.

**Targets:**
- ✅ S3/MinIO adapter: implements `DocumentStorage` port. Tenant-prefixed bucket paths (`/{tenant_id}/documents/{doc_id}.pdf`).
- ✅ Encrypted tenant config fields: `llm_api_key` stored encrypted (AES-256-GCM) with a `key_encryption_key` env var.
- ✅ Migration path: existing local files stay accessible while new uploads go to S3.
- ✅ Connection pool sizing: benchmark and set optimal `pool_size`, `max_overflow`, `pool_timeout` for asyncpg.
- ✅ Storage health check: verify S3/MinIO reachability in `/health` endpoint.
- ✅ Document download/presigned URL endpoint for admin dashboard.

**Acceptance Criteria:**
- ✅ Uploaded documents are readable from S3/MinIO, isolated by tenant prefix.
- ✅ Encrypted LLM key in DB is decryptable only with the server-side KEK; a DB dump alone yields ciphertext.
- ✅ Connection pool does not exhaust under concurrent load.

---

### [Completed] Milestone 13: Multi-Industry Configurability

**Objective:** Enable different clients (coaching, legal, CA) to run with different chunking, metadata, guardrails, and citation formats — all configured at runtime, no code changes.

**Prerequisites:** M3 (CAD system), M9 (per-tenant config).

**Complexity:** Extra Large

**Dependencies:** M9

**Expected Outcome:** A legal tenant and a coaching tenant can use the same Retriever instance with completely different chunk granularity, metadata schemas, and prompt guardrails.

**Targets:**
- ✅ Pluggable chunking strategies per tenant (semantic splitting, recursive character, fixed-token sliding window).
- ✅ Pluggable metadata extractors per document type (extract dates, case numbers, contract clauses).
- ✅ Pluggable input/output guardrails per tenant (PII redaction, prompt injection detection, output content filtering).
- ✅ Industry template packs: pre-built configuration bundles for legal, medical, finance, HR, education. Config only — no code changes.
- ✅ Citation format customization per tenant (e.g., `[Source: doc_id, page N]` vs `(see exhibit A)`).
- ✅ Per-tenant model routing: different LLM for different query intents (summarization vs analysis vs extraction).
- ✅ Document type detection and routing to appropriate parser (PDF, DOCX, HTML, Markdown, code).

**Acceptance Criteria:**
- ✅ Two tenants with different industry profiles produce different chunk granularity for the same document.
- ✅ A new document type is supported by adding a config entry and a parser adapter — no domain code changes.
- ✅ Guardrail violations are logged per tenant and can trigger different actions (block, warn, redact).

---

### [Completed] Milestone 14: Performance & Scale

**Objective:** Optimize for production traffic. Measure, find bottlenecks, fix them, verify with benchmarks.

**Prerequisites:** M11 (stable API surface), M12 (production storage).

**Complexity:** Large

**Dependencies:** M11, M12

**Expected Outcome:** The platform handles 200 concurrent search requests under 150ms latency budget.

**Targets:**
- ✅ HNSW index tuning: benchmark `m` and `ef_construction` parameters for optimal recall/latency tradeoff.
- ✅ Semantic query result cache: cache vector search results for semantically identical queries (cosine similarity > 0.99).
- ✅ Connection pool sizing benchmarks and auto-tuning.
- ✅ Chunk-level batch operations for bulk document ingest (reduce per-chunk transaction overhead).
- ✅ SSE connection lifecycle management: handle client disconnect cleanup, backpressure on slow consumers.
- ✅ Memory profiling under concurrent load: identify leaks in streaming responses, connection pools, async task accumulation.
- ✅ Cold-start optimization: lazy adapter initialization, connection pooling warmup on boot.
- ✅ Token budget compression benchmarks: measure latency savings vs quality impact of aggressive compression.

**Acceptance Criteria:**
- ✅ k6 benchmark: p95 latency < 150ms for search at 200 concurrent connections.
- ✅ SSE streaming starts first token within 500ms (per latency budget).
- ✅ Bulk ingest of 1000 documents completes without OOM or connection pool exhaustion.

---

### [Completed] Milestone 15: Enterprise Readiness

**Objective:** Meet enterprise compliance, security, and operational requirements. SOC 2 alignment, SSO, RBAC expansion, data lifecycle management.

**Prerequisites:** M9-M14.

**Complexity:** Extra Large

**Dependencies:** M9, M11, M12, M13, M14

**Expected Outcome:** The platform can be deployed in regulated environments with documented compliance posture.

**Targets:**
- ✅ SSO/OIDC integration: support external identity providers for admin dashboard login.
- ✅ Role-based access expansion: read-only API keys, scope granularity (per-document-type, per-collection).
- ✅ Data retention policies per tenant: auto-expire documents, sessions, inference logs based on configurable TTL.
- ✅ Backup/restore procedures documented and tested: PostgreSQL dump/restore, Redis RDB snapshots, vector index rebuild from chunks.
- ✅ Immutable audit trail: audit logs are append-only with cryptographic chain (hash-linked entries).
- ✅ Encryption at rest verification: document storage encryption, database encryption.
- ✅ Rate limit enforcement at tenant level (not just global).

**Acceptance Criteria:**
- ✅ SOC 2 evidence package can be generated from audit logs and deployment documentation.
- ✅ SSO integration with at least one provider (Okta, Auth0, or Azure AD).
- ✅ Backup/restore drill completes with zero data loss.
- ✅ Data retention enforcement verified: expired documents are auto-deleted.

---

### [Completed] Milestone 16: User Feedback & Quality Loops

**Objective:** Capture and analyze end-user feedback on RAG replies directly in production, enabling quality analytics inside the Admin Dashboard.

**Complexity:** Medium

**Dependencies:** M9, M10, M11

**Targets:**
- Create `FeedbackDb` relational schema scoped by tenant and linked to `chat_messages`.
- Implement client-scoped feedback submission endpoint: `POST /v1/tenants/{tenantId}/chat/sessions/{sessionId}/messages/{messageId}/feedback`.
- Add feedback statistics (thumbs up/down ratio, common negative flags) and custom text comments search tool inside the Admin Dashboard.

**Acceptance Criteria:**
- Feedback submission validates the message exists and belongs to the active tenant/user.
- Dashboard renders real-time quality curves based on logged ratings.

---

### [Completed] Milestone 17: Secure Document Distribution

**Objective:** Safely serve source document downloads to authenticated mobile and web users using secure, temporary links, resolving citation file clicks.

**Complexity:** Medium

**Dependencies:** M12, M15

**Targets:**
- Implement client-scoped file access validation endpoint: `GET /v1/tenants/{tenantId}/documents/{documentId}/download-url`.
- Implement `S3Storage.generate_presigned_url` method returning temporary access tokens (e.g. 5-minute expiry).
- S3-compatible presigned URLs (covers AWS S3 / MinIO / Cloudflare R2) for expiring downloads.

**Acceptance Criteria:**
- Requesting download URLs without valid user JWT fails with 401.
- Generated URLs expire and refuse access immediately after configured timeout (e.g., 5 mins).

---

### [Completed] Milestone 18: Metadata & Tag Filtering

**Objective:** Enable users to restrict search and chat queries to specific document tags, collections, or custom fields.

**Complexity:** Medium

**Dependencies:** M11, M13

**Targets:**
- ✅ Typed `MetadataFilter` Pydantic model with 10 operators (`eq`, `neq`, `in`, `gt`, `gte`, `lt`, `lte`, `exists`, `contains`, `regex`).
- ✅ `tags: list[str]` field on documents — new `TEXT[]` column + GIN index.
- ✅ Document-level tag filtering via `JOIN documents ... d.tags @> ARRAY[:tags]` in both vector and keyword search legs.
- ✅ Chunk-level metadata filtering with rich operators (`->>` for scalar, `?|` for array, `@>` for containment, `~*` for regex, `?` for key-existence).
- ✅ Shared `build_filter_clause()` in `adapters/vector/filter_builder.py` — deduplicated from two copies to one.
- ✅ GIN index `ix_document_chunks_meta_data` on `meta_data` JSONB column for index-scan performance.
- ✅ Filters and tags wired into both `SearchRequest` (`POST /v1/tenants/{tenantId}/search`) and `ChatMessageRequest` (`POST .../chat/sessions/{sessionId}/messages`).
- ✅ TypeScript SDK updated: `MetadataFilter` type + `filters`/`tags` params on `search()`, `chat()`, `chatStream()`.
- ✅ Alembic migration `4a2b3c5d6e7f` for `documents.tags` column + both GIN indexes.
- ✅ 18 new tests covering all filter operators, tag filtering, combined filters, and domain model defaults.
- ✅ 173/173 tests passing (was 155).

**Acceptance Criteria:**
- ✅ Querying with `tags: ["financial_statements"]` returns only chunks belonging to matching documents (verified by test).
- ✅ Search queries with metadata filters maintain p95 latency < 150ms (GIN index covers JSONB operators).

---

### [Completed] Milestone 19: Smart Model Failover

**Objective:** Build high availability into the inference engine to dynamically recover from third-party LLM outages without client downtime.

**Complexity:** Medium

**Dependencies:** M6, M13

**Deliverables:**
- ✅ `ProviderUnavailableError` exception — adapters catch retryable SDK errors (timeout, connection, 5xx, rate limit) and raise this.
- ✅ `fallback_provider`, `fallback_model`, `retry_attempts`, `retry_delay_ms` on `AIProviderConfig`.
- ✅ `InferenceLog.notes` field for telemetry.
- ✅ OpenAI adapter: catches `InternalServerError`, `APITimeoutError`, `APIConnectionError`, `RateLimitError` → `ProviderUnavailableError`. Auth errors (401) propagate correctly.
- ✅ Anthropic adapter: same pattern with `InternalServerError`, `OverloadedError`, `APITimeoutError`, `APIConnectionError`, `RateLimitError`.
- ✅ `RoutingLLMProvider` retries primary with exponential backoff, then falls back to secondary provider. Injects `_actual_provider` in config dict + info events in stream.
- ✅ `InferenceOrchestrator` reads `_actual_provider` → logs in `notes`.
- ✅ 16 tests covering retry, fallback, all-providers-down, non-retryable passthrough, streaming failover, adapter error wrapping.

**Acceptance Criteria:**
- ✅ Primary provider timeout triggers retry (2 attempts with backoff), then fallback to secondary provider.
- ✅ Fallback events are logged in telemetry with `actual_provider=` in notes.

---

### [Completed] Milestone 20: Token Cost Optimization

**Objective:** Control input token billing on long chat sessions by introducing context summarization compression.

**Complexity:** Large

**Dependencies:** M6, M14

**Deliverables:**
- ✅ `ModelPricing` schema (`input_cost_per_1k`, `output_cost_per_1k`) + `DEFAULT_PRICING` dict covering gemini, gpt-4o, claude models on `AIProviderConfig.pricing`.
- ✅ `cost_usd: float` on `Usage`, `InferenceLog`, and `InferenceLogDb` + Alembic migration `7b3c4d5e6f8g`.
- ✅ `cost_calculator.py` utility: apply model pricing to token counts.
- ✅ Orchestrator calculates cost post-inference and logs it; increments `TOKEN_CONSUMPTION` (input/output) and `COST_SPEND` Prometheus counters.
- ✅ `MetricsRegistry` injected into orchestrator constructor (optional, defaults to None).
- ✅ Conversation summarizer: `_summarize_history` compresses history older than `summarize_after_turns` (default 15) into a single summary via the LLM. Configured via `RetrievalSettings.summarize_after_turns`. Applied in both `generate()` and `generate_stream()`. Fails safe on LLM error.
- ✅ Anthropic streaming now captures usage from `message_delta` events.
- ✅ 14 tests covering pricing config, cost calculation, metrics emission, summarization trigger/skip, and anthropic streaming usage.

**Acceptance Criteria:**
- ✅ Chats extending to 50+ messages trigger summarization, reducing context window usage.
- ✅ Token cost is tracked per-inference and available in `InferenceLog.cost_usd`.

---

### [Completed] Milestone 21: Web Search Grounding

**Objective:** Fallback to live web search results when the local database does not contain relevant context chunks.

**Complexity:** Large

**Dependencies:** M5, M6

**Deliverables:**
- ✅ `WebSearchProvider` port with `WebSearchResult` model — abstract `search(query, max_results)` method.
- ✅ `TavilySearchAdapter` — calls `api.tavily.com/search` via httpx, returns clean content. Graceful no-op when API key is empty.
- ✅ `enable_web_search` flag on `FeatureFlags`, plus `web_search_threshold`, `web_search_provider`, `web_search_max_results` on `RetrievalSettings`.
- ✅ `HybridSearchService.search()`: after local search, if top score < threshold, fires web search and appends results with scores below local max. Sorts and trims to `top_k`. Fails safe on API errors.
- ✅ `TAVILY_API_KEY` env var in `settings.py`, wired into `main.py`.
- ✅ Web search fields passed through `SearchQuery` in both search and chat endpoints.
- ✅ 12 tests covering port defaults, Tavily adapter, config fields, low-score trigger, high-score skip, flag-off skip, graceful degradation, and no-web-provider case.

**Acceptance Criteria:**
- ✅ Queries on topics not in local documents (scores < 0.65) trigger Tavily web search.
- ✅ Web results appear as `[Web: Title](url)` citations in the LLM prompt.

---

### [Completed] Milestone 22: Structured Data Extraction

**Objective:** Extract clean, structured JSON payloads directly from unstructured documents using client-specified JSON schemas.

**Complexity:** Medium

**Dependencies:** M11, M13

**Deliverables:**
- `DocumentChunk` domain model confirmed; `get_document_chunks` method on `DocumentRepository` port and `SqlDocumentRepository` adapter.
- `json_schema` field on `InferenceRequest` wired into OpenAI adapter (`response_format={"type": "json_object"}`) and Anthropic adapter (schema appended to system prompt).
- New extraction endpoint: `POST /v1/tenants/{tenantId}/documents/{documentId}/extract` with `ExtractRequest`/`ExtractResponse` DTOs.
- LLM response parsed as JSON; invalid JSON returns 422.

**Acceptance Criteria:**
- Extraction API returns valid JSON output conforming to input schemas.
- Adapters respect `json_schema` field and configure provider accordingly.
- 215+ tests passing.

---

### [Completed] Milestone 23: Multi-Modal Processing

**Objective:** Add OCR and vision support for scanned PDFs and image files during worker ingestion.

**Complexity:** Large

**Dependencies:** M4, M12

**Deliverables:**
- `ChatMessage.images: list[dict]` field added to domain model; `model_dump()` backward-compatible (empty list = string content).
- OpenAI adapter converts `images` to content blocks (`text` + `image_url`) when present; `generate_stream` similarly wired.
- Anthropic adapter converts `images` to Anthropic content blocks (`text` + `image` with base64 source) when present.
- `AIProviderConfig.vision_model` config field (default `gpt-4o`); `Settings.VISION_MODEL` env var.
- Worker extraction pipeline: `mime_type` passed from upload endpoint to Celery task. New `_describe_with_vision()` function in worker calls OpenAI vision API for images and zero-text PDFs (first page).
- `Pillow>=10.0.0`, `openai>=1.0.0` added to worker deps.

**Acceptance Criteria:**
- Uploaded JPEG/PNG images are processed, described, chunked, and indexed.
- Scanned PDFs (zero extractable text) fall through to vision LLM (first page described).
- Text PDFs and plain text files unaffected (no regression).
- 286+ tests passing.

---

### [Completed] Milestone 24: Self-Querying Retrieval

**Objective:** Convert natural language search queries into structured database metadata filters.

**Complexity:** Medium

**Dependencies:** M5, M18

**Deliverables:**
- `SelfQueryProvider` port + `LLMSelfQueryAdapter` — parses natural language into `MetadataFilter` list via LLM (gemini-1.5-flash, 2s timeout, structured JSON output).
- Wired into `HybridSearchService` as step 0: parsed filters merged with existing filters before fan-out search.
- Auto-retry/fallback: adapter returns empty list on any failure (timeout, invalid JSON, LLM error).
- Query rewriting (HyDE) reuses the same pattern via `QueryRewriterProvider` + `LLMQueryRewriterAdapter`, generating a hypothetical document for embedding.
- Full integration coverage with 9 tests.

**Acceptance Criteria:**
- ✅ Querying "invoices from 2025" appends `[{"field": "doc_type", "eq": "invoice"}, {"field": "date_reference", "eq": "2025"}]` filters to the search.
- ✅ On LLM timeout/crash, search proceeds without filters (graceful degradation).
- ✅ 312+ tests passing.

---

### [Completed] Milestone 25: Developer Console & Local Ingestion

**Objective:** Build a Next.js Developer Console with a local Ollama indexing pipeline and validate dynamic configuration fallback logic.

**Complexity:** Medium

**Dependencies:** M10, M11

**Targets:**
- Bootstrapped `apps/developer-console` using Next.js 16 and `@prat3010/retriever-client-js`.
- Configured local Ollama embeddings (`nomic-embed-text`) inside `ingest_self.py` to index the codebase.
- Enforced platform key access rules matching backend endpoint API validation.
- Implemented chat playground with real-time SSE token stream rendering.

---

### [Completed] Milestone 26: SaaS Tenant Resource Quotas

**Objective:** Enforce SaaS resource limits (file counts, storage volumes, token budgets, daily requests) at the tenant API level.

**Complexity:** Medium

**Dependencies:** M9, M15

**Targets:**
- ✅ Add limits configuration schemas (`max_documents`, `max_storage_bytes`, `max_monthly_tokens`, `max_daily_requests`, `soft_limit_percentage`) to `TenantQuotaSettings`.
- ✅ Implement `QuotaService` domain component and `SqlQuotaRepository` adapter for real-time usage calculation.
- ✅ Implement quota validation hooks on document upload (`/v1/documents`) and chat message (`/v1/chat`) API endpoints.
- ✅ Trigger `402 Payment Required` or `429 Quota Exceeded` exceptions with quota response headers (`Quota-Exceeded-Resource`, `Quota-Limit`, `Quota-Usage`).
- ✅ Attach `X-Quota-Warning` header when soft limit percentage is crossed.

**Acceptance Criteria:**
- ✅ Uploading documents beyond the tenant's configured limit is blocked and throws 402 Payment Required.
- ✅ Exceeding token or request budgets returns 429 Too Many Requests.
- ✅ 7/7 unit tests pass in `test_tenant_quotas.py`.

---

### [Completed] Milestone 27: Multi-Workspace Collections

**Objective:** Allow tenants to partition their documents into isolated collections/workspaces.

**Complexity:** Medium

**Dependencies:** M9, M13, M18

**Targets:**
- ✅ Add `collection_id` uuid column to `documents`, `document_chunks`, and `vector_records` tables with indexing.
- ✅ Update document upload, list, search, and chat API endpoints to accept optional `collectionId` scoping parameters.
- ✅ Restrict vector (`pgvector`), sparse (`tsvector`), and hybrid search queries to matching collection boundaries when specified.
- ✅ Inherit `collection_id` from document down to generated chunks and vector embeddings during ingestion.

**Acceptance Criteria:**
- ✅ Search and chat queries within collection "Legal" never return search chunks from collection "HR".
- ✅ 6/6 unit tests pass in `test_workspace_collections.py`.

---

### [Completed] Milestone 28: Interactive Chunking Auditor

**Objective:** Provide administrative users with a visual preview sandbox to audit document chunking splits before indexing.

**Complexity:** Medium

**Dependencies:** M10, M13

**Targets:**
- ✅ Implement chunk preview sandbox API: `POST /v1/admin/tenants/{tenantId}/documents/chunk-preview`.
- ✅ Build `ChunkerFactory` supporting `sliding`, `semantic`, and `hierarchical` chunking strategies.
- ✅ Calculate character start/end index offsets (`startCharIdx`, `endCharIdx`), character lengths, and token counts without database or vector store side effects.
- ✅ Expose structured preview payloads (`totalChunks`, `totalTokens`, `totalChars`, `avgChunkTokens`) for administrative auditor inspection.

**Acceptance Criteria:**
- ✅ Auditor endpoint returns exact split positions and token size estimations for visual dashboard rendering.
- ✅ 5/5 unit tests pass in `test_chunking_auditor.py`.

---

### [Completed] Milestone 29: A/B Testing Platform

**Objective:** Full experiment management lifecycle — create, start, stop experiments via admin API, with per-variant performance telemetry.

**Complexity:** Medium

**Dependencies:** M10, M14, M19

**Targets:**
- ✅ Admin experiment CRUD APIs: `GET`, `POST`, `PUT`, `DELETE` `/v1/admin/tenants/{tenantId}/experiments`.
- ✅ Status lifecycle management: `POST /v1/admin/tenants/{tenantId}/experiments/{experimentId}/status` (`draft`, `active`, `paused`, `completed`).
- ✅ Per-variant metrics aggregation: `GET /v1/admin/tenants/{tenantId}/experiments/{experimentId}/metrics` (requests, tokens, avg/p95 latency).
- ✅ Deterministic variant allocation (`assign_variant`) and overrides (`apply_overrides`) in both `chat` and `search` routers.

**Acceptance Criteria:**
- ✅ Admin can create, start, pause, edit, delete, and inspect per-variant metrics for A/B experiments.
- ✅ Pausing or stopping an experiment routes traffic back to baseline tenant configuration.
- ✅ 3/3 unit tests pass in `test_ab_testing.py`.

---

### [Completed] Milestone 30: Production Polish

**Objective:** Close the gap between a feature-complete codebase and a production-hardened deployment. Real-world Oracle VPS operation revealed gaps in deployment docs, secrets management, observability, CI/CD, and LLM key lifecycle.

**Prerequisites:** M25 (all prior features are complete).

**Complexity:** Medium

**Dependencies:** None

**Expected Outcome:** Deployment topology documented accurately; secrets managed via .env with rotation process; basic monitoring and alerting active; CI/CD pipeline exists; LLM API key provisioning is documented and repeatable.

**Targets:**
- ✅ Real deployment topology documented: Oracle VPS, systemd, nginx reverse proxy, Let's Encrypt SSL, Ollama sidecar — replaces stale K8s/Docker references.
- ✅ Secrets management: all env vars in single `.env` on server; encrypted LLM keys at rest (AES-256-GCM KEK verified in code); rotation process documented.
- ✅ Observability: `/metrics` endpoint exposed and reachable via https (verified `curl https://rag.prateeq.in/metrics` → 200); **Sentry configured** (DSN live, EU region, test error ingested 2026-07-31); uptime monitoring ⬜ unverifiable (external service).
- ✅ Basic alerting: `scripts/quota-alert.sh` — daily cron check of LLM key usage (OpenRouter `/auth/key`), ntfy.sh push + optional webhook when remaining < 20%/10%. ⚠️ Platform key is currently free-tier → reports "not monitorable"; monitorable once a prepaid key is used.
- ✅ Backup automation: `scripts/backup-db.sh` — nightly cron (02:30 UTC), per-table gzipped CSV over the Supabase pooler (pg_dump incompatible with pgbouncer), 14-day retention, manifest per run. Verified: 20 tables backed up. Restore procedure in DEPLOYMENT.md (schema rebuilt via Alembic).
- ✅ CI/CD: GitHub Actions workflow for deploy (`deploy-api.yml` — SSH + `systemctl restart` + post-deploy smoke test); all secrets configured (verified `ORACLE_HOST/USER/SSH_KEY/PORT` in GitHub secrets).
- ✅ Nginx hardening: rate limiting (`20r/s` zone, burst 40) + HSTS/CSP/nosniff/DENY headers verified live; fail2ban `sshd` jail active (maxretry 4, bantime 1h).
- ✅ LLM key operational process: documented how to provision a new key, update tenant config, and verify chat works end-to-end (DEPLOYMENT.md provisioning checklist).
- ✅ Staging environment: documented process (local dev + CI + auto-deploy smoke test; second Oracle VM optional) in DEPLOYMENT.md.
- ✅ Root cause documentation: addendum added to DEPLOYMENT.md explaining the initial deploy chat outage (both LLM keys exhausted quota; M19 failover had no healthy fallback; lessons applied).

**Acceptance Criteria:**
- ⬜ New developer can deploy Retriever from scratch following docs alone (no tribal knowledge) — verify.
- ✅ CI/CD pipeline deploys code changes with zero manual SSH steps beyond initial setup (`deploy-api.yml` + secrets verified).
- ✅ Nightly DB backups exist with verified restore procedure — backup runs + manifests verified; restore documented.
- ✅ LLM key expiry/quota exhaustion triggers an alert before it blocks chat — quota-alert.sh + cron live (monitorable once key is prepaid).
- ✅ All architecture docs reconcile with the actual Oracle VPS topology — Render references removed (docs cleanup).

---

### [Completed] Milestone 31: Security Hardening & Secrets Remediation

**Objective:** Eliminate credential exposure in version control, enforce fail-safe production defaults, harden network perimeter, and fix weak authentication checks in the admin proxy.

**Complexity:** Medium

**Dependencies:** None

**Targets:**
- ✅ Root `.env` never committed (verified: `git log --diff-filter=A -- .env` is empty). Credential rotation of leaked Supabase DB password / OpenAI key: ⬜ still required.
- ✅ `apps/web/.env.local` scrubbed from git history (commit `53c6286`, all 148 commits, branches `main` + `decompose-main-py`) via `git-filter-repo` + force-push (2026-07-31). Token verified expired on its own (2026-07-18, `exp` claim + Vercel API 403) — rotation unnecessary. Server git objects purged (`reflog expire` + `gc --prune=now`); root `.gitignore` hardened to `.env*`.
- ✅ `@model_validator(mode="after")` in `config.py` crashes FastAPI startup with `ValueError` if `ENVIRONMENT == "production"` and `ADMIN_MASTER_KEY` or `KEY_ENCRYPTION_KEY` still have their default development values (config.py:66-84).
- ✅ SSH into Oracle VM: `ADMIN_MASTER_KEY` and `KEY_ENCRYPTION_KEY` in production `.env` are **not** default values (verified on server).
- ✅ Remove port 8000 ingress rule from Oracle Cloud security group — verified: `nc` to `130.210.35.134:8000` from external host times out (filtered); API only reachable via nginx 443/80.
- ✅ `proxy.ts`: validates `admin_key` cookie against backend `GET /v1/admin/verify-key` (5-min validated cookie cache); invalid keys are cleared and redirected to `/login` (apps/web/src/proxy.ts).

**Acceptance Criteria:**
- ✅ `git log --diff-filter=A -- .env` returns empty (no `.env` file in history) — verified.
- ✅ Starting API in production mode with default secrets raises `ValueError` and exits — verified in code.
- ✅ Port scan on Oracle VM public IP shows port 8000 as filtered/closed — verified from external host.
- ✅ Admin dashboard with random cookie string redirects to `/login` — verified in code.

---

### [Completed] Milestone 32: Onboarding & Client UX Overhaul

**Objective:** Fix the broken onboarding handoff (no user created during wizard), eliminate confusing defaults in the client login form, introduce human-friendly short IDs, and polish the admin and client UX around identity management.

**Complexity:** Medium

**Dependencies:** M9 (Users model)

**Targets:**
- ✅ **Add user creation to onboarding wizard:** Insert Step 2.5 between "API Key" and "Credentials" in `onboard/page.tsx`. Auto-create a user with the tenant name as display name. Display the real `userId` (or short ID) in the final credentials card alongside tenant ID and API key.
- ✅ **Fix client login form defaults in `RagInterface.tsx`:**
  - ✅ Set `tenantId` default to `""` (empty — force entry).
  - ✅ Set `userId` default to `""` (empty — force entry).
  - ✅ Change API key placeholder from `sk_live_...` to `ret_live_...`.
  - ✅ Keep `apiUrl` default as `https://rag.prateeq.in`.
- ⬜ **Simplify tenant and user IDs:** Frontend done (relaxed `isUuid()` to accept `tn_`/`usr_` short IDs). **Backend deferred:** add short ID columns, accept short IDs in API paths, keep UUID as internal primary key — not built.
- ✅ **Show internal User ID in Users tab:** Add a "User ID" column to `tenant-users.tsx` table with a copy-to-clipboard action so admins can easily provide it to clients.
- ✅ **Hide API Base URL field:** In `ConfigPanel`, show the API URL field only when an "Advanced" toggle is enabled. Default value stays as `https://rag.prateeq.in`.

**Documents to Update:**
- ✅ `ONBOARDING_WORKFLOW.md` — reflect the new 4-step wizard with user creation.
- ✅ `ADMIN_DASHBOARD_GUIDE.md` — update `/onboard` section to describe the new user step.
- ✅ `docs/features/admin-dashboard.md` — update agent guide.
- ✅ `Prateek_website/docs/rag-lab.md` — update Config Tab section to reflect new defaults.
- ✅ `TECH_DEBT.md` — mark onboarding gap and UX issues as resolved.

**Acceptance Criteria:**
- ✅ Onboarding a new client through the admin wizard produces a Tenant ID, User ID, and API Key — all usable immediately without visiting a separate tab.
- ✅ Client connects at `prateeq.in/rag` by entering only Tenant ID, User ID, and API Key (URL is pre-filled and can be changed via Advanced toggle).
- ⬜ Short IDs (`tn_X7kM2p`, `usr_Qp3N8w`) are accepted by both admin and client apps — partial: client accepts, backend API paths still UUID-only (deferred).
- ✅ Admin Users tab displays the internal short User ID with one-click copy.

---

### [Completed] Milestone 33: Code Quality & Architecture

**Objective:** Break down the 2,250-line `main.py` monolith, eliminate type safety gaps, consolidate duplicated constants, and clean up inconsistent patterns across both the backend and frontend codebases.

**Complexity:** Large

**Dependencies:** None

**Targets:**
- ✅ **Split `main.py` into FastAPI routers:** `routers/tenant.py`, `routers/document.py`, `routers/search.py`, `routers/chat.py`, `routers/admin.py`, `routers/health.py` — all 55+ handlers extracted; `main.py` reduced to bootstrap (170 lines); shared DI wiring moved to `container.py`.
- ✅ **Add shared TypeScript types in `rag-client.ts` or a new `rag-types.ts`:** `SearchResult { chunkId, content, score, metadata }`, `DocumentMeta { documentId, filename, status, createdAt }`, `SearchResponse { results, searchMeta? }`; `any` types and `eslint-disable` comments removed from `RagInterface.tsx`.
- ✅ **Consolidate `API_BASE` constant:** duplicate definitions removed from `onboard/page.tsx` and `login/page.tsx`; imported from `lib/api.ts` exclusively.
- ✅ **Clean up `RetrieverClient` (`rag-client.ts`):** `uploadDocument` and `deleteDocument` refactored to the shared `request<T>()` pipeline; shared auth-header helper extracted.
- ✅ **Remove duplicate cookie clearing in `sidebar.tsx`:** logout handler no longer sets `document.cookie` directly — `clearKey()` in `store/auth.ts` handles it.

**Documents to Update:**
- ✅ `docs/architecture.md` — updated for router structure.
- ✅ `TECH_DEBT.md` — main.py god-file marked resolved.
- ✅ `CHANGELOG.md` — architectural changes recorded.
- ✅ `Prateek_website/docs/rag-lab.md` — client class references updated.

**Acceptance Criteria:**
- ✅ All existing unit tests pass with the new router structure (369 at the time; current suite: 407/407).
- ✅ `RagInterface.tsx` has zero `any` types and zero `eslint-disable` comments.
- ✅ `grep -r "API_BASE" apps/web/src/ | grep -v "lib/api.ts" | grep -v node_modules` returns empty.
- ✅ `uploadDocument` and `deleteDocument` in `rag-client.ts` share the same request pipeline as other methods.

---

### [Completed] Milestone 34: Production Operations & DevOps

**Objective:** Eliminate manual SSH deploys, add error tracking and uptime monitoring, fix unbounded tenant queries, and close the remaining production operations gaps identified in the analysis.

**Complexity:** Medium

**Dependencies:** M31

**Targets:**
- ✅ **GitHub Actions auto-deploy to Oracle VM:** `.github/workflows/deploy-api.yml` exists — triggers on push to `main` affecting `apps/api/` or `packages/`, SSHes into the Oracle VM (deploy key in GitHub Secrets), pulls + restarts `retriever-api`, runs post-deploy smoke tests. All secrets configured (verified: `ORACLE_HOST/USER/SSH_KEY/PORT` in GitHub secrets).
- ✅ **Configure Sentry:** `SENTRY_DSN` set in production `.env` (EU region), app restarted, test error ingested and confirmed. ⚠️ Required fix during enablement: server had older `sentry-sdk` whose OTel integration re-export changed — import now uses `sentry_sdk.integrations.opentelemetry.integration` (main.py:40).
- ⬜ **Uptime monitoring:** Configure UptimeRobot or Better Uptime to check `https://rag.prateeq.in/health/liveness` every 5 minutes — external service, unverifiable.
- ✅ **Add pagination to `useAllTenants`:** hardcoded `?limit=1000` replaced with configurable `limit` param, default 50 (`apps/web/src/hooks/use-tenants.ts`).

**Documents to Update:**
- ⬜ `DEPLOYMENT.md` — document the auto-deploy workflow and Sentry setup — workflow exists, Sentry section pending.
- ⬜ `ORACLE_DEPLOYMENT_REFERENCE.md` — update deployment procedure to reference CI/CD — verify.
- ⬜ `TECH_DEBT.md` — mark deploy and monitoring items as resolved — verify.
- ⬜ `PROJECT_STATUS.md` — update DevOps health indicators — verify.

**Acceptance Criteria:**
- ⬜ Pushing a change to `apps/api/src/main.py` triggers the deploy workflow and restarts the API on Oracle VM within 2 minutes — workflow + secrets present, end-to-end run unverified.
- ✅ A deliberate `raise Exception("test")` in a route handler appears in Sentry within 60 seconds — verified via `sentry_sdk.capture_exception()` one-off (error "Sentry wiring test from retriever-oracle-vm" ingested).
- ⬜ UptimeRobot dashboard shows green status for `rag.prateeq.in` with 5-minute check intervals — external, unverifiable.
- ✅ `useAllTenants` no longer fetches 1000 records in a single query — verified (default 50).

---

### [Completed] Milestone 35: Final Polish & Infrastructure Self-Detection

**Objective:** Add server-spec auto-detection for infrastructure services, update stale model defaults, clean up deprecated Docker Compose syntax, and improve the client chat UI for large screens.

**Complexity:** Small

**Dependencies:** None

**Targets:**
- ⬜ **Server-spec auto-detection (`config.py`):** `InfraCapabilities` class exists — reads total RAM (`psutil.virtual_memory().total`) and CPU cores (`os.cpu_count()`) at startup and **logs** viability thresholds (Redis ≥2 GB, Broker ≥2 GB, Workers ≥4 GB + 2 cores) with boot message `INFO: Server specs: 0.9 GB RAM, 1 CPU core. Running in LEAN mode (synchronous processing).` Env overrides `REDIS_ENABLED/BROKER_ENABLED/WORKERS_ENABLED` accepted but **not yet consumed** — nothing reads these flags (known gap; wiring into `container.py` tracked separately as spec-gated deployment).
- ✅ **Update Gemini default model:** `defaultModel` for Gemini provider in `providers.ts` changed from `gemini-1.5-flash` to `gemini-2.5-flash` (verified apps/web/src/lib/providers.ts:25).
- ✅ **Remove Docker infrastructure:** `docker-compose.yml`, `Dockerfile`, `workers/Dockerfile.worker`, `apps/api/docker-compose.test.yml`, `.github/workflows/docker.yml` removed (verified — no Docker files remain in repo).
- ⬜ **Chat container height:** `max-height: min(60vh, 600px)` change unverifiable — `rag.module.css` no longer present in repo (chat UI moved/removed).

**Documents to Update:**
- ⬜ `TECH_DEBT.md` — mark all items as resolved — verify.
- ⬜ `CHANGELOG.md` — record final polish changes — verify.
- ⬜ `PROJECT_STATUS.md` — final status update across all milestones — done, but contained stale claims; corrected during docs cleanup.

**Acceptance Criteria:**
- ✅ API startup log shows correct auto-detection message for Oracle VM (0.9 GB RAM, LEAN mode) — verified (`InfraCapabilities.log_boot_status()` runs at import, config.py:146-148).
- ✅ Admin dashboard provider list shows `gemini-2.5-flash` as the default for Gemini — verified.
- ✅ No Docker files remain in repo (was: "docker compose config validates" — obsolete once Docker was removed).
- ⬜ Chat pane on a 1440px screen shows more messages before scrolling (taller container) — unverifiable, file absent.

---

### [Completed] Milestone 36: SaaS Data Connectors Framework

**Objective:** Build an extensible background data connector framework (`BaseConnector`) to discover, ingest, and sync documents from external sources (Web Crawlers, Google Drive, Notion, Slack, S3).

**Targets:**
- ✅ Define `BaseConnector` abstract domain port and `ConnectorConfig` models in `src/domain/abstractions/connector.py`.
- ✅ Implement `WebCrawlerConnector` (HTML-to-markdown scraping with depth and domain bounds) and `MockCloudDriveConnector` (cloud discovery & delta sync).
- ✅ Build `ConnectorRegistry` strategy lookup.
- ✅ Admin connector CRUD & sync trigger APIs: `GET`, `POST`, `PUT`, `DELETE` `/v1/admin/tenants/{tenantId}/connectors` and `POST .../connectors/{connectorId}/sync`.
- ✅ 3/3 unit tests pass in `test_data_connectors.py`.

**M36.5 addendum (post-M36, tracked in PROJECT_STATUS):** Modular Target-Engine Embedding & Remote Storage Fallback — `targetEngine` (`laptop` | `oracle` | `auto`) query param on `POST /v1/admin/tenants/{tenantId}/documents/{documentId}/process`; real-time `PENDING → PROCESSING → INDEXED` status; remote HTTP file retrieval via `REMOTE_STORAGE_API_URL` when files are missing locally; batch processing CLI (`scripts/process-pending.sh`).

---

### [Completed] Milestone 37: GraphRAG & Knowledge Graph Indexing

**Objective:** Complement vector + keyword hybrid search with entity-relationship knowledge graph extraction and multi-hop graph retrieval.

**Targets:**
- ✅ Environment Auto-Detection (`InfraCapabilities.detect()`): Auto-tailors execution profile between low-RAM Oracle VM (PostgreSQL) and MacBook Air M4 (Dual Engine).
- ✅ Define `BaseGraphRepository` abstract domain port and models in `src/domain/abstractions/graph.py`.
- ✅ Implement `PgGraphRepository` (PostgreSQL `graph_triples` + Recursive SQL) and `Neo4jGraphRepository` (async Cypher driver with auto-fallback).
- ✅ Implement `GraphExtractor` for triple parsing during document ingestion.
- ✅ Admin Graph & Capabilities APIs: `GET /v1/admin/tenants/{tenantId}/graph/capabilities`, `POST .../graph/engine`, `GET .../graph`, `POST .../graph/query`, `DELETE .../graph/triples/{tripleId}`.
- ✅ 5/5 unit tests pass in `test_graphrag.py` (Total test suite: 412/412 tests passing).
- ✅ **Resolved in M44 (v0.42.0):** Graph-aware retrieval wired into search/chat, `neo4j` driver dependency declared, and Neo4j relationship `document_id` tracking fixed.

---

### [Completed] Milestone 38: Critical Security Remediation (v0.36.0, 2026-08-04)

**Objective:** Close the critical application-level security defects identified in the August 2026 security audit. This milestone gates any public SaaS sale: the current Google OAuth flow provisions sessions from unverified client-supplied email, the metadata filter builder interpolates unvalidated field names into SQL, and the local file-serve path allows cross-tenant path traversal with a default HMAC key. No feature milestone ships before this one.

**Complexity:** Medium

**Dependencies:** None

**Status:** ✅ All code targets landed in v0.36.0 (2026-08-04); full suite 425 passed, 1 skipped; `ruff check` clean. Remaining follow-up outside the milestone: guest demo key provisioning and `docs/rag-lab.md` Auth section refresh. **Deploy note:** the server must set `SECRET_KEY` (>=32 chars, random), `STORAGE_HMAC_KEY` (random), and `OIDC_AUDIENCE` (Google OAuth client ID) or startup fails — see CHANGELOG v0.36.0.

**Targets:**
- **Google OAuth verification (`src/routers/auth.py`):**
  - Enforce `aud` verification against a configured Google client ID (`OIDC_AUDIENCE`) and validate the issuer claim (`accounts.google.com`) on every ID token.
  - Remove the unverified client-supplied `email` fallback for session provisioning, or gate it strictly behind `ENVIRONMENT != "production"`.
  - Fix the existing-user branch that generates a new API key without persisting it (`auth.py:97`) — persist the generated key hash atomically.
  - Replace the hardcoded JWT signing fallback (`"retriever-jwt-secret-key-2026"`) with a required `SECRET_KEY` setting enforced by the production validator (`config.py` `validate_production_secrets`).
- **SQL-injection-safe metadata filters (`src/adapters/vector/filter_builder.py`):**
  - Validate `MetadataFilter.field` against a strict `[a-zA-Z0-9_]+` whitelist before SQL interpolation; return 422 on invalid field names.
  - Add regression tests with injection payloads (`"x' OR 1=1--"`, `"a') ; DROP TABLE--"`, etc.).
- **File-serve hardening (`src/routers/document.py`, `src/adapters/storage/local_storage.py`):**
  - Basename-only filename validation (reject `..`, absolute paths, null bytes) in `serve_local_download`.
  - Make `STORAGE_HMAC_KEY` a required non-default secret in production (extend `validate_production_secrets`); constant-time signature comparison.
- **Defense-in-depth batch:**
  - Enforce an upload size cap before reading the request body into memory (`src/routers/document.py:79`).
  - Fail startup (or warn loudly) when `RATE_LIMIT_ENABLED=False` in production.
  - Add RLS policies for `eval_datasets`, `eval_questions`, `eval_runs`, `eval_run_results`, and `graph_triples` (`src/adapters/database/setup.py`).
  - Redact tracebacks from the global exception handler (`src/main.py:99-103`).
- **Demo credential resolution:** provision a server-side guest tenant + read-only API key for the `prateeq.in/rag` live demo (or remove the demo) so the public sandbox either works or is not advertised.

**Documents to Update:**
- `PROJECT_STATUS.md` — correct the "RLS active on all customer-data tables" and "`/v1/auth/google` verifies Google JWKS tokens" claims.
- `TECH_DEBT.md` — move resolved items to the Fixed table.
- `CHANGELOG.md` — record the remediation release.
- `docs/rag-lab.md` — update the Au### [Completed] Milestone 39: Production Multi-Tenant Identity & Workspace Portal

**Objective:** Upgrade client authentication to production-ready multi-tenant Supabase Auth OIDC/JWKS verification with zero-touch workspace auto-provisioning.

**Deliverables:**
- ✅ **Supabase Auth RS256 JWKS Verification:** Integrated in `src/adapters/api/security.py` with 1-hour in-memory key caching (`_jwks_cache`) and claim extraction.
- ✅ **Auto-Tenant & User Provisioning:** `security.py` automatically provisions new `TenantDb`, `UserDb`, and `ApiKeyDb` records in PostgreSQL upon first touch from an authenticated Supabase Auth user.
- ✅ **Session Context Endpoint:** Implemented `GET /v1/auth/session` in `src/routers/auth.py` returning active session context (`tenantId`, `userId`, `roles`, `scopes`).
- ✅ **Client Workspace Studio Integration:** Connected `ConfigPanel.tsx` in `Prateek_website` (`/rag/app`) to query `/v1/auth/session` using the client's Supabase access token for zero-touch workspace access.
- ✅ **Unit Test Suite:** Added `tests/test_supabase_auth.py` verifying JWKS decoding, endpoint payload, and auto-provisioning (428 total tests passing).

---

### Milestone 40: Active Real-Time LLM Safety Guardrails (Completed - v0.38.0)

**Objective:** Protect the platform against malicious prompt injections, system prompt extraction, jailbreaks, and unverified PII leaks.

**Deliverables:**
- ✅ **Pre-Execution Input Guardrail Pass:** Fast heuristic regex pre-checks combined with Llama Guard 3 taxonomy classification prompt template (`llm_safety_guard.py`).
- ✅ **Post-Execution Output Guardrail Pipeline:** Output PII & secret redactor (`output_guardrails.py`) scrubbing SSNs, credit cards, API keys, and auth tokens.
- ✅ **Router Integration:** Applied output guardrail pipeline to `/v1/chat` responses in `chat.py`.
- ✅ **Unit Test Suite:** Added `tests/test_llm_safety_guardrails.py` verifying pre-execution injection blocks, PII scrubbing, and output safety (433 total tests passing).

---

### [Completed] Milestone 41: Chunk-Level Granular Access Control (ACL) & DB RLS Hardening (v0.39.0)

**Objective:** Enforce zero-trust multi-tenancy and user/role-level authorization at the document chunk level.

**Targets:**
- ✅ Added `allowed_roles` and `allowed_users` fields to `DocumentChunk` domain schema and filter builder.
- ✅ Updated vector (`pgvector`) and sparse search queries to evaluate `X-User-ID` and `X-User-Role` claims against chunk ACL lists.
- ✅ Enforced zero-trust fallbacks hiding restrictive ACL chunks from unauthorized users.
- ✅ Added unit test suite `apps/api/tests/test_chunk_acl.py` verifying ACL SQL filter conditions.


---

### [Completed] Milestone 42: Layout-Aware Vision OCR & Table Parsing (v0.40.0)

**Objective:** Upgrade document ingestion from PyPDF2 text extraction to layout-aware OCR and vision-model parsing for scanned PDFs, multi-column layouts, and complex tables.

**Targets:**
- ✅ Implemented `convert_table_to_markdown` for matrix grid to GitHub Flavored Markdown table transformation.
- ✅ Added `extract_layout_from_pdf` to preserve multi-column reading order and structured page blocks.
- ✅ Integrated layout-aware parsing into `sync_ingestion_service.py` and Celery worker ingestion tasks.
- ✅ Enriched chunk `meta_data` with `has_tables`, `table_count`, and `layout_parsed` attributes.
- ✅ Added unit test suite `apps/api/tests/test_layout_parser.py`.


---

### [Completed] Milestone 43: Dynamic Multi-Embedding Vector Schemas & Index Scaling (v0.41.0)

**Objective:** Remove rigid vector dimension constraints (`Vector(768)`) to support seamless switching across different embedding models (768, 1536, 3072 dims) without database migration failures.

**Targets:**
- ✅ Declared `VectorRecord1536Db` (`vector_records_1536`) and `VectorRecord3072Db` (`vector_records_3072`) models in `src/adapters/database/models.py`.
- ✅ Configured Row-Level Security (RLS) policies and HNSW cosine indexes (`idx_vector_records_1536_embedding` and `idx_vector_records_3072_embedding`) in `src/adapters/database/setup.py`.
- ✅ Updated `PgVectorSearchAdapter.search_similar` in `src/adapters/vector/vector_repository.py` to route search queries dynamically based on vector dimension.
- ✅ Updated `sync_ingestion_service.py` to instantiate dimension-matched vector models during document uploads.
- ✅ Added unit test suite `apps/api/tests/test_multi_embedding.py`.


---

### [Completed] Milestone 44: GraphRAG Productionization & Retrieval Integration (v0.42.0)

**Objective:** Productionize the Knowledge Graph by adding the `neo4j` Python driver dependency, fixing Neo4j relationship `document_id` tracking, logging ingestion graph extraction errors, and fusing multi-hop graph triples into `HybridSearchService` for search and chat inference.

**Complexity:** Medium

**Dependencies:** M37

**Delivered Capabilities:**
- **Neo4j Driver Dependency & Persistence:** Added `neo4j>=5.18.0` to `apps/api/pyproject.toml` and updated `Neo4jGraphRepository` to set and read `r.document_id` on relationship edges.
- **Fixed Document Deletion & Logging:** Fixed `delete_document_triples` relationship deletion in Neo4j and replaced silent ingestion exception swallows in `sync_ingestion_service.py` with `logger.warning`.
- **Graph Evidence Retrieval Fusion:** Added `enable_graph_search` flag to `SearchQuery` and implemented `_apply_graph_search_pass` in `HybridSearchService` to automatically fetch and prepend graph evidence (`[Graph Evidence] Subject -- PREDICATE --> Object`).

---

### [Completed] Milestone 45: Learned Sparse Retrieval (SPLADE) & Reranker Microservice (v0.43.0)

**Objective:** Enhance sparse keyword matching with learned sparse token expansion (SPLADE) and offload cross-encoder reranking from in-process execution to an external Text Embeddings Inference (TEI) microservice container.

**Delivered Capabilities:**
- **TEI Reranker Microservice Adapter** (`apps/api/src/adapters/cognitive/tei_reranker_adapter.py`): Built `TeiRerankerAdapter(RerankerProvider)` to offload cross-encoder scoring to external TEI HTTP endpoints (`TEI_RERANK_URL`) with graceful fallback to local cross-encoders.
- **SPLADE Learned Sparse Search Adapter** (`apps/api/src/adapters/vector/splade_sparse_adapter.py`): Implemented `SpladeSparseSearchAdapter(KeywordSearchProvider)` with term weight extraction (`extract_sparse_weights`) and expanded PostgreSQL query generation (`build_expanded_query_string`).
- **Configuration & Resolution Wiring** (`apps/api/src/config.py`, `apps/api/src/container.py`): Added `TEI_RERANK_URL` and `SPARSE_SEARCH_PROVIDER` settings with automatic fallback resolution chains (`Cohere` -> `TEI` -> `LocalReranker`).
- **Unit Test Suite** (`apps/api/tests/test_splade_and_reranker.py`): Created unit test suite verifying TEI HTTP API calls, threshold filtering, fallbacks, and SPLADE term expansion (451 total unit tests passing).

---

### [Completed] Milestone 46: Agentic Workflow Execution Engine (v0.44.0)

**Objective:** Extend the generative inference layer from conversational RAG to autonomous multi-step tool execution loops with tool registration registries, multi-turn function calling parsers, and step orchestration engines.

**Delivered Capabilities:**
- **Agent Domain Models** (`apps/api/src/domain/agentic/abstractions.py`): Defined Pydantic models for `ToolDefinition`, `ToolCall`, `ToolResult`, `AgentStep`, `AgentExecutionRequest`, and `AgentExecutionResult`.
- **Tool Registry** (`apps/api/src/domain/agentic/tool_registry.py`): Built central registry to register, unregister, whitelist, and execute sync/async tool handlers (including built-in safe `calculator` tool).
- **Agentic Execution Engine** (`apps/api/src/domain/agentic/execution_engine.py`): Implemented `AgenticExecutionEngine` for multi-turn ReAct reasoning loops, thought extraction, tool call parsing, and final response synthesis.
- **FastAPI Agentic Router** (`apps/api/src/routers/agentic.py`): Exposed `POST /v1/tenants/{tenantId}/agentic/execute` and `GET /v1/tenants/{tenantId}/agentic/tools` endpoints.
- **Unit Test Suite** (`apps/api/tests/test_agentic_engine.py`): Created unit tests verifying tool registry, calculator execution, ReAct loop reasoning, and router endpoints (456 total unit tests passing).

---

### [Completed] Milestone 47: Recursive Language Model (RLM) Engine & REPL Sandbox (v0.45.0)

**Objective:** Integrate a Recursive Language Model (RLM) inference super-layer (`src/domain/rlm/`) over Retriever's document chunk trees, enabling active programmatic data exploration, safe Python REPL sandboxing, and recursive sub-LLM calls for complex multi-document analytical synthesis.

**Delivered Capabilities:**
- **RLM Domain Abstractions** (`apps/api/src/domain/rlm/abstractions.py`): Defined Pydantic models & interfaces for `ReplExecutionResult`, `ReplSandboxProvider`, `RlmAnalysisRequest`, and `RlmAnalysisResult`.
- **Restricted Python REPL Sandbox** (`apps/api/src/adapters/sandbox/python_sandbox_adapter.py`): Implemented `RestrictedPythonSandboxAdapter` with safe AST parsing, blocking dangerous imports (`os`, `sys`, `subprocess`, `socket`), safe built-ins, and 15-second execution timeout bounds.
- **RLM Execution Engine** (`apps/api/src/domain/rlm/engine.py`): Built multi-pass analytical synthesis engine combining vector/graph search, programmatic Python REPL script execution, and recursive sub-LLM synthesis.
- **FastAPI RLM Router** (`apps/api/src/routers/rlm.py`): Exposed `POST /v1/tenants/{tenantId}/rlm/analyze` endpoint.
- **Unit Test Suite** (`apps/api/tests/test_rlm_engine.py`): Created unit tests verifying AST security blocking, REPL math execution, RLM synthesis, and router endpoints (460 total unit tests passing).

---

### [Completed] Milestone 48: Multi-Agent Consensus & Critic Reflection Loops (v0.46.0)

**Objective:** Enhance response precision for high-stakes enterprise decisions using multi-agent debate and validation loops (Generator Agent vs. Critic/Auditor Agent), featuring dynamic dual-provider AI model switching capabilities.

**Delivered Capabilities:**
- **Consensus Domain Models** (`apps/api/src/domain/consensus/abstractions.py`): Defined Pydantic models for `CriticEvaluation`, `ConsensusRequest`, and `ConsensusResult`.
- **Multi-Agent Reflection Engine** (`apps/api/src/domain/consensus/reflection_loop.py`): Built `MultiAgentConsensusEngine` running an iterative reflection loop between Generator and Critic/Auditor agents to eliminate hallucinations and enforce evidence compliance.
- **Dual-Provider AI Switching**: Added dynamic provider resolution allowing Generator and Critic roles to use separate LLM providers (e.g. Gemini as Generator, Anthropic/OpenAI as Critic) or fall back seamlessly to single-provider mode.
- **FastAPI Consensus Router** (`apps/api/src/routers/consensus.py`): Exposed `POST /v1/tenants/{tenantId}/consensus/generate` endpoint.
- **Unit Test Suite** (`apps/api/tests/test_consensus_loop.py`): Created unit tests verifying single-provider, dual-provider cross-model auditing, revision loops, and router endpoints (463 total unit tests passing).

---

### [Completed] Milestone 49: Context Compression & Zero-Trust Field Encryption (v0.47.0)

**Objective:** Minimize LLM inference token overhead and protect sensitive enterprise data stored in vector databases using intelligent context window compression and tenant-scoped AES-256 envelope encryption.

**Delivered Capabilities:**
- **Security & Compression Domain Models** (`apps/api/src/domain/security_compression/abstractions.py`): Defined Pydantic models for `CompressionRequest`, `CompressionResult`, `EncryptionRequest`, `EncryptionResult`, `DecryptionRequest`, and `DecryptionResult`.
- **Intelligent Context Window Compressor** (`apps/api/src/adapters/cognitive/context_compressor_adapter.py`): Built `IntelligentContextCompressor` trimming filler words, redundant phrases, and non-essential sentences while preserving numbers, dates, named entities, and key factual statements (cutting LLM token costs & latency by up to 50%).
- **AES-256 Envelope Field Encryptor** (`apps/api/src/adapters/security/encryption_adapter.py`): Built `Aes256FieldEncryptor` providing tenant-derived Fernet/AES-256-GCM symmetric encryption for zero-trust data protection at rest.
- **FastAPI Security & Compression Router** (`apps/api/src/routers/security_compression.py`): Exposed `/v1/tenants/{tenantId}/context/compress`, `/v1/tenants/{tenantId}/security/encrypt`, and `/v1/tenants/{tenantId}/security/decrypt` endpoints.
- **Unit Test Suite** (`apps/api/tests/test_context_compression_encryption.py`): Created unit tests verifying token trimming, key facts retention, AES-256 roundtrip encryption across tenants, and router endpoints (467 total unit tests passing).

---

### [Completed] Milestone 50: Online Production Hallucination Tracing (v0.48.0)

**Objective:** Transition evaluation from offline batch dataset runs to continuous, real-time online monitoring on live production API traffic.

**Delivered Capabilities:**
- **Evaluation Configuration Settings** (`apps/api/src/domain/abstractions/config.py`): Added `EvaluationSettings` model (`enable_online_tracing`, `online_sample_rate`, `hallucination_threshold`) to `TenantConfiguration`.
- **Online Evaluations Database Model & RLS** (`apps/api/src/adapters/database/models.py`, `setup.py`): Created `OnlineEvaluationDb` model (`online_evaluations` table) with Row-Level Security isolation.
- **Continuous Evaluator Service** (`apps/api/src/domain/evaluation/online_evaluator.py`): Built `OnlineHallucinationEvaluator` for asynchronous claim extraction, `faithfulness`, `context_precision`, and `hallucination_index` scoring with SLA alert triggers.
- **Repository Persistence & Aggregation** (`apps/api/src/adapters/database/evaluation_repository.py`): Implemented `SqlOnlineEvaluationRepository` with log persistence, paginated log retrieval, and real-time tenant summary calculations.
- **FastAPI Admin Endpoints** (`apps/api/src/routers/admin.py`): Exposed `GET /v1/admin/tenants/{tenantId}/evaluation/online/summary` and `GET /v1/admin/tenants/{tenantId}/evaluation/online/logs`.
- **Unit Test Suite** (`apps/api/tests/test_online_evaluator.py`): Created unit tests verifying online scoring, non-blocking background dispatch, database storage, threshold alert triggers, and FastAPI summary endpoints (471 total unit tests passing).

---

### [Completed] Milestone 51: Compliance & Data Sovereignty Lifecycle (GDPR/SOC2) (v0.49.0)

**Objective:** Automate data retention, PII anonymization, and GDPR right-to-be-forgotten vector deletion.

**Delivered Capabilities:**
- **Zero-Footprint Inline PII Anonymizer** (`apps/api/src/domain/compliance/pii_anonymizer.py`): Built `PiiAnonymizer` masking SSNs, credit cards, emails, phone numbers, and custom regex tokens before text chunking & vector embedding generation.
- **Cascading Hard Purge Engine** (`apps/api/src/domain/compliance/purge_service.py`): Implemented `HardPurgeService` executing multi-tier hard deletions cascading across PostgreSQL relational tables (`documents`, `document_chunks`), multi-vector stores (`vector_records_1536`, `3072`), Redis semantic cache, Neo4j/Pg graph triples, and physical file storage.
- **SLA Data Retention Worker** (`apps/api/src/domain/compliance/retention_worker.py`): Built `RetentionWorker` scanning document creation dates against tenant retention SLAs (`data_retention_days`) to auto-destroy expired records.
- **FastAPI Admin Compliance Endpoints** (`apps/api/src/routers/admin.py`): Exposed `DELETE /v1/admin/tenants/{tenantId}/compliance/documents/{documentId}`, `POST /v1/admin/tenants/{tenantId}/compliance/forget`, `POST /v1/admin/tenants/{tenantId}/compliance/anonymize`, and `POST /v1/admin/tenants/{tenantId}/compliance/run-retention-purge`.
- **Unit Test Suite** (`apps/api/tests/test_compliance.py`): Created unit tests verifying PII token masking, hard deletion cascades, retention schedulers, and admin endpoints (475 total unit tests passing).

---

### [Completed] Milestone 52: Commercial Payments & Deposit Billing (v0.50.0)

**Objective:** Integrate Stripe, Razorpay, and PhonePe payment gateways for client deposit collection, automated quota management, and subscription state tracking.

**Delivered Capabilities:**
- **Cryptographic Webhook Receivers** (`apps/api/src/routers/payments.py`): Built `/v1/payments/webhooks/{provider}` endpoints for Stripe, Razorpay, and PhonePe with HMAC signature verification.
- **Audit-Proof Payment Ledger Model & RLS** (`apps/api/src/adapters/database/models.py`, `setup.py`): Created `PaymentTransactionDb` (`payment_transactions` table) with Row-Level Security isolation.
- **Payment Transaction Repository** (`apps/api/src/adapters/database/payment_repository.py`): Implemented `SqlPaymentRepository` for transaction persistence and paginated ledger history queries.
- **Automated Tenant Quota Provisioning** (`apps/api/src/domain/billing/payment_service.py`): Built `PaymentService` auto-upgrading tenant storage document limits, token rate limits, and request quotas (`TenantQuotaSettings`) upon successful billing webhook notifications.
- **Checkout Link Generator & Admin Ledger API**: Exposed `POST /v1/payments/checkout-session` and `GET /v1/admin/tenants/{tenantId}/payments/ledger`.
- **Unit Test Suite** (`apps/api/tests/test_payments.py`): Created unit tests verifying webhook signature validation, ledger storage, automatic quota upgrades, checkout generation, and admin endpoints (479 total unit tests passing).

---

### [Completed] Milestone 53: Enterprise n8n & Workflow Automation Integration (v0.51.0)

**Objective:** Integrate self-hosted n8n automation connectors and webhook triggers into the Retriever platform for automated inbound document ingestion (Gmail, Google Drive, Notion) and outbound event triggers (Slack, WhatsApp, Zendesk).

**Delivered Capabilities:**
- **Outbound Webhook Dispatcher** (`apps/api/src/domain/workflow/n8n_dispatcher.py`): Built `N8nWebhookDispatcher` domain service dispatching event triggers (chat feedback, escalations) to external n8n HTTP webhooks.
- **Inbound Auto-Ingest Webhook Endpoint** (`apps/api/src/routers/workflow.py`): Exposed `POST /v1/tenants/{tenantId}/ingest/webhook` accepting text/markdown or base64 PDF/Docx payloads from n8n workflows with inline PII anonymization.
- **Outbound Webhook Configuration API**: Exposed `POST /v1/admin/tenants/{tenantId}/workflow/webhooks` to configure active n8n target URLs per tenant.
- **n8n OpenAPI Spec Generator API**: Exposed `GET /v1/workflow/n8n-spec` providing OpenAPI 3.0.3 specifications for 1-click import into n8n HTTP Nodes.
- **Unit Test Suite** (`apps/api/tests/test_workflow_n8n.py`): Created unit tests verifying inbound text/file ingestion, PII redaction pass-through, outbound event dispatching, and OpenAPI schema generation (483 total unit tests passing).

---

### [Completed] Milestone 54: Enforced Parent-Child Hydration & Exact Citation Grounding (v0.52.0)

**Objective:** Maximize context quality with small-chunk search precision while enforcing strict string-span citation verification.

**Target Deliverables:**
- **Automated Parent-Child Ingestion Default**: Automatically partition ingested files into child (150-token) and parent (800-token) records, dynamically hydrating parent context in `PromptBuilder`.
- **Exact String-Span Citation Matcher** (`apps/api/src/domain/inference/citation_validator.py`): Enforce exact substring offset matching between generated quotes and context chunks, flagging ungrounded claims with visual UI warnings.

---

### [Completed] Milestone 55: Embeddable Chat Widget & Public JavaScript Client (v0.53.0)

**Objective:** Deliver zero-dependency embeddable chat widget script and full-featured client SDK.

**Target Deliverables:**
- **Standalone Embed Widget** (`widget.js`): Zero-dependency embeddable script for client websites with 1-line script tag integration.
- **Client SDK Expansion** (`@prat3010/retriever-client-js` & `Prateek_website/src/lib/rag-client.ts`): Expose client methods for streaming RAG sessions, document downloads, feedback, and telemetry inspection.

---

### [Completed] Milestone 63: Multimodal Discovery & Dogfooding Tenant (`prateeq_scoping`)

**Objective:** Onboard authentic dogfooding tenant with engineering rate cards and embed widget chatbox for live scoping.

**Target Deliverables:**
- **Authentic Scoping Tenant**: Dedicated `prateeq_scoping` tenant on Retriever with catalog documents and system prompt.
- **Scoping AI Prompt & RFP Dropzone**: Multimodal natural language intent bar (`AiScopingPromptBar.tsx`) and PDF RFP dropzone (`RfpUploaderModal.tsx`).

---

### [Completed] Milestone 64: Productized Architecture Cart Drawer & GraphRAG Upsells

**Objective:** Build slide-over cart drawer with volume bundle discounts and GraphRAG technology upsell recommendations.

**Target Deliverables:**
- **Slide-Over Cart Drawer** (`ArchitectureCartDrawer.tsx`): Interactive line-item cart with 5-second undo toast.
- **Volume Bundle Meter & GraphRAG Upsells**: 5–10% automatic bundle tier discounts and compatibility-based add-on recommendations.

---

### [Completed] Milestone 65: Live Visual Architecture Topology Map & Cascade Solver

**Objective:** Interactive SVG/Canvas node visualizer and dynamic GraphRAG DAG dependency cascade solver modal.

**Target Deliverables:**
- **Topology Visualizer** (`ArchitectureTopologyMap.tsx`): Multi-tier node flow visualizer (Client $\rightarrow$ Edge $\rightarrow$ Services $\rightarrow$ Data $\rightarrow$ Integrations).
- **Dependency Cascade Modal** (`DependencyCascadeModal.tsx`): Active dependency disconnect warning and resolution dialog.

---

### [Completed] Milestone 66: Terminal Scoping CLI (`/terminal`) & Mobile QR Checkout

**Objective:** CTO/developer CLI scoping commands and dynamic ASCII QR code mobile checkout.

**Target Deliverables:**
- **Terminal Scoping CLI** (`terminalScoping.ts`): Commands for `scope new`, `scope analyze`, `cart checkout`.
- **ASCII & Image QR Code Generator** (`/api/terminal/qrcode`): Mobile QR code generation for instant deposit checkout.

---

### [Completed] Milestone 67: Dashboard Decomposition, Workspace Bridge, 7-Day Trial & SOW Freeze

**Objective:** Supabase Auth PKCE handoff, dedicated 7-day trial tenant auto-provisioning, embedded CPQ customizer, and SHA-256 SOW freezing.

**Target Deliverables:**
- **7-Day Trial Auto-Provisioning**: Dedicated `tn_client_<uuid>` tenant on Retriever with immutable baseline SOW document (`is_system: true`).
- **Embedded Dashboard CPQ & Escrow**: Full CPQ customizer in `/dashboard`, 50% deposit capture, and Phase 2 Change Orders.

---

### [Completed] Milestone 68: Unified Persistent Copilot (Retriever RAG Stream) & Sprint Feeds

**Objective:** Connect dashboard copilot to private Retriever tenant chat session and stream live git commits and staging previews.

**Target Deliverables:**
- **Persistent RAG Project Copilot** (`ClientProjectCopilot.tsx`): Real-time chat session grounded in client RFP and sprint milestones.
- **Git CI/CD Feeds & Staging Previews**: 1-click GitHub repo scaffolding and live commit feed in `/dashboard`.
- **Multi-Format Proposal Suite 2.0**: 1-Page Executive Pitch vs 3-Page Master Statement of Work PDF.
- **Post-Launch SLA Cockpit**: 5-minute uptime health pings and automated monthly SLA compliance report PDF.

---

### [Completed] Milestone 69: Pre-Chunk Contextual Retrieval Ingestion Engine (v0.54.0)

**Objective:** Eliminate ambiguous standalone chunks by pre-pending document-level context during ingestion (Anthropic Contextual Retrieval method).

**Target Deliverables:**
- **Contextual Ingestion Worker** (`apps/api/src/adapters/cognitive/contextual_header_adapter.py`, `workers/src/tasks/__init__.py`): Async Celery task using a fast LLM (`gemini-1.5-flash` / `claude-3-5-haiku`) to generate 50–80 word document context headers for every chunk prior to vector embedding generation.
- **Accuracy Boost**: Reduces top-20 retrieval failure rates by up to $49\%$.

---

### [Completed] Milestone 70: Late-Interaction (ColBERT) Token-Level Reranker (v0.55.0)

**Objective:** Surface nuanced technical terms, serial numbers, and code identifiers where standard bi-encoders fail using token-level MaxSim late interaction.

**Target Deliverables:**
- **ColBERT Token-Level Reranker Adapter** (`apps/api/src/domain/retrieval/colbert_engine.py`, `apps/api/src/adapters/cognitive/local_reranker_adapter.py`, `apps/api/src/adapters/cognitive/tei_reranker_adapter.py`): Implement token-level MaxSim reranking over top-50 candidates.
- **Flexible Engine Support**: Support local Text-Embeddings-Inference (TEI) containers and sub-15ms local fallback.

---

### [Completed] Milestone 71: Corrective RAG (CRAG) & Agentic Reflection Loop (v0.56.0)

**Objective:** Enable autonomous self-reflection and query correction.

**Target Deliverables:**
- **CRAG Reflection Engine** (`apps/api/src/domain/retrieval/corrective_retrieval_service.py`, `document_refiner.py`, `corrective_retrieval_adapter.py`): Evaluate candidate retrieval confidence scores before LLM generation.
- **Autonomous Fallback**: If score drops below threshold, automatically execute query reformulations or web search fallback before generating response.

---

### [Completed] Milestone 72: Interactive RLM Python REPL Sandbox Studio (v0.57.0)

**Objective:** Productize Recursive Language Models into an interactive developer workspace studio.

**Target Deliverables:**
- **RLM Workspace Studio Tab** (`Prateek_website/src/app/rag/app/`, `RlmStudioPanel.tsx`): Dedicated UI tab (`/rag/app/rlm`) where users can watch the AI write and execute Python code to recursively inspect, filter, and summarize document vaults using `/v1/rlm`.

---

### [Active Next] Milestone 73: GraphRAG Leiden Community Detection & Closed-Loop Self-Tuning (v0.58.0)

**Objective:** Unlock macro-level dataset reasoning and automated quality self-tuning based on continuous production evaluations.

**Target Deliverables:**
- **Hierarchical Leiden Community Extraction** (`apps/api/src/domain/graph/`): Construct global entity graphs, execute Leiden community clustering, and pre-generate macro hierarchical summaries.
- **Closed-Loop Telemetry Self-Tuning**: Connect M50 online evaluation telemetry (`OnlineHallucinationEvaluator`) directly to `config_service` to automatically calibrate `reranking_threshold`, `top_k`, and `rrf_k` values based on continuous Ragas scoring.

---

### [Planned] Milestone 74: Semantic NLI & SLM-as-a-Judge Online Hallucination Engine (v0.59.0)

**Objective:** Replace naive keyword overlap checks with semantic Natural Language Inference (NLI) and async Small Language Model judges to eliminate false-positive faithfulness scores.

**Target Deliverables:**
- **DeBERTa NLI Cross-Encoder Adapter** (`apps/api/src/adapters/cognitive/nli_evaluator.py`): Classify claim-premise pairs using `cross-encoder/nli-deberta-v3-small` with calibrated entailment probabilities.
- **Async SLM Evaluation Task** (`workers/src/tasks/evaluation_tasks.py`): Celery task evaluating full generated responses against context using local Ollama (`qwen2.5:3b` / `llama3.2:3b`) with structured reasoning and span localization.
- **Calibrated Hallucination Alerting**: Update `OnlineHallucinationEvaluator` to compute real-time Hallucination Index from NLI contradiction scores.

---

### [Planned] Milestone 75: Full-Stack OpenTelemetry Auto-Instrumentation & Distributed Trace Graph (v0.60.0)

**Objective:** Provide end-to-end distributed tracing across database queries, vector similarity operations, outbound LLM APIs, and async Celery workers.

**Target Deliverables:**
- **SQLAlchemy Auto-Instrumentation** (`apps/api/src/adapters/telemetry/setup.py`): Instrument SQLAlchemy engine to trace SQL execution, pgvector similarity lookup durations, and transaction locks.
- **HTTPX Client Instrumentation**: Trace latency of outbound calls to Ollama, Gemini, Groq, Tavily, and Resend.
- **Celery Worker Tracing**: Instrument Celery background workers to trace ingestion pipelines, OCR parsing, and async evaluation tasks.
- **W3C TraceContext Propagation**: Propagate `traceparent` headers across Next.js proxy $\rightarrow$ FastAPI Gateway $\rightarrow$ Celery workers.

---

### [Planned] Milestone 76: Real-Time Telemetry Live Aggregations & SLA Webhook Alerting Engine (v0.61.0)

**Objective:** Transition telemetry endpoints from static fallbacks to live multi-tenant database aggregations with automated incident webhooks.

**Target Deliverables:**
- **Live Database Aggregations** (`apps/api/src/routers/admin.py`, `Prateek_website/src/app/api/rag/telemetry/route.ts`): Stream live query metrics from `inference_logs` and `online_evaluations`.
- **Multi-Channel Alert Dispatcher** (`apps/api/src/domain/telemetry/alert_service.py`): Push alerts to Slack, Discord, custom webhooks, or Resend email upon Hallucination Index $> 30\%$, token quota $\ge 90\%$, or P99 latency spikes.

---

### [Planned] Milestone 77: Synthetic Golden Dataset Generation & Automated CI/CD Regression Gate (v0.62.0)

**Objective:** Automate continuous RAG evaluation by synthesizing benchmark datasets and enforcing PR blocking gates in CI/CD.

**Target Deliverables:**
- **Synthetic Test-Case Generator** (`apps/api/src/domain/evaluation/synthetic_dataset_generator.py`): Ingest tenant documents and auto-generate 50+ Q&A evaluation pairs with ground-truth chunk links.
- **Automated CI/CD Regression Workflow** (`.github/workflows/eval_regression.yml`, `scripts/run_eval_regression.py`): Enforce minimum quality thresholds (Faithfulness $\ge 0.90$, Answer Relevancy $\ge 0.85$, Hallucination $\le 0.10$) before merging releases.

---

### [Planned] Milestone 78: Visual Claim-by-Claim Grounding Diff & Synchronizer Observability Cockpit (v0.63.0)

**Objective:** Deliver granular visual insight into model faithfulness and integrate backend observability into the local Synchronizer desktop control center.

**Target Deliverables:**
- **Visual Claim Grounding Inspector** (`apps/web/src/components/tenant-hallucinations.tsx`, `Prateek_website/src/components/rag/ChatPanel.tsx`): Color-coded sentence grounding (green = verified, red = ungrounded) with interactive popovers linking to cited source chunks.
- **Synchronizer Analytics Tab Overhaul** (`Prateek_website/scripts/sync_tabs/analytics.py`): Embed live Retriever token usage, cost breakdowns, and active hallucination alert feeds into the desktop Streamlit synchronizer.

---

### [Planned] Milestone 79: Sparse-Dense Hybrid Engine & Contrastive LoRA Domain Adapters (v0.64.0)

**Objective:** Combine Scikit-Learn custom sparse text vectorization with PyTorch contrastive domain adapter fine-tuning for specialized legal, technical, and engineering terminology.

**Target Deliverables:**
- **Custom Sublinear TF-IDF / BM25 Vectorizer** (`packages/processing-core/`, `apps/api/src/adapters/vector/`): Scikit-Learn based sparse vectorizer preserving code symbols, camelCase/snake_case tokens, and custom stopwords for sub-millisecond sparse lookup alongside pgvector dense embeddings.
- **PyTorch Contrastive LoRA Domain Adapter** (`workers/src/tasks/adapter_worker.py`): Multi-layer projection adapter trained with PyTorch `MultipleNegativesRankingLoss` on client SOWs and technical architectures to maximize domain cluster separation.

---

### [Planned] Milestone 80: PyTorch Late-Interaction ColBERT Token-Level MaxSim Engine (v0.65.0)

**Objective:** Implement hardware-accelerated ColBERT multi-vector token reranking to capture exact technical terms, acronyms, and code identifiers without external API dependencies.

**Target Deliverables:**
- **Token-Level Multi-Vector Embedding** (`apps/api/src/adapters/reranker/colbert_adapter.py`): PyTorch ColBERT model outputting token matrices $Q \in \mathbb{R}^{|Q| \times D}$ and $D \in \mathbb{R}^{|D| \times D}$.
- **Hardware-Accelerated MaxSim Operator**: `torch.einsum` / tensor dot-product operator running on Apple Silicon Metal Performance Shaders (`torch.device("mps")`) and Oracle VPS CUDA workers for <10ms stage-2 candidate reranking.

---

### [Planned] Milestone 81: Scikit-Learn Unsupervised Chunk Clustering & HDBSCAN Dynamic Topic Modeling (v0.66.0)

**Objective:** Automate semantic topic discovery and hierarchical community node generation across tenant document libraries.

**Target Deliverables:**
- **HDBSCAN & KMeans Chunk Clustering** (`apps/api/src/domain/clustering/topic_cluster_service.py`): Density-based unsupervised clustering on 768-dim embeddings to automatically segment documents into topic clusters without hardcoded cluster counts.
- **GraphRAG Community Node Genesis**: Automatically generate high-level topic summary nodes and link individual chunks to parent topics in the Neo4j/pgvector GraphRAG index.

---

### [Planned] Milestone 82: Scikit-Learn 2D/3D Embedding Space Projection Pipeline for SaaS Studio (v0.67.0)

**Objective:** Power an interactive 3D vector space visualizer in the SaaS Studio (`/rag/app`) using server-side dimensionality reduction.

**Target Deliverables:**
- **PCA + UMAP Projection Service** (`apps/api/src/routers/embeddings.py`): Endpoint `POST /v1/tenants/{id}/embeddings/project` reducing 768D embeddings to 3D coordinates $(x, y, z)$ with cluster centroid metadata.
- **Interactive 3D WebGL Vector Cloud** (`Prateek_website/src/components/rag/VectorVisualizer.tsx`): Three.js / Canvas interactive point cloud displaying document clusters and real-time query vector intersection.

---

### [Completed] Milestone 83: Scikit-Learn Real-Time Telemetry Anomaly Detection & Quota Abuse Guard (v0.68.0)

**Objective:** Deploy an unsupervised machine learning anomaly detection sentinel to safeguard tenant API keys and prevent scraping.

**Delivered Artifacts:**
- **Isolation Forest & Pure-NumPy Anomaly Detector** (`apps/api/src/adapters/cognitive/anomaly_detector_adapter.py`): Scikit-Learn `IsolationForest` (with `StandardScaler` and 0.05 contamination rate) and authentic pure-NumPy multivariate Mahalanobis / robust MAD distance baseline scoring multi-dimensional telemetry features (request velocity, prompt entropy, latency variance, token ratio, error rate, cost velocity).
- **Telemetry Anomaly Sentinel Domain Service** (`apps/api/src/domain/telemetry/anomaly_sentinel_service.py`): Sliding-window inference log feature aggregation, automated risk classification (LOW, MEDIUM, HIGH, CRITICAL), and factor attribution explanation synthesis.
- **Credential Quarantine & Abuse Enforcement** (`apps/api/src/adapters/database/anomaly_repository.py`, `apps/api/src/adapters/database/identity_repository.py`, `apps/api/src/adapters/telemetry/rate_limiter_dep.py`): Automated API key suspension (`status = "quarantined"`) for CRITICAL threats, dynamic Redis quarantine restriction (2 req/min), and 1-click unquarantine.
- **Database Persistence & Alembic Migration** (`telemetry_anomalies` table, migration `e2f1a3b4c5d6`): Indexed tracking of security anomaly events, scores, raw features, and resolution audits.
- **Celery Asynchronous Sentinel Task** (`workers/src/tasks/anomaly_sentinel.py`): Background task `run_telemetry_anomaly_sentinel` scanning rolling windows and triggering automatic protection.
- **Admin & Tenant REST APIs** (`apps/api/src/routers/admin.py`, `apps/api/src/routers/tenant.py`): Endpoints for listing anomalies, on-demand scans, resolving alerts, and quarantining/unquarantining credentials.
- **Incident Alerting** (`apps/api/src/domain/telemetry/alert_service.py`): Real-time Slack/Discord security webhooks on detected abuse.


---

### [Completed] Milestone 84: Scikit-Learn ML Project Effort & Sprint Delivery Timeline Regression Model (v0.69.0)

**Objective:** Predict realistic engineering sprint hours and delivery windows with statistical confidence intervals in the Scoping Lab and Client Workspace.

**Target Deliverables:**
- **Multi-Output Gradient Boosting Regressor** (`Prateek_website/src/lib/pricing.ts`, `/api/scoping/estimate-timeline`): Model trained on historical CPQ scoping configurations predicting sprint hours ($P_{50} / P_{90}$), calendar delivery ranges, and complexity index.
- **Dynamic Scoping Timeline Indicator**: Live interactive sprint confidence bar embedded in the Cart Drawer (`/scoping`) and Client Workspace (`/dashboard`).

---

### [Completed] Milestone 85: Scikit-Learn & PyTorch Visitor Persona & Lead Conversion Propensity Classifier (v0.70.0)

**Objective:** Segment anonymous visitors into dynamic personas and score cold outreach prospects by conversion probability.

**Target Deliverables:**
- **Zero-Cookie Visitor Clustering** (`Prateek_website/src/proxy.ts`, `scripts/sync_tabs/analytics.py`): Scikit-Learn `KMeans` clustering on GDPR-compliant telemetry to identify Enterprise Clients, SaaS Buyers, Recruiters, and Dev Peers, tailoring dynamic UI CTAs.
- **Supervised Lead Scoring Classifier** (`Prateek_website/src/app/admin/`, `scripts/sync_tabs/clients.py`): Logistic Regression / Random Forest model predicting reply and conversion probability for automated outreach campaigns.

---

### [Active Next] Milestone 86: Edge AI Token Shield, DDoS Defense & Upstash Redis Rate Limiting (v0.71.0)

**Objective:** Protect public inference endpoints from API token drain and provide resilient auto-reconnect streaming for mobile clients.

**Target Deliverables:**
- **Edge Token-Bucket Rate Limiter**: Upstash Redis sliding window limiter across `/api/scoping/parse-intent`, `/api/scoping/parse-rfp`, and `/api/client/copilot`.
- **Resilient SSE Reconnection Protocol**: `Last-Event-ID` auto-reconnect stream buffer eliminating severed responses during Wi-Fi/5G switches.

---

### [Completed] Milestone 86.5: Platform Capabilities & Active Batteries Observability Cockpit (v0.71.1)

**Objective:** Build unified, real-time observability and control for platform retrieval, machine learning, and defense batteries across backend endpoints and admin dashboards.

**Delivered:**
- **Platform Batteries Domain Abstraction & Registry (`apps/api/src/domain/batteries/`)**: Assembled unified inventory of platform batteries (expanded from initial 12 to 14 batteries: BM25, pgvector HNSW, ColBERT MaxSim, Docling OCR, RLM Python REPL, GraphRAG HDBSCAN, Isolation Forest Anomaly Sentinel, Quantile Effort Regressor, Zero-Cookie Persona Clusterer, Token Shield, LlamaGuard 3, LongLLMLingua, NeMo Conversational Guardrails, and Neo4j Cypher Graph Engine with hardware sensing).
- **Admin & Tenant Inspection Endpoints**: `GET /v1/admin/platform/batteries` (Admin Master Key gated) and `GET /v1/tenants/{tenantId}/batteries` exposing live engine statuses, algorithmic foundations, latency profiles, and active hyperparameters.
- **Admin Dashboard Visual Cockpit (`apps/web` at `/batteries`)**: High-tech operational command center with real-time KPI metrics, category filter pills, pulsing health indicators, and engine parameter tags.
- **Automated Verification**: Pytest suite `apps/api/tests/test_batteries.py` asserting inventory completeness, category coverage, dynamic hardware sensing overrides, and strict Hexagonal boundary isolation.

---

### [Completed] Milestone 87: Automated Cloud Database Snapshots, S3/R2 WAL Archival & PITR Recovery (v0.72.0)

**Objective:** Ensure enterprise disaster recovery with encrypted daily cloud backups, cryptographic integrity validation, and point-in-time recovery.

**Delivered:**
- **Pooler-Safe Encrypted Snapshots (`apps/api/src/adapters/backup/cloud_backup_adapter.py`)**: Transaction-pooler safe logical database streaming, gzip compression, AES-256 GCM envelope encryption, and SHA-256 manifest generation.
- **Cloud Archival & Off-Site Storage (`S3Storage`)**: Direct streaming upload to Cloudflare R2 / AWS S3 with automated retention policy cleanup (14-day rotation).
- **Point-in-Time Recovery (PITR) & Restore Engine (`apps/api/src/adapters/backup/cloud_restore_adapter.py`)**: Cryptographic SHA-256 integrity checks, topological foreign key DAG traversal (`tenants` -> `users` -> `documents` -> `vector_records`), and zero-downtime `--dry-run` simulation mode.
- **Single-Command CLI Suite**: `scripts/db_snapshot.py` and `scripts/db_restore.py` for systemd timers and immediate disaster recovery.
- **Admin Dashboard Integration (`apps/web` `/system-data`)**: Real-time snapshot inventory, encrypted size meters, on-demand backup trigger button, and 1-click dry-run audit inspection.
- **Automated Verification**: Pytest suite `apps/api/tests/test_backup_restore.py` covering roundtrip encryption/decryption, tampered archive rejection, REST APIs, and Hexagonal boundaries.

---

### [Completed] Milestone 88: Enterprise Compliance Vault: Presidio PII Redaction & GDPR Cryptographic Wipe (v0.73.0)

**Objective:** Provide SOC 2, HIPAA, and GDPR compliance with automated PII redaction and cryptographic deletion certificates.

**Delivered:**
- **Context-Aware Enterprise PII Redactor (`apps/api/src/domain/compliance/pii_anonymizer.py`)**: Multi-domain entity recognition with Luhn algorithm checksum validation for credit cards, IBAN, SSNs, Aadhaar, PAN, Passports, Secrets/API Keys (`AKIA...`, `sk-...`, `ghp_...`), HIPAA Medical Record Numbers, IPv4/IPv6, and emails.
- **Advanced Masking Strategies**: Direct category tag redaction (`[REDACTED_TYPE]`), synthetic masking (`***-**-1234`), and deterministic **Cryptographic Pseudonymization** (`[PSEUDONYM:sha256[:8]]`) for consistent anonymized multi-doc search.
- **Cryptographic Compliance Deletion Certificate Authority (`src/domain/compliance/certificate_service.py`)**: Issues tamper-evident, HMAC-SHA256 signed GDPR Article 17 Erasure Certificates proving permanent data destruction across PostgreSQL, vector indexes, Redis cache, and object storage.
- **Auditor Verification REST API**: `GET /v1/compliance/verify/{certificateId}` enabling third-party auditors to cryptographically verify signature authenticity against the canonical payload.
- **Admin Dashboard Compliance Cockpit (`apps/web/src/components/tenant-compliance.tsx`)**: Real-time category domain toggles, live interactive sanitizer sandbox, and an Auditor Erasure Certificate ledger with 1-click JSON download and live verification.
- **Automated Verification**: Pytest suite `apps/api/tests/test_compliance_vault.py` covering Luhn validation, API key scrubbing, cryptographic HMAC signing, tamper detection, and Hexagonal boundaries.

---

### [Completed] Milestone 89: Geo-Distributed Multi-Region Edge Vector Read-Replicas (v0.74.0)

**Objective:** Reduce cross-continental vector search and read query latency from ~180ms down to sub-30ms using Geo-Distributed Edge Routing and CQRS read-replica connection pooling.

**Delivered:**
- **Geo-IP Edge Routing Service (`src/domain/routing/edge_router_service.py`)**: Pure Python domain service mapping ISO country codes (Americas, Europe, Asia-Pacific) to topologically optimal regional endpoints (`us-east`, `eu-central`, `ap-south`) with empirical latency modeling and $>85\%$ latency reduction calculation.
- **CQRS Read-Replica Connection Pooler (`src/adapters/database/read_replica_adapter.py`)**: Multi-region database engine pooler executing heavy vector lookups and read queries on regional replicas while ensuring mutations strictly target the Primary Master. Includes zero-cost, zero-config automatic primary master fallback.
- **Continuous Latency & Health Prober**: Non-blocking RTT health checker measuring live roundtrip milliseconds per regional node.
- **Admin REST API Endpoints (`src/routers/admin.py`)**: `GET /v1/admin/platform/regions`, `POST /v1/admin/platform/regions/probe`, `GET /v1/admin/platform/regions/preview`.
- **Command Center Dashboard UI (`apps/web/src/app/(dashboard)/system-data/page.tsx`)**: 3-Region status cards, live RTT latency badges, 1-click latency probe trigger, and an interactive Geo-IP routing simulator for US, UK, Germany, India, Japan, Australia, and Brazil.
- **Automated Verification**: Pytest suite `apps/api/tests/test_edge_router.py` (7/7 passed) covering Geo-IP resolution, circuit breakers, fallback assurance, REST endpoints, and Hexagonal boundaries.

---

### [Completed] Milestone 90: Universal Ecosystem Plugins (Slack Bot, Chrome Extension & 2-Way GDrive Sync) (v0.75.0)

**Objective:** Embed Retriever directly into everyday client workflows across Slack, Chromium browsers, and 2-way Cloud Storage (Google Drive & Notion), completing Phase K.

**Delivered:**
- **Authentic Google Drive v3 REST Connector (`src/domain/connectors/google_drive.py`)**: Real HTTP-backed connector querying target Google Drive folders, automatically exporting Google Docs to clean plain text, and tracking differential changes via `modifiedTime` and MD5 checksums.
- **Authentic Notion Knowledge Base Connector (`src/domain/connectors/notion.py`)**: Real Notion REST API v1 connector traversing database pages and block children trees into GitHub Flavored Markdown with `last_edited_time` differential synchronization.
- **Retired Mock Connectors (`src/domain/connectors/registry.py`)**: Permanently replaced mock implementations with authentic HTTP-backed connector strategies conforming to zero-toy utility invariants.
- **Native Slack Workspace Bot Service (`src/domain/integrations/slack_service.py` & `src/routers/integrations.py`)**: HMAC-SHA256 signature verification, replay attack prevention, and dynamic Slack Block Kit message composer with grounded citation pills, latency metadata, and interactive 👍/👎 feedback buttons for `/ask-retriever <query>`.
- **Direct JSON Raw Document Ingestion API (`POST /v1/tenants/{tenantId}/documents/raw`)**: Fast-path text and markdown ingestion route supporting Chrome extension clippers and Slack thread archiving.
- **1-Click Chrome Ingestion Extension (Manifest V3) (`apps/extension/`)**: Production-ready Chromium extension with reader-mode DOM text extraction, tenant credentials storage, and direct 1-click `.zip` bundle download endpoint (`GET /v1/integrations/extension/bundle`).
- **Command Center & Studio Integrations Hub**: Live Integrations management page in Admin Dashboard (`/integrations`) and SaaS App Studio (`/rag/app` Integrations tab) with test simulators and 1-click copy buttons.
- **Operational Runbook**: Published comprehensive operations guide at `docs/runbooks/ECOSYSTEM_PLUGINS_AND_INTEGRATIONS.md`.
- **Automated Verification**: Pytest suite `apps/api/tests/test_ecosystem_plugins.py` (7/7 passed) covering Slack signature security, Block Kit layout, connector discovery, markdown parsing, bundle download, and Hexagonal boundaries.

---

### [Completed] Milestone 91: LangGraph Cyclic Agentic Orchestration & Human-in-the-Loop (HITL) State Engine (v0.76.0)

**Objective:** Upgrade linear agent routing to stateful cyclic computation graphs with persistent checkpoints and human approval nodes.

**Delivered:**
- **Stateful Cyclic Agent Graphs (`src/adapters/cognitive/langgraph_orchestrator.py`)**: Replaced linear chain execution with compiled LangGraph `StateGraph` and resilient cyclic reasoning loops (`reasoner` $\rightarrow$ `tool_executor` $\rightarrow$ `reasoner` $\rightarrow$ `synthesizer`).
- **Persistent State Checkpoints (`SqlAgentCheckpointRepository` & `agent_checkpoints`)**: PostgreSQL JSONB state checkpointer with strict `tenant_id` isolation, enabling multi-agent threads to pause, resume, and branch across client sessions.
- **Human-in-the-Loop (HITL) Gateways**: Execution pauses at `hitl_gate` before triggering sensitive actions (`document_delete`, `tenant_prompt_update`, `api_key_revoke`), emitting structured approval events to the frontend.
- **Time-Travel Debugging & Rollback Endpoints**: `GET /v1/tenants/{tenantId}/agentic/threads/{threadId}/history` and `POST /v1/tenants/{tenantId}/agentic/threads/{threadId}/rollback` with forward step pruning and state restoration.
- **Dual-Surface Frontend Studios**:
  - **Retriever Admin Dashboard** (`/orchestration`): Live execution trace, toolbox filter, HITL intervention card, and checkpoint history scrubber.
  - **Retriever SaaS App Studio** (`/rag/app`): Integrated "Agent Studio" tab conforming to Design System 2.0 (Azure & Noir) with `<Portal>`-safe approval modals.
- **Operational Runbook**: Comprehensive operations and troubleshooting guide at `docs/runbooks/RUNBOOK_LANGGRAPH_AGENTIC_ORCHESTRATION.md`.
- **Automated Verification**: Pytest suite `apps/api/tests/test_agentic_langgraph.py` asserting safe loops, HITL approval/rejection handling, time-travel rollback, multi-tenant isolation, and Hexagonal architecture boundaries.

---

### [Completed] Milestone 92: DSPy Declarative Prompt Compilation & Algorithmic Self-Optimization Pipeline (v0.77.0)

**Objective:** Replace brittle prompt engineering with declarative DSPy signatures, automated metric-driven teleprompters, and versioned hot-activation.

**Key Deliverables:**
- **Declarative Signatures & Domain Protocols (`src/domain/inference/dspy_abstractions.py`)**: `FewShotDemonstration`, `CompiledPromptProgram`, `DSPyCompilerProtocol`, `CompiledPromptRepositoryProtocol`. Strictly conforms to Hexagonal boundary (0 external framework imports).
- **Teleprompter Optimization Engine (`src/adapters/cognitive/dspy_compiler_adapter.py`)**: Authentic implementation of `BootstrapFewShot`, `MIPROv2`, and `RandomSearch` with composite evaluation metric (grounding + faithfulness + token recall).
- **PostgreSQL Persistence & Hot Activation (`src/adapters/database/compiled_prompt_repository.py`)**: `compiled_prompt_programs` table with RLS tenant isolation, cached active program, and atomic 1-click swap.
- **Dynamic PromptBuilder Injection (`src/domain/inference/prompt_builder.py`)**: Seamlessly injects active compiled instructions and formatted few-shot exemplars into live inference queries with fallback to default string templates.
- **Tenant REST APIs (`src/routers/prompts.py`)**: Mounted at `/v1/tenants/{tenantId}/prompts` (`/compile`, `/compiled`, `/compiled/active`, `/activate`, `/deactivate`, `/delete`).
- **Retriever Web & SaaS Studio Dashboards**: Cockpit UI with score comparison cards, exemplar drawers, and production hot-swaps in `retriever/apps/web` and `Prateek_website/src/components/rag/PromptOptimizationPanel.tsx`.
- **Comprehensive Verification**: 100% test coverage with automated Pytest and Vitest test suites.

---

### [Completed] Milestone 93: Enterprise LLM Gateway & Multi-Model Smart Router (LiteLLM Architecture) (v0.78.0)

**Objective:** Provide unified multi-provider proxying with dynamic fallback cascades, cooldown circuit breakers, and virtual tenant quota management.

**Delivered Features:**
- **Hexagonal Domain Abstractions (`src/domain/abstractions/gateway.py`)**: Pure domain models (`GatewayModelInfo`, `ModelRoutingConfig`, `VirtualTenantBudget`, `BudgetExceededError`, `GatewayRouterProtocol`, `BudgetRepositoryProtocol`) and `GatewaySettings` on `TenantConfiguration`.
- **Smart Gateway Router Adapter (`src/adapters/cognitive/gateway_router.py`)**: Universal provider routing across 100+ models with dynamic fallback cascade ($\text{Primary} \to \text{Secondary} \to \text{Local Free Model}$), cooldown circuit breakers on 429/5xx, and latency probing.
- **Virtual Tenant Budget Ledger (`src/adapters/database/budget_repository.py`)**: Aggregated spend tracking from `InferenceLogDb` (with SQLAlchemy token synonyms) supporting pre-flight enforcement (`warn_only`, `block` returning HTTP 402, and `downgrade_free_model` to local Ollama).
- **Inference Orchestrator Integration (`src/domain/inference/orchestrator.py`)**: Automatic pre-flight budget checks on `generate` and `generate_stream` with model prefix-normalized pricing lookup.
- **REST APIs (`src/routers/gateway.py`)**: Mounted at `/v1/gateway/models`, `/v1/gateway/probe`, and `/v1/tenants/{tenantId}/gateway` (`/routes`, `/budget`).
- **Retriever Admin Dashboard (`retriever/apps/web`)**: `/gateway` cockpit for model cascade configuration, live latency pings, and tenant budget management.
- **SaaS App Studio (`Prateek_website`)**: Interactive `GatewayPanel.tsx` in `/rag/app` with Design System 2.0 aesthetics and real-time budget attribution.
- **Comprehensive Verification**: 100% test coverage with automated Pytest, Vitest, and Hexagonal boundary suites.

---

### [Completed] Milestone 94: NVIDIA NeMo Guardrails & Multi-Turn Conversational Safety Rails (v0.79.0)

**Objective:** Enforce conversational safety, factual grounding, and topical scope limits via programmable Colang rails.

**Deliverables:**
- **NVIDIA NeMo Guardrails Integration**: Colang `.co` flow definitions controlling dialogue direction, factual topic grounding, and preventing jailbreaks / prompt injection.
- **Multi-Turn Scope Anchoring**: Conversational constraints ensuring LLM outputs stay strictly within tenant-defined business domain.
- **Sub-20ms Fast-Path Input Rails**: Asynchronous input verification running concurrently with vector embedding generation.
- **Post-Inference Factual Grounding**: Automated claim entailment verification cross-checking generated responses against retrieved context chunks.
- **Platform Battery #13**: Registered in `BatteryService` catalog under `SAFETY_DEFENSE`.
- **SaaS Studio Guardrails Panel**: Full-featured UI panel in `/rag/app` with live Colang flow editor, preset templates, real-time safety sandbox, and audit telemetry stream.
- **Documentation & Conformance**: Complete REST API spec, Cognitive Deep-Dive, Runbook, ADR-016, and 100% passing tests (17 unit & conformance tests).

---

### [Completed] Milestone 95: Durable Asynchronous Execution & Background AI Workflow Engine (v0.80.0)

**Objective:** Ensure step-level resilient durable execution for long-running multi-step AI ingestion, evaluation, and graph extraction jobs with zero waste on crash recovery.

**Delivered Capabilities:**
- **Pure Hexagonal Domain Abstractions (`durable_workflow.py`, `durable_engine.py`)**: Zero-dependency domain model defining workflow blueprints, step execution contexts, and checkpoint state machines.
- **Step-Level Memoization & Idempotent State Machine**: Checkpoint persistence in PostgreSQL (`workflow_executions`, `workflow_step_checkpoints`) protected by Postgres Row-Level Security (RLS). Completed steps replay in $<2\text{ms}$ with zero computation cost.
- **Resilient Automatic Backoff**: Exponential retry backoff on transient step failures with configurable concurrency controls.
- **Pre-Packaged Enterprise Blueprints**: `vault_bulk_ingest`, `batch_graph_extraction`, `synthetic_eval_generator`, `bulk_reembed_pipeline`.
- **Platform Battery #15**: Registered `durable_workflow_engine` in `BatteryService` catalog under `BACKGROUND_WORKFLOWS`.
- **FastAPI REST Endpoints**: Tenant endpoints under `/v1/tenants/{tenant_id}/workflows/*` and admin overview under `/v1/admin/workflows/overview`.
- **SaaS Studio & Admin Integration**: `WorkflowsPanel.tsx` in `/rag/app`, Webhook handler route in Next.js, and durable executions status in Admin Dashboard.
- **Automated Verification & Docs**: 100% passing Pytest suite (`test_durable_workflow.py`), Vitest suite, ADR-017, REST API spec, Cognitive Deep-Dive, and Runbook.

---

### [Completed] Milestone 96: Serverless Dedicated GPU Serving & Dynamic vLLM / LoRA Deployment Pipeline (Modal / BentoML) (v0.81.0)

**Objective:** Enable zero-downtime serverless GPU auto-scaling and dynamic LoRA adapter swapping on dedicated tenant models with scale-to-zero compute economics.

**Delivered Capabilities:**
- **Hexagonal Domain Abstractions**: `src/domain/abstractions/serverless_gpu.py` defining pure protocols (`ServerlessGpuClientProtocol`, `TenantLoraRegistryProtocol`) and data models with zero framework imports.
- **Scale-to-Zero Deployment Recipes**: `deploy/modal/vllm_server.py` (vLLM 0.6+, A10G GPU, persistent HuggingFace cache volume, `--enable-lora`, 300s scale-down timeout) and `deploy/bentoml/service.py` with dynamic mounting.
- **Dynamic Multi-Tenant LoRA Swapping**: Hot-swapping fine-tuned LoRA tensors via request headers without container restarts, backed by `SqlTenantLoraRepository` with Postgres RLS isolation.
- **Smart Gateway Cascade Failover**: `GatewayRouterAdapter` integration dispatching to `modal/vllm-llama-3.1-8b` and `bentoml/vllm-qwen-2.5-7b` with automatic fallback cascade.
- **Platform Battery #16**: Registered `serverless_gpu_vllm` in `BatteryService` catalog under `ML_INTELLIGENCE`.
- **FastAPI Endpoints**: Admin status/probe/cost-savings (`/v1/admin/serverless/*`) and tenant LoRA CRUD (`/v1/tenants/{tenantId}/lora-adapters/*`).
- **SaaS Studio UI Parity**: `GatewayPanel.tsx` in `/rag/app` featuring live container lifecycle, TTFT warm-boot latency probe, scale-to-zero economy card, and dynamic LoRA activator matrix with Dual-Theme Parity.
- **Automated Verification & Docs**: 100% passing Pytest suite (`test_serverless_gpu.py`, 16/16), 100% passing Vitest suite (`GatewayPanel.test.tsx`, 8/8), ADR-018, REST API spec, and Runbook.

---

### [Completed] Milestone 97: Autonomous FDE Metaprogrammer & Self-Extending Capability Studio (v0.82.0)

**Objective:** Enable the platform to autonomously analyze user requirements, recommend existing batteries, and scaffold verified, production-grade Hexagonal architecture modules with static AST boundary gates and 1-click community PR generation.

**Delivered Capabilities:**
- **Dual-Persona Solution Engine**:
  1. *For Business / Non-Tech Users:* Natural language requirement analyzer in SaaS Studio that matches requirements against the 16 native platform batteries with match scores and rationales, enabling zero-code adoption.
  2. *For Forward Deployed Engineers (FDEs):* Autonomous Hexagonal metaprogrammer that synthesizes 6 verified code slices (`domain/abstractions.py`, `domain/service.py`, `adapters/custom_adapter.py`, `routers/router.py`, `tests/test_plugin.py`, and `manifest.json`).
- **Static AST Security & Boundary Gate (`boundary_checker.py`)**: Uses standard Python `ast.parse()` to guarantee **0 framework imports** (`fastapi`, `sqlalchemy`, `celery`, `redis`, `modal`, `httpx`, etc.) in domain slices and block dangerous builtins (`exec`, `eval`) before files touch disk.
- **Git-Isolated Plugin Storage (`apps/api/src/plugins/custom/{plugin_id}/`)**: Dedicated plugin workspace directory gitignored with `.gitkeep` to prevent merge conflicts with upstream core releases.
- **Dynamic In-Process Mounting with Fault Barrier (`plugin_manager.py`)**: Dynamic discovery and mounting of `/v1/plugins/{plugin_id}/*` FastAPI routers during application lifespan. Plugin import errors are safely isolated, keeping core APIs and other tenants 100% operational.
- **Platform Battery #17**: Registered `autonomous_fde_metaprogrammer` in `BatteryService` under `SYSTEM_EXTENSIBILITY`. Custom plugins declaring `battery_service: true` dynamically appear in battery inventories.
- **1-Click Community PR Generator (`pr_generator.py`)**: Generates automated Git branch names (`feat/plugin-{plugin_id}`) and comprehensive GitHub Pull Request Markdown for seamless open-source contribution.
- **Developer CLI (`scripts/retriever_cli.py`)**: Standalone CLI for scaffolding, verifying AST boundaries, listing plugins, and triggering runtime reloads.
- **Retriever Web & SaaS Studio Dashboards**:
  - `retriever/apps/web` at `/scaffold`: Topbar, persona switcher, battery cards, AST boundary checklist, multi-file code viewer, and plugin ledger.
  - `Prateek_website` at `/rag/app`: `FeatureStudioPanel.tsx` with Design System 2.0 dual-theme aesthetics, `<MagneticButton>`, `<NumberFlow>` animated metrics, `<Portal>` modal, and 100% Vitest test coverage.
- **Comprehensive Verification**: 100% test pass rate across backend Pytest suite (`test_scaffolding.py`, 15/15) and frontend Vitest suite (`FeatureStudioPanel.test.tsx`, 9/9). ADR-019 and feature deep-dive documented.

---

### [Completed] Milestone 98: Sovereign Edge SQLite / Turso Vector Synchronization & Offline-First Edge Agent (v0.83.0)

**Phase M Inauguration:** Global Distributed Sovereign Edge & Multi-Cloud Resiliency  
**Objective:** Deliver a zero-daemon, in-process edge storage and retrieval engine combining native SQLite 3 FTS5 BM25 with binary float32 vector BLOBs, differential delta synchronization, 1-click standalone bundle exports, and Lamport clock offline mutation reconciliation.

**Delivered Capabilities:**
- **Hexagonal Domain Layer**: `abstractions/edge_sync.py` defining pure Pydantic protocols (`EdgeNode`, `EdgeSyncDelta`, `EdgeBundleManifest`, `EdgeSearchRequest`, `EdgeSearchResponse`, `EdgeMutation`, `EdgeSyncConflictResolution`) and `domain/edge_sync/` (`DeltaCalculator` with SHA-256 state hashing and `FusionRanker` with Reciprocal Rank Fusion $k=60$).
- **Embedded SQLite 3 Hybrid Storage Engine**: `sqlite_edge_engine.py` providing schema creation (`edge_chunks`, `edge_chunks_fts` with Porter tokenizer, `edge_vectors` with binary float32 BLOBs, `edge_mutation_log`), in-process NumPy cosine similarity scoring, and sub-2ms local hybrid query execution.
- **Differential Sequence Delta Generator & Standalone Bundler**: `edge_sync_adapter.py` extracting cloud pgvector records, generating watermarked sequence deltas (`since_sequence`), computing SHA-256 integrity checksums, and building 1-click standalone `.sqlite` database bundles.
- **Lamport Clock Offline Mutation Reconciler**: `edge_mutation_reconciler.py` tracking offline mutations, resolving conflicts with Last-Write-Wins (LWW) and sequence ordering, and applying changes to cloud PostgreSQL (`ChatMessageFeedbackDb`).
- **Database Models & Alembic Migration**: `EdgeNodeDb` and `EdgeSyncCheckpointDb` models with Alembic migration `k1l2m3n4o5p6_create_edge_sync_tables.py`.
- **Platform Battery #18**: Registered `sovereign_edge_sync` (`Sovereign Edge SQLite & Vector Sync Engine`) in `BatteryService` under category `EDGE_DISTRIBUTION`.
- **FastAPI Endpoints**: Mounted `/v1/admin/edge/overview` and tenant routes `/v1/tenants/{tenantId}/edge/nodes`, `/register`, `/delta`, `/bundle`, `/mutations`, `/search`.
- **Retriever Web Admin & SaaS Studio UI**:
  - `retriever/apps/web` at `/edge`: Overview metrics cards, node registry table, offline hybrid search simulator, and 1-click standalone `.sqlite` bundle exporter.
  - `Prateek_website` at `/rag/app`: `EdgeSyncPanel.tsx` with Design System 2.0 dual-theme aesthetics, `<MagneticButton>`, `@number-flow/react` animated metrics, simulated network partition switch, and 100% Vitest coverage.
- **Comprehensive Verification**: 100% test pass rate across backend Pytest suite (`test_edge_sync.py`, 13/13) and frontend Vitest suite (`EdgeSyncPanel.test.tsx`, 7/7). ADR-020 and feature guide documented.

---

### [Completed] Milestone 99: Distributed Multi-Cloud Failover & Edge Turso LibSQL Replication (v0.84.0)

**Objective:** Deliver an active-active multi-cloud failover engine spanning Oracle Cloud, AWS, Fly.io, and Cloudflare Global Anycast, with quorum consensus, monotonic generation terms, circuit-breaker EWMA latency tracking, and embedded Turso LibSQL WAL replication.

**Delivered Capabilities:**
- **Hexagonal Domain Layer**: `abstractions/multicloud.py` and `domain/multicloud/failover_controller.py` enforcing strict $>50\%$ majority quorum consensus ($Q = \lfloor N/2 \rfloor + 1 = 3/4$), monotonic generation term incrementation, and EWMA latency evaluation ($\alpha = 0.2$).
- **Embedded LibSQL & Turso Adapter**: `adapters/multicloud/turso_libsql_adapter.py` providing local SQLite read paths ($<1\text{ms}$), async WAL frame streaming, and write-through proxying to the active primary.
- **Platform Battery #19**: Registered `multicloud_failover_libsql` under `EDGE_DISTRIBUTION` in `BatteryService`.
- **FastAPI Endpoints**: `/v1/admin/multicloud/overview`, `/probe`, `/failover` and `/v1/tenants/{tenantId}/multicloud/replica/*`.
- **Operator Surfaces**: Admin Cockpit at `/multicloud` and Client SaaS App Studio at `/rag/app` (`MultiCloudPanel.tsx`) with interactive partition simulation and WAL frame tracking.
- **Comprehensive Verification**: 100% test pass rate across backend Pytest suite (`test_multicloud_failover.py`, 8/8) and frontend Vitest suite (`MultiCloudPanel.test.tsx`, 6/6). ADR-021 documented.

---

### [Completed] Milestone 100: Sovereign Edge Voice & Local Whisper / WebRTC Speech Synthesis (v0.85.0)

**Objective:** Deliver a full-duplex conversational voice engine powered by local Whisper ASR, mathematical RMS/ZCR VAD endpointing, WebRTC SDP/ICE signaling, and streaming neural speech synthesis with sub-250ms TTFAB and zero cloud audio egress.

**Delivered Capabilities:**
- **Hexagonal Domain Layer**: `abstractions/voice.py` and `domain/voice/voice_orchestrator.py` implementing full-duplex session state machines (`idle` -> `connecting` -> `listening` -> `thinking` -> `speaking`), turn lifecycle tracking, and telemetry recording.
- **Audio DSP & Local Whisper ASR**: `whisper_transcription_adapter.py` calculating RMS energy ($E_{\text{RMS}}$) and Zero-Crossing Rate (ZCR) for zero-latency speech endpointing, integrated with local quantized Whisper ASR.
- **Streaming Neural Speech Synthesis**: `speech_synthesis_adapter.py` streaming PCM16 / Opus audio chunks in $\le 180\text{ms}$ per phoneme sentence, delivering sub-250ms TTFAB across Atlas, Nova, and Echo timbres.
- **WebRTC Signaling Protocol**: `webrtc_signaling_adapter.py` orchestrating SDP offer/answer exchanges and trickle ICE candidate aggregation.
- **PostgreSQL Isolation & Migrations**: Schema revision `m1n2o3p4q5r6` creating `voice_sessions` and `voice_turns` with Supabase Row-Level Security (RLS).
- **Platform Battery #20**: Registered `sovereign_edge_voice` under `MULTIMODAL_COGNITION` in `BatteryService`.
- **FastAPI Endpoints**: `/v1/admin/voice/telemetry` and tenant endpoints `/v1/tenants/{tenantId}/voice/*` (`session`, `signal`, `transcribe`, `synthesize`, `turn`).
- **Operator Surfaces**: Admin Voice Cockpit at `/voice` and Client SaaS App Studio at `/rag/app` (`VoiceStudioPanel.tsx`) featuring real-time animated audio waveforms, VAD sensitivity slider, timbre selector, turn ledger, and offline simulation fallback.
- **Comprehensive Verification**: 100% test pass rate across backend Pytest suite (`test_edge_voice.py`, 10/10) and frontend Vitest suite (`VoiceStudioPanel.test.tsx`, 7/7). ADR-022 and feature guide documented.

---

## 7. Cross-Cutting Engineering Invariants

These are tracked across all milestones and are not individual deliverables:

| Concern | Owner | Verification |
|---|---|---|
| **RAG Quality** | All milestones | Ragas evaluation: faithfulness > 0.95, answer relevance > 0.90, context recall > 0.92. Evaluated on golden dataset after every M13+ change. |
| **Security** | All milestones | RLS enforcement verified on every new table. No secrets in logs. No hardcoded prompts. Architecture conformance tests block regressions. |
| **Backward Compatibility** | M11+ | SDK versioning follows semver. API version prefix (`/v1/`) maintained. Deprecation policy documented. |
| **Documentation** | All milestones | Every API endpoint documented. Architecture decisions recorded as ADRs. Deployment and integration guides maintained. |

---

## **Related Architecture & Cross-References**

- [Master Cross-Platform Roadmap (SSoT)](../Prateek_website/docs/UNIFIED_MASTER_ROADMAP.md)
- [Project Health & Test Status](PROJECT_STATUS.md)
- [2026 RAG Engine Architecture Blueprint](docs/RAG_2026_PRODUCT_ROADMAP.md)
- [Admin Dashboard Operational Roadmap](docs/ADMIN_DASHBOARD_ROADMAP.md)
- [Client Dashboard & SaaS Studio Roadmap](../Prateek_website/docs/CLIENT_DASHBOARD_ROADMAP.md)
- [Technical Debt Ledger](TECH_DEBT.md)
