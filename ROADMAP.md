# 🗺️ Retriever — Open-Source Product & Architectural Roadmap

> **The un-bloated, Hexagonal alternative to LangChain + Pinecone + LiteLLM + Celery.**  
> *Strict PostgreSQL Row-Level Security, ColBERT MaxSim reranking, GraphRAG, NeMo Guardrails, scale-to-zero vLLM serving, and sovereign edge sync.*

---

## ⚡ Current Status: Enterprise Production Ready (v0.85+)

Retriever has completed **102 foundational engineering milestones** spanning core retrieval, multi-tenant isolation, cognitive agentic loops, and scale-to-zero serving across 112 automated test suites.

👉 **Looking for granular historical milestone logs (M1–M102)?**  
See our exhaustive 100+ milestone engineering record: [`docs/engineering/MILESTONES_HISTORY.md`](docs/engineering/MILESTONES_HISTORY.md).

---

## 🔋 The 20 Platform Batteries Matrix

All 20 batteries are wired through strict Hexagonal dependency injection:

| Battery # | Battery Identifier | Category | Architectural Foundation | Status |
|:---:|:---|:---|:---|:---:|
| **1** | `dense_vector_hnsw` | Core Retrieval | pgvector HNSW cosine indexing with dynamic dimensionality (768, 1536, 3072) | ✅ Production |
| **2** | `sparse_lexical_bm25` | Core Retrieval | Native PostgreSQL full-text search with English stemming & RRF fusion | ✅ Production |
| **3** | `colbert_maxsim_reranker` | Late Interaction | Token-level late interaction computing cross-attention similarity | ✅ Production |
| **4** | `docling_ocr_parser` | Multimodal Ingestion | Vision layout parsing, markdown table reconstruction, bounding-box citations | ✅ Production |
| **5** | `rlm_repl_sandbox` | Code Execution | Recursive Language Model document synthesis with sandboxed Python REPL | ✅ Production |
| **6** | `graphrag_topology` | Graph Reasoning | Dual-engine GraphRAG with Neo4j Cypher and PostgreSQL recursive CTEs | ✅ Production |
| **7** | `isolation_forest_sentinel` | ML Operations | Scikit-Learn unsupervised behavioral profiling with automated token-quarantine | ✅ Production |
| **8** | `quantile_effort_regressor` | ML Operations | Gradient boosted quantile regressors ($P_{10}, P_{50}, P_{90}$) for software effort | ✅ Production |
| **9** | `zero_cookie_persona_clusterer`| ML Operations | Unsupervised KMeans buyer intent clustering with conversion propensity | ✅ Production |
| **10** | `edge_token_shield` | Rate Limiting | Distributed Redis sliding-window token throttling with resilient SSE reconnections | ✅ Production |
| **11** | `llama_guard_safety` | LLM Safety | Llama Guard 3 prompt injection filtering and zero-trust PII redaction | ✅ Production |
| **12** | `longllmlingua_compressor` | Token Optimization | Perplexity-directed prompt compression removing up to 70% of filler tokens | ✅ Production |
| **13** | `nemo_conversational_guardrails`| Conversational Safety| NVIDIA NeMo Colang multi-turn topical moderation and jailbreak prevention | ✅ Production |
| **14** | `neo4j_cypher_engine` | Knowledge Graph | Enterprise Cypher graph engine with hardware-sensed fallback to PostgreSQL CTEs | ✅ Production |
| **15** | `durable_workflow_engine` | Asynchronous Workflows| Step-memoized fault-tolerant checkpoint state machines with automatic backoff | ✅ Production |
| **16** | `serverless_gpu_vllm` | ML Serving | Scale-to-zero serverless vLLM with dynamic multi-tenant LoRA tensor swapping | ✅ Production |
| **17** | `autonomous_fde_metaprogrammer`| Extensibility | AST-verified Hexagonal code synthesis and dynamic in-process plugin mounting | ✅ Production |
| **18** | `sovereign_edge_sync` | Edge Distribution | Embedded SQLite 3 FTS5, binary float32 BLOB vectors & differential delta CRDT | ✅ Production |
| **19** | `multicloud_failover_libsql` | Edge Distribution | Multi-cloud quorum consensus failover & embedded Turso LibSQL replication | ✅ Production |
| **20** | `sovereign_edge_voice` | Multimodal Voice | Full-duplex WebRTC, local Whisper ASR, RMS/ZCR VAD & streaming neural TTS | ✅ Production |

---

## 🚀 Upcoming Open-Source Roadmap (2026+)

### Milestone 103: Public Open-Source Launch (v1.0.0-rc1)
- [ ] **1-Line Quickstart Script:** `curl -fsSL https://get.retriever.run | bash` for automated environment sensing and Docker launch.
- [ ] **Decoupled API Client SDK:** Publish standalone `@prat3010/retriever-client` npm and `retriever-python` PyPI packages.
- [ ] **Hacker News & X Launch:** Execute community launch playbook ([`docs/OPEN_SOURCE_LAUNCH_PLAYBOOK.md`](docs/OPEN_SOURCE_LAUNCH_PLAYBOOK.md)).

### Milestone 104: Community Connectors Ecosystem
- [ ] **Enterprise Data Connectors:**
  - PostgreSQL / MySQL change-data-capture (CDC) sync via Debezium.
  - S3 / Google Cloud Storage / Azure Blob auto-indexing watcher.
  - Notion, GitHub Issues / PRs, and Google Drive OAuth connectors.
- [ ] **Custom Ingestion Pipeline SDK:** Standardized interface for community-authored file parsers.

### Milestone 105: Kubernetes Native Operator & Helm Charts
- [ ] **Official Helm Chart:** Production-ready Helm template for multi-replica FastAPI pods, partitioned pgvector storage, and Redis Sentinel.
- [ ] **Kubernetes Operator:** Custom Resource Definition (`kind: RetrieverCluster`) managing automated database backups, rolling schema migrations, and GPU worker autoscaling.

### Milestone 106: Multimodal Vision GraphRAG
- [ ] **Direct Image & Video Chunking:** Embedding and indexing technical schematics, architectural blueprints, and slide decks alongside extracted text.
- [ ] **Visual Graph Traversal:** Interleaved image-text entity extraction linking diagram components to tabular data and explanatory prose.

---

## 📚 Technical Documentation Hub

- 🏛️ **Architecture & ADRs:** [`docs/architecture.md`](docs/architecture.md) • [`docs/decisions/`](docs/decisions/)
- 🔌 **REST & SSE API Reference:** [`docs/api/`](docs/api/) (28 endpoints)
- 🔒 **Enterprise Security Whitepaper:** [`docs/security/ENTERPRISE_RAG_SECURITY_WHITEPAPER.md`](docs/security/ENTERPRISE_RAG_SECURITY_WHITEPAPER.md)
- 🛡️ **Sovereign Edge Swarm Handbook:** [`docs/cognitive/SOVEREIGN_EDGE_SWARM_HANDBOOK.md`](docs/cognitive/SOVEREIGN_EDGE_SWARM_HANDBOOK.md)
- 🚀 **Production Deployment Guides:** [`docs/infrastructure/DEPLOYMENT.md`](docs/infrastructure/DEPLOYMENT.md)
- 🤝 **Contributing Guidelines:** [`CONTRIBUTING.md`](CONTRIBUTING.md)
