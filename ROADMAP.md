# 🗺️ Retriever — Open-Source Product & Architectural Roadmap

> **The un-bloated, Hexagonal alternative to LangChain + Pinecone + LiteLLM + Celery.**  
> *Strict PostgreSQL Row-Level Security, ColBERT MaxSim reranking, GraphRAG, NeMo Guardrails, scale-to-zero vLLM serving, and sovereign edge sync.*

---

## ⚡ Current Status: Enterprise Production Ready (v0.93.0+)

Retriever has completed **109 foundational engineering milestones** spanning core retrieval, multi-tenant isolation, cognitive agentic loops, and scale-to-zero serving across 118 automated test suites.

👉 **Looking for granular historical milestone logs (M1–M109)?**  
See our exhaustive 100+ milestone engineering record: [`docs/engineering/MILESTONES_HISTORY.md`](docs/engineering/MILESTONES_HISTORY.md).

---

## 🔋 The 28 Platform Batteries Matrix

All 28 batteries are wired through strict Hexagonal dependency injection:

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
| **21** | `zero_trust_micro_enclave` | Safety & Defense | Hardware-rooted AES-256-GCM memory sealing & remote attestation | ✅ Production |
| **22** | `autonomous_swarm_mesh` | Edge Distribution | SWIM failure detection, epidemic P2P gossip & vector clock reconciliation | ✅ Production |
| **23** | `universal_mcp_server` | Tool Protocols | JSON-RPC 2.0 & SSE Model Context Protocol server exposing all platform batteries | ✅ Production |
| **24** | `react_execution_loop` | Agentic Workflows | Autonomous multi-turn ReAct reasoning loop with self-healing error recovery | ✅ Production |
| **25** | `cognitive_agent_memory` | Agent Memory | Ebbinghaus decay retention & episodic/procedural experience distillation | ✅ Production |
| **26** | `multi_agent_swarm_quorum` | Multi-Agent Systems | Dialectic debate DAG, weighted quorum voting & hallucination pruning | ✅ Production |
| **27** | `cdc_community_connectors` | System Extensibility | Relational PostgreSQL/MySQL high-watermark CDC, S3/R2 watchers & GitHub/Slack | ✅ Production |
| **28** | `kubernetes_native_operator` | System Extensibility | Level-triggered state reconciler, RetrieverCluster CRD OpenAPI v3 & Helm 3 | ✅ Production |

---

## 🚀 Active Open-Source Releases & Roadmap (2026+)

### Milestone 110: Public Open-Source Launch (v1.0.0-rc1) — **Completed**
- [x] **1-Line Quickstart Script:** `curl -fsSL https://get.retriever.run | bash` with automated environment sensing (Apple Silicon MPS / NVIDIA CUDA / CPU) and 1-click Docker Compose launch.
- [x] **Decoupled API Client SDKs:** Standalone `@prat3010/retriever-client` on npm (TypeScript/ESM/CJS) and `retriever-python` on PyPI (Sync/Async) covering all 26 batteries.
- [x] **Hacker News & X Launch:** Reconciled 26-battery launch playbook ([`docs/OPEN_SOURCE_LAUNCH_PLAYBOOK.md`](docs/OPEN_SOURCE_LAUNCH_PLAYBOOK.md)).

### Milestone 111: Community Connectors Ecosystem (v1.1.0-alpha1) — **Completed**
- [x] **Enterprise Data Connectors:**
  - PostgreSQL & MySQL high-watermark Change-Data-Capture (CDC) connector with chronological watermark cursor tracking (`DatabaseCdcConnector`).
  - S3-compatible cloud object storage watcher for AWS S3, Cloudflare R2, MinIO, and GCS with ETag differential change detection (`S3StorageConnector`).
  - GitHub repository markdown docs, issues, and pull request sync with `since` cursor tracking (`GitHubConnector`).
  - Slack channel history and thread aggregation connector with timestamp cursor tracking (`SlackConnector`).
- [x] **Custom Ingestion Pipeline SDK:** Standardized `BaseConnector` lifecycle, `BaseDocumentParser`, `@register_connector` decorator for dynamic third-party extensions, and `GET /v1/admin/connectors/manifests`.
- [x] **Platform Battery #27 Registration:** Cataloged `cdc_community_connectors` in `BatteryService` under `SYSTEM_EXTENSIBILITY`.
- [x] **Decoupled Client SDKs Updated:** Added connector management methods to `@prat3010/retriever-client` and `retriever-python`.

### Milestone 112: Kubernetes Native Operator & Helm Charts (v1.2.0-alpha1) — **Completed**
- [x] **Official Production Helm 3 Chart:** Highly configurable Helm chart in `deploy/helm/retriever/` orchestrating multi-replica FastAPI pods, Next.js Web Studio, HPA v2, Ingress with cert-manager TLS, PostgreSQL 16 + pgvector StatefulSet, and Redis 7.
- [x] **Kubernetes Custom Resource Definition (CRD):** `RetrieverCluster` (`retriever.run/v1alpha1`) with comprehensive OpenAPI v3 schema validation, subresources (`status`, `scale`), and `kubectl get rc` printer columns.
- [x] **Level-Triggered Cluster Reconciler:** Hexagonal reconciler managing state transitions (`Pending` $\rightarrow$ `Provisioning` $\rightarrow$ `Running`), rolling upgrades on image tag changes, GPU accelerator node affinity/tolerations, and automated database backup jobs.
- [x] **Platform Battery #28 Registration:** Cataloged `kubernetes_native_operator` in `BatteryService` under `SYSTEM_EXTENSIBILITY`.
- [x] **Admin Cluster Management APIs:** `GET /v1/admin/operator/status`, `GET /v1/admin/operator/clusters`, `POST /v1/admin/operator/reconcile`, and `POST /v1/admin/operator/clusters/{cluster_name}/backup`.

### Milestone 113: Multimodal Vision GraphRAG (Next Target)
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
