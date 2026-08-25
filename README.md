# Retriever — Enterprise Multi-Tenant RAG Cognitive Platform

> **High-Performance Hybrid Vector Search, GraphRAG, Context Compression & Recursive Agentic Cognition.**
> 
> 📌 **Master Cross-Platform Roadmap (SSoT):** [`../Prateek_website/docs/UNIFIED_MASTER_ROADMAP.md`](../Prateek_website/docs/UNIFIED_MASTER_ROADMAP.md)  
> 📌 **Admin Dashboard Guide:** [`ADMIN_DASHBOARD_GUIDE.md`](ADMIN_DASHBOARD_GUIDE.md)  
> 📌 **Frontend Client Studio:** [`../Prateek_website/docs/24_RAG_App_Studio_PRD.md`](../Prateek_website/docs/24_RAG_App_Studio_PRD.md)

---

## 🚀 Architectural Vision & Hexagonal Core

Retriever is designed as an enterprise-grade, highly modular Retrieval-Augmented Generation (RAG) platform based on a strict **Ports and Adapters (Hexagonal)** architecture:

```text
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ CLIENT FRONTEND & CONTROL PLANE                                                        │
 │ • prateeq.in/rag & prateeq.in/rag/app (Next.js 16 App Router)                          │
 │ • Supabase Auth PKCE Session Verification & Multi-Tenant Routing                       │
 └──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                            │ REST / SSE API Streams (X-User-ID / Bearer)
                                            ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ FASTAPI APPLICATION GATEWAY (`apps/api`)                                               │
 │ • Routers: /v1/chat, /v1/search, /v1/documents, /v1/admin, /v1/auth, /v1/workflow     │
 │ • Guardrails: Llama Guard 3 Injection Filter & PII Redactor                           │
 └──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                            │
                                            ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ COGNITIVE DOMAIN CORE (`src/domain`)                                                   │
 │ • Hybrid Search (HNSW Dense + SPLADE/BM25 Sparse + RRF)                                │
 │ • GraphRAG Knowledge Graph Indexing & Neo4j/Pg Triples                                 │
 │ • Recursive Language Model (RLM) & Python REPL Sandbox (M47)                           │
 │ • Multi-Agent Generator-Critic Reflection Loops (M48)                                  │
 │ • LongLLMLingua Context Compression (M49) & Zero-Trust Envelope Encryption             │
 └──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                            │
                                            ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ INFRASTRUCTURE ADAPTERS (`src/adapters`)                                               │
 │ • Database: PostgreSQL 16 + pgvector (Row-Level Security Tenant Isolation)              │
 │ • Vector: Dynamic Partitioning (768, 1536, 3072 dims)                                  │
 │ • Storage: S3 / Cloudflare R2 presigned documents                                      │
 │ • Broker / Cache: Redis Semantic Cache & RabbitMQ Celery workers                      │
 └────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📚 Complete Technical Documentation Matrix

### 🔌 1. REST API Specifications (`docs/api/`)
| Specification | Path & Description |
|:---|:---|
| [`docs/api/auth.md`](docs/api/auth.md) | Identity resolution, Supabase Auth RS256 JWKS validation & API key hashing |
| [`docs/api/chat.md`](docs/api/chat.md) | Chat sessions, SSE token streaming, inline citations `[Source ID]` & feedback |
| [`docs/api/search.md`](docs/api/search.md) | Parallel dense/sparse hybrid search, RRF fusion & Cross-Encoder reranking |
| [`docs/api/document.md`](docs/api/document.md) | Multipart uploads, Docling layout OCR, chunking & signed download URLs |
| [`docs/api/admin.md`](docs/api/admin.md) | System-wide admin control (Tenants, API keys, Prompts, Experiments, Evaluation) |
| [`docs/api/tenant.md`](docs/api/tenant.md) | Workspace provisioning, Configuration-as-Data (CAD) & live key validation |
| [`docs/api/payments.md`](docs/api/payments.md) | Hosted checkout sessions, Stripe/Razorpay/PhonePe webhooks & payment ledger |
| [`docs/api/pricing.md`](docs/api/pricing.md) | Public SaaS pricing packages & dynamic operator pricing updates |
| [`docs/api/agentic.md`](docs/api/agentic.md) | Autonomous multi-step tool-calling execution loop & tool registry |
| [`docs/api/consensus.md`](docs/api/consensus.md) | Multi-Agent Generator vs. Critic adversarial debate & reflection loops |
| [`docs/api/rlm.md`](docs/api/rlm.md) | Recursive Language Model document synthesis & Python REPL execution |
| [`docs/api/security_compression.md`](docs/api/security_compression.md) | LongLLMLingua prompt token compression & AES-256 field encryption |
| [`docs/api/workflow.md`](docs/api/workflow.md) | n8n inbound auto-ingest webhook & outbound event dispatch |
| [`docs/api/health.md`](docs/api/health.md) | Service uptime, Kubernetes liveness/readiness probes & connection health |

### 🧠 2. Cognitive Engines & AI Subsystems (`docs/cognitive/`)
| Guide | Description |
|:---|:---|
| [`docs/cognitive/hybrid_search_and_fusion.md`](docs/cognitive/hybrid_search_and_fusion.md) | HNSW Dense + SPLADE/BM25 Sparse + RRF + Cross-Encoder Re-ranking + MMR |
| [`docs/cognitive/query_intelligence.md`](docs/cognitive/query_intelligence.md) | Query Intent Classification, HyDE Rewriting, Self-Querying & CRAG Fallbacks |
| [`docs/cognitive/chunking_and_parsing.md`](docs/cognitive/chunking_and_parsing.md) | Docling Vision OCR, Recursive Character Splitter & AST Code Chunking |
| [`docs/cognitive/graphrag.md`](docs/cognitive/graphrag.md) | Dual-engine GraphRAG (PostgreSQL Triples & Neo4j Cypher) |
| [`docs/cognitive/agentic_workflows_and_repl.md`](docs/cognitive/agentic_workflows_and_repl.md) | Autonomous ReAct loops & sandboxed Python REPL execution |
| [`docs/cognitive/consensus_and_reflection.md`](docs/cognitive/consensus_and_reflection.md) | Generator-Critic verification loops for high-stakes enterprise grounding |
| [`docs/cognitive/context_compression.md`](docs/cognitive/context_compression.md) | LongLLMLingua perplexity-based prompt token compression |
| [`docs/cognitive/guardrails_and_safety.md`](docs/cognitive/guardrails_and_safety.md) | Llama Guard 3 injection filter & zero-footprint PII redaction |
| [`docs/cognitive/evaluation_and_hallucinations.md`](docs/cognitive/evaluation_and_hallucinations.md) | Online Faithfulness scoring, RAGAS & DeepEval benchmark testbeds |

### 🏗️ 3. Infrastructure & Storage (`docs/infrastructure/`)
| Guide | Description |
|:---|:---|
| [`docs/infrastructure/database_and_schemas.md`](docs/infrastructure/database_and_schemas.md) | PostgreSQL 16 schema, 24 relational tables, pgvector HNSW & RLS isolation |
| [`docs/infrastructure/caching_and_performance.md`](docs/infrastructure/caching_and_performance.md) | Redis L1 Config Cache, L2 Semantic Cache & sliding-window rate limiters |
| [`docs/infrastructure/async_workers_and_queues.md`](docs/infrastructure/async_workers_and_queues.md) | Celery worker architecture, RabbitMQ queues & Beat periodic schedules |
| [`docs/infrastructure/storage_and_encryption.md`](docs/infrastructure/storage_and_encryption.md) | S3/R2 object storage, presigned URLs & Zero-Trust Envelope Encryption |
| [`docs/infrastructure/telemetry_and_observability.md`](docs/infrastructure/telemetry_and_observability.md) | OpenTelemetry tracing, Prometheus `/metrics` & SHA-256 chained audit logs |

### 📦 4. Integrations & Client SDKs (`docs/integrations/`)
| Guide | Description |
|:---|:---|
| [`docs/integrations/typescript_sdk.md`](docs/integrations/typescript_sdk.md) | Complete guide for `@retriever/client-js` TypeScript SDK |
| [`docs/integrations/cloudflare_proxy_worker.md`](docs/integrations/cloudflare_proxy_worker.md) | Edge proxy deployment with JWT parsing & secret key injection |
| [`docs/integrations/n8n_workflow_integration.md`](docs/integrations/n8n_workflow_integration.md) | Gmail, Notion & Google Drive ingestion pipelines via n8n |
| [`docs/integrations/commercial_billing_integration.md`](docs/integrations/commercial_billing_integration.md) | Multi-gateway billing setup (Stripe, Razorpay, PhonePe) |

---

## 🛠️ Quick Start (Local Development)

```bash
# 1. Start Postgres with pgvector, Redis & RabbitMQ
docker compose up -d

# 2. Setup Virtual Environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 3. Run Alembic Database Migrations
alembic upgrade head

# 4. Launch FastAPI Core Server
uvicorn apps.api.src.main:app --reload --port 8000
```

---

## 🧪 Automated Testing Baselines

```bash
# Run complete test suite (500+ unit tests)
pytest apps/api/tests/ -v

# Run linting & Hexagonal import boundaries verification
ruff check .
pytest apps/api/tests/test_architecture.py
```
