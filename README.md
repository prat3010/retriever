# Retriever — The Open-Source Enterprise Cognitive Engine

<div align="center">

[![License](https://img.shields.io/badge/license-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue.svg)](pyproject.toml)
[![PostgreSQL](https://img.shields.io/badge/postgresql-16%20%2B%20pgvector-336791.svg)](https://github.com/pgvector/pgvector)
[![Tests](https://img.shields.io/badge/tests-777%2B%20passed%20%E2%9C%93-brightgreen.svg)](tests/)
[![Batteries](https://img.shields.io/badge/batteries-20%20included-ff69b4.svg)](#-the-20-platform-batteries)
[![Serving](https://img.shields.io/badge/vLLM-Scale--to--Zero%20(A10G)-orange.svg)](deploy/)

**The un-bloated, Hexagonal alternative to LangChain + Pinecone + LiteLLM + Celery.**  
*Strict PostgreSQL Row-Level Security, ColBERT MaxSim reranking, GraphRAG, NeMo Guardrails, scale-to-zero vLLM serving, sovereign edge sync, multi-cloud failover, and sovereign edge voice.*

[🚀 Live Production Demo](https://rag.prateeq.in) • [📚 Full Documentation](docs/) • [⚡ 30-Second Quickstart](#-quick-start-30-second-dopamine) • [🎯 Launch Playbook](docs/OPEN_SOURCE_LAUNCH_PLAYBOOK.md)

</div>

---

## 💡 Why Retriever? The "Anti-Wrapper" Stack Killer

Most RAG setups in 2026 are fragile glue code: developers stitch together LangChain (abstraction hell), Pinecone ($100s/mo with cross-tenant leak risks), LiteLLM, Celery, and custom OCR scripts. And when running dedicated models, teams pay $720/mo per client for idle GPUs.

**Retriever replaces the entire fragmented stack with a single, clean Hexagonal engine:**

| Capability | Retriever (Open-Source) | Pinecone / Qdrant | LangChain / LlamaIndex | LiteLLM Proxy | Dify / AnythingLLM |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Architecture** | **Pure Hexagonal (0-lockin)** | Proprietary Cloud | Spaghetti Wrappers | Routing Proxy | Monolith App |
| **Multi-Tenancy** | **PostgreSQL RLS (DB-Level)** | Namespace only | Application-level filter | Virtual keys only | Basic workspace |
| **Hybrid Search & Fusion** | **HNSW + BM25 + ColBERT MaxSim** | Dense only | Manual glue code | N/A | Dense only |
| **Layout OCR & Tables** | **Docling Vision OCR (Built-in)** | None | Paid API integration | N/A | Basic text extract |
| **Knowledge Graph** | **Dual GraphRAG (Neo4j / CTEs)** | None | Add-on package | N/A | None |
| **Prompt Optimization** | **DSPy Teleprompter (M92)** | None | Manual prompt tweaking | N/A | None |
| **Conversational Safety** | **NVIDIA NeMo Colang (M94)** | None | Basic regex | None | Keyword blocklist |
| **Durable Asynchronous Jobs**| **Step-Memoized Checkpoints (M95)**| None | Fragile in-memory | N/A | Basic background |
| **Dedicated GPU Serving** | **Scale-to-Zero vLLM / Modal (M96)** | N/A | None | N/A | None |
| **Sovereign Edge Sync** | **SQLite FTS5 + Binary Vectors (M98)** | None | N/A | None | None |
| **Multi-Cloud Failover** | **Quorum Consensus + Turso LibSQL (M99)**| None | None | None | None |
| **Sovereign Edge Voice** | **Local Whisper + Neural TTS (M100)** | None | None | None | None |
| **Monthly Compute Cost** | **$0 - $15 (Scale-to-Zero)** | $100 - $1,000+ | High token waste | Subscription | Server rental |
| **Self-Hosted On-Prem** | **1-Click Docker (`compose up`)** | Closed Cloud | Code library | Self-hosted | Self-hosted |

---

## ⚡ Quick Start (30-Second Dopamine)

Spin up the entire platform locally with zero external API dependencies (runs 100% free with local Ollama embeddings):

```bash
# 1. Clone and launch full stack (PostgreSQL 16 + pgvector, Redis, Ollama, API)
git clone https://github.com/prat3010/retriever.git && cd retriever
docker compose up -d

# 2. Verify health readiness (<60 seconds)
curl http://localhost:8000/health/readiness
# {"status":"ready","environment":"production"}

# 3. Query the auto-seeded demo workspace
curl -X POST http://localhost:8000/v1/search \
  -H "Authorization: Bearer ret_live_demo_00000000000000000000000000000000" \
  -H "Content-Type: application/json" \
  -d '{"query": "How does hybrid search fusion work?"}'
```

- **Interactive API Documentation:** Visit [`http://localhost:8000/docs`](http://localhost:8000/docs)
- **Control Plane & SaaS Studio:** Visit [`http://localhost:3000`](http://localhost:3000)

---

## 🔋 The 20 Platform Batteries

Retriever ships with **20 production-grade batteries** pre-wired through Hexagonal dependency injection:

| Battery # | Battery Identifier | Category | Algorithm / Foundation |
|:---:|:---|:---|:---|
| **1** | `dense_vector_hnsw` | Core Retrieval | pgvector HNSW cosine indexing with dynamic dimensionality (768, 1536, 3072) |
| **2** | `sparse_lexical_bm25` | Core Retrieval | Native PostgreSQL full-text search with English stemming & Reciprocal Rank Fusion |
| **3** | `colbert_maxsim_reranker` | Late Interaction | Token-level late interaction computing cross-attention similarity without latency hit |
| **4** | `docling_ocr_parser` | Multimodal Ingestion | Document layout vision parsing, markdown table reconstruction, bounding-box citations |
| **5** | `rlm_repl_sandbox` | Code Execution | Recursive Language Model document synthesis with sandboxed Python REPL execution |
| **6** | `graphrag_topology` | Graph Reasoning | Dual-engine GraphRAG with Neo4j Cypher and PostgreSQL recursive CTE relational traversals |
| **7** | `isolation_forest_sentinel` | ML Operations | Scikit-Learn unsupervised behavioral profiling with autonomous token-quarantine |
| **8** | `quantile_effort_regressor` | ML Operations | Gradient boosted quantile regressors ($p10, p50, p90$) for software timeline estimation |
| **9** | `zero_cookie_persona_clusterer`| ML Operations | Unsupervised KMeans buyer intent clustering with conversion propensity scoring |
| **10** | `edge_token_shield` | Rate Limiting | Distributed Redis sliding-window token throttling with resilient SSE reconnections |
| **11** | `llama_guard_safety` | LLM Safety | Llama Guard 3 prompt injection filtering and zero-trust PII redaction |
| **12** | `longllmlingua_compressor` | Token Optimization | Perplexity-directed prompt compression removing up to 70% of filler tokens |
| **13** | `nemo_conversational_guardrails`| Conversational Safety| NVIDIA NeMo Colang multi-turn topical moderation and jailbreak prevention |
| **14** | `neo4j_cypher_engine` | Knowledge Graph | Enterprise Cypher graph engine with hardware-sensed fallback to PostgreSQL CTEs |
| **15** | `durable_workflow_engine` | Asynchronous Workflows| Step-memoized fault-tolerant checkpoint state machines with automatic backoff retries |
| **16** | `serverless_gpu_vllm` | ML Serving | Scale-to-zero serverless vLLM with dynamic multi-tenant LoRA tensor swapping (Modal / BentoML) |
| **17** | `autonomous_fde_metaprogrammer`| System Extensibility | AST-verified Hexagonal code synthesis and dynamic in-process plugin mounting |
| **18** | `sovereign_edge_sync` | Edge Distribution | Embedded SQLite 3 FTS5, binary float32 BLOB vectors & differential delta synchronization |
| **19** | `multicloud_failover_libsql` | Edge Distribution | Multi-cloud quorum consensus failover & embedded Turso LibSQL WAL frame replication |
| **20** | `sovereign_edge_voice` | Multimodal Cognition | Full-duplex WebRTC, local Whisper ASR, RMS/ZCR VAD & streaming neural speech synthesis |

---

## 🏛️ Architectural Topology: Pure Hexagonal Core

```text
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ CLIENT CONTROL PLANE & SAAS STUDIO (Next.js 16)                                        │
 │ • Chat Studio, Documents Library, Search Inspector, Embed Configurator & Observability │
 │ • Supabase Auth PKCE Session Verification & Multi-Tenant Routing                       │
 └──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                            │ REST / SSE API Streams (X-User-ID / Bearer)
                                            ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │ FASTAPI APPLICATION GATEWAY (`apps/api/src/routers`)                                   │
  │ • Routers: /v1/chat, /v1/search, /v1/documents, /v1/voice, /v1/multicloud, /v1/edge    │
  │ • Guardrails: Llama Guard 3 Injection Filter & NeMo Conversational Moderation Rails    │
  └──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │
                                             ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │ COGNITIVE DOMAIN CORE (`apps/api/src/domain`)                                          │
  │ • Pure Python abstractions (0 framework / database imports)                            │
  │ • Hybrid Search (HNSW + BM25 + ColBERT MaxSim + RRF Fusion)                            │
  │ • GraphRAG Knowledge Graph Indexing & Neo4j / Pg Triples                               │
  │ • DSPy Declarative Prompt Compilation & Self-Optimization                              │
  │ • Durable Checkpoint State Machine & Step Memoization (M95)                            │
  │ • Sovereign Edge Voice & Local Whisper / WebRTC Speech Synthesis (M100)                │
  └──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │
                                             ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │ INFRASTRUCTURE ADAPTERS (`apps/api/src/adapters`)                                      │
  │ • Database: PostgreSQL 16 + pgvector (Row-Level Security Tenant Isolation)              │
  │ • Serving: Serverless Modal / BentoML vLLM A10G with Dynamic LoRA Tensor Swapping      │
  │ • Edge & Voice: Embedded SQLite FTS5, Turso LibSQL Replicas, Local Whisper & Neural TTS│
  │ • Broker / Cache: Redis Semantic Cache & Sliding-Window Token Shield                    │
  │ • Async Tasks: Celery / RabbitMQ Workers & Distributed Schedulers                      │
  └────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📚 Complete Technical Documentation

- **[Open-Source Launch Playbook](docs/OPEN_SOURCE_LAUNCH_PLAYBOOK.md):** 10k-Star viral launch execution strategy.
- **[Enterprise Security Whitepaper](docs/security/ENTERPRISE_RAG_SECURITY_WHITEPAPER.md):** PostgreSQL RLS isolation, AES-256 envelope encryption, and zero PII retention.
- **[REST API Reference](docs/api/):** Complete specifications for all 25+ REST/SSE endpoints.
- **[Architecture Decision Records (ADRs)](docs/decisions/):** 22 accepted architectural decisions (PostgreSQL, pgvector, ColBERT, GraphRAG, NeMo, vLLM, LibSQL, WebRTC Voice).
- **[Production Operations Runbooks](docs/runbooks/):** Operational guides for SREs and MLOps teams.
- **[Project Health & Test Status](docs/operations/PROJECT_STATUS.md):** Continuous verification matrix across 112 test suites.
- **[Product Roadmap & Batteries Matrix](ROADMAP.md):** Platform roadmap and 20 production batteries overview.

---

## 🧪 Automated Testing & Benchmark Baselines

```bash
# 1. Run complete unit & integration test suite (730+ tests across 108 suites)
uv run pytest apps/api/tests/ -v

# 2. Verify strict Hexagonal import boundaries (0 framework imports in domain)
uv run pytest apps/api/tests/test_architecture.py -v

# 3. Code formatting & linting conformance
uv run ruff check apps/api/src/ apps/api/tests/
```

---

## 👷 Author & Enterprise Architecture Discovery

Retriever is engineered by **[Prateek Sharma](https://prateeq.in)**.

> **Need Retriever deployed inside your enterprise VPC (AWS/GCP/Azure) with custom compliance, private fine-tuned LoRA pipelines, or proprietary ERP/CRM connectors?**  
> 
> 👉 **[Explore Architecture Discovery & Deployments](https://prateeq.in/scoping)**  
> ✉️ Direct inquiries: `prateeqsharma@gmail.com`

---

## 📄 License

Retriever is open-source software licensed under the **[Apache License 2.0](LICENSE)**.
