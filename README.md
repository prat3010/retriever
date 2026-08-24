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
 │ • Routers: /v1/chat, /v1/search, /v1/documents, /v1/admin, /v1/auth                   │
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

## 📁 Key Documentation & Navigation

| Document | Description |
|:---|:---|
| [`ROADMAP.md`](ROADMAP.md) | Backend engineering milestones (M1–M53) & implementation history |
| [`PROJECT_STATUS.md`](PROJECT_STATUS.md) | Platform health indicators, test baselines & active milestone status |
| [`docs/RAG_2026_PRODUCT_ROADMAP.md`](docs/RAG_2026_PRODUCT_ROADMAP.md) | 2026 Architecture & cognitive engine specification |
| [`docs/ADMIN_DASHBOARD_ROADMAP.md`](docs/ADMIN_DASHBOARD_ROADMAP.md) | Admin dashboard control panel architecture (`admin.rag.prateeq.in`) |
| [`ADMIN_DASHBOARD_GUIDE.md`](ADMIN_DASHBOARD_GUIDE.md) | Operator guide for tenant management, API keys, and prompt presets |
| [`DEPLOYMENT.md`](DEPLOYMENT.md) & [`ORACLE_DEPLOYMENT_REFERENCE.md`](ORACLE_DEPLOYMENT_REFERENCE.md) | Production Oracle VPS deployment, Nginx SSL & systemd service setup |
| [`docs/constitution/master-vision.md`](docs/constitution/master-vision.md) | Engineering Constitution & non-negotiable coding rules |
| [`docs/architecture.md`](docs/architecture.md) | Detailed logical architecture blueprint |
| [`docs/implementation/system-design.md`](docs/implementation/system-design.md) | Physical system design, DB schemas & API contracts |
| [`TECH_DEBT.md`](TECH_DEBT.md) | Resolved & deferred technical debt ledger |

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
