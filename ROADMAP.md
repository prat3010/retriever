# 🗺️ Retriever — Open-Source Product & Architectural Roadmap

> **The un-bloated, Hexagonal alternative to LangChain + Pinecone + LiteLLM + Celery.**  
> *Strict PostgreSQL Row-Level Security, ColBERT MaxSim reranking, GraphRAG, NeMo Guardrails, scale-to-zero vLLM serving, and sovereign edge sync.*

---

## ⚡ Current Status: Enterprise Production Ready (v0.93.0+)

Retriever has completed **109 foundational engineering milestones** spanning core retrieval, multi-tenant isolation, cognitive agentic loops, and scale-to-zero serving across 118 automated test suites.

👉 **Looking for granular historical milestone logs (M1–M109)?**  
See our exhaustive 100+ milestone engineering record: [`docs/engineering/MILESTONES_HISTORY.md`](docs/engineering/MILESTONES_HISTORY.md).

---

## 🔋 The 30 Platform Batteries Matrix

All 30 batteries are wired through strict Hexagonal dependency injection:

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
| **29** | `multimodal_vision_graphrag` | Computation Graph | Architectural schematic parsing, normalized bounding-box coordinates & cross-modal GraphRAG | ✅ Production |
| **30** | `distributed_mcp_mesh` | System Extensibility | Decentralized P2P MCP Mesh Topology, HMAC-SHA256 trust envelopes & federated ReAct delegation | ✅ Production |
| **31** | `mesh_load_balancer` | System Extensibility | Power-of-Two-Choices (P2C) load balancing, EWMA latency decay, load-shedding & ephemeral scale-to-zero | ✅ Production |
| **32** | `vector_raft_sharding` | Edge Distribution | Consistent virtual-node hash partitioning, Raft consensus replication & parallel scatter-gather | ✅ Production |
| **33** | `zkp_vector_attestation` | Safety & Defense | Deterministic binary Merkle trees, zero-knowledge leaf commitments & Ed25519 Grounding Certificates | ✅ Production |

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

### Milestone 113: Multimodal Vision GraphRAG & Schematic Ingestion (v1.3.0-alpha1) — **Completed**
- [x] **Platform Battery #29 Registration:** Cataloged `multimodal_vision_graphrag` in `BatteryService` under `COMPUTATION_GRAPH`.
- [x] **Architectural Schematic Parsing Engine:** Pure domain `SchematicExtractor` parsing SVG XML layouts, binary image headers, flow patterns, and directional connectors with protocols.
- [x] **Normalized Coordinate Geometry:** `BoundingBox` validation ensuring strict $[0.0, 1.0]$ bounds, IoU math, and architectural ontology classification (`api_gateway`, `database`, `microservice`, `queue`, `client_app`, `cache`, `storage`, `auth_service`).
- [x] **Cross-Modal Knowledge Graph Traversal:** Multi-hop graph search linking visual layout components to textual documentation chunks with verifiable visual citations (`[Schematic: ... | Box: ... | "..."]`).
- [x] **FastAPI Multimodal Endpoints:** Mounted `/v1/tenants/{tenantId}/vision/schematic/extract`, `/extract-text`, `/graph/query`, `/schematics/{documentId}`, and `/v1/graph/multimodal/status`.
- [x] **Decoupled SDKs Extended:** Added full Vision GraphRAG API parity to `@prat3010/retriever-client` (npm) and `retriever-python` (PyPI).
- [x] **Control Plane Visual Lightbox:** Integrated visual citation badges and responsive `<Portal>` bounding-box inspection lightbox in `ChatPanel.tsx` with Design System 2.0 theme parity.

### Milestone 114: Real-time Audio Streaming & Low-Latency Full-Duplex WebRTC Voice Agent (v1.4.0-alpha1) — **Completed**
- [x] **Ultra-Low Latency Streaming Audio Pipeline:** Bi-directional full-duplex WebSocket streaming endpoint (`/v1/tenants/{tenantId}/voice/stream/{sessionId}`) with sub-300ms Time-to-First-Audio-Byte (TTFAB) and zero-cloud audio egress.
- [x] **Continuous 20ms PCM16 Ingestion & VAD Endpointing:** Real-time RMS & ZCR voice activity detection and automatic speech endpointing (400ms silence threshold) eliminating manual click-to-stop.
- [x] **Conversational Barge-In / Interruption Engine:** Instant cancellation of server-side synthesis tasks upon user speech detection ($\ge 3$ frames = 60ms) emitting an `interrupted` event and resetting state to `LISTENING`.
- [x] **Decoupled Client SDKs Updated:** Exported `createVoiceStream` and full event typing (`onSessionReady`, `onVadState`, `onTranscript`, `onAgentAudioChunk`, `onInterrupted`, `onTurnComplete`) in `@prat3010/retriever-client` and `retriever-python`.
- [x] **Control Plane Voice Studio Upgrade:** Integrated genuine Web Audio API `AudioContext` + `AnalyserNode` frequency spectrum visualization in `VoiceStudioPanel.tsx` and purged all fake `Math.random()` bars and timer mocks.

### Milestone 115: Distributed Model Context Protocol (MCP) Mesh & Agent Federation (v1.5.0-alpha1) — **Completed**
- [x] **Platform Battery #30 Registration:** Cataloged `distributed_mcp_mesh` in `BatteryService` under `SYSTEM_EXTENSIBILITY`.
- [x] **Decentralized MCP Tool Mesh:** Multi-cluster tool discovery, dynamic capability advertisement, heartbeat leasing (120s eviction), and latency-weighted peer routing.
- [x] **Cryptographic Trust Envelopes:** Inter-cluster tool execution and delegation signed via HMAC-SHA256 with 60-second sliding-window nonce replay protection.
- [x] **Cross-Cluster Agent Federation:** Distributed ReAct cognitive loop allowing agents to delegate sub-goals to specialist agents on remote sovereign clusters with strict circular loop breakers (`FederationLoopError`).
- [x] **Decoupled API Client SDKs Extended:** Added full mesh and federation API parity to `@prat3010/retriever-client` (npm) and `retriever-python` (PyPI).
- [x] **Control Plane Studio Upgraded:** Integrated 3-tab segmented controller in `McpPanel.tsx` with decentralized node topology visualizer and cross-cluster agent delegation cockpit under Design System 2.0.

### Milestone 116: Autonomous Mesh Dynamic Load-Balancing & Ephemeral Enclave Auto-Scaling (v1.6.0-alpha1) — **Completed**
- [x] **Platform Battery #31 Registration:** Cataloged `mesh_load_balancer` in `BatteryService` under `SYSTEM_EXTENSIBILITY`.
- [x] **Power-of-Two-Choices (P2C) Load Balancing:** Implemented pure domain P2C candidate selection algorithm minimizing composite load scores combining EWMA latency, queue depth, and slot saturation without stampedes.
- [x] **EWMA Latency Decay & Concurrency Tracking:** Atomic execution slot reservation (`acquire_slot`/`release_slot`) with Exponentially Weighted Moving Average decay ($\alpha = 0.2$) reflecting genuine execution overhead.
- [x] **Autonomous Scale-to-Zero Enclave Provisioning:** In-process `SovereignEnclaveProvisionerAdapter` scaling out edge enclaves under high cluster pressure and reaping idle enclaves after 300s of inactivity.
- [x] **Circuit-Breaker Load-Shedding:** Hard circuit breaker emitting HTTP 429 Too Many Requests when all candidate nodes exceed 95% slot saturation.
- [x] **FastAPI REST Endpoints:** Mounted `/v1/mesh/load/metrics`, `/v1/mesh/load/autoscaling/events`, `/v1/mesh/load/autoscaling/policy`, `/v1/mesh/load/heartbeat-telemetry`, and `/v1/mesh/load/scale-down/reap`.
- [x] **Decoupled API Client SDKs Extended:** Added full load metrics, autoscaling policy, and enclave reaping API parity to `@prat3010/retriever-client` (npm) and `retriever-python` (PyPI).
- [x] **Control Plane Studio Upgraded:** Integrated 4th tab "Dynamic Load & Enclaves" in `McpPanel.tsx` with cluster capacity dials, interactive autoscaling policy sliders, and live event audit ledger under Design System 2.0.

### Milestone 117: Decentralized Multi-Tenant Vector Sharding & Distributed Raft Consensus (v1.7.0-alpha1) — **Completed**
- [x] **Platform Battery #32 Registration:** Cataloged `vector_raft_sharding` in `BatteryService` under `EDGE_DISTRIBUTION`.
- [x] **Consistent Virtual-Node Hashing:** Deterministic 32-bit FNV-1a hash ring partitioning with 64 virtual nodes (`vnodes`) per shard, supporting both dedicated tenant isolation and shared uniform partitions.
- [x] **Distributed Raft Consensus State Machine:** In-process Raft engine maintaining monotonic terms, candidate majority elections ($\lfloor N/2 \rfloor + 1$), heartbeat leases (50ms), and replicated AppendEntries logs for vector mutations.
- [x] **Scatter-Gather Parallel Vector Search:** Concurrent async query fan-out with Reciprocal Rank Fusion (RRF), score normalization, duplicate suppression, and tunable read consistency quorums (`LOCAL`, `ONE`, `QUORUM`, `ALL`).
- [x] **Online Zero-Downtime Shard Rebalancing:** Skew detector standard deviation monitoring with 2-phase online migration (snapshot transfer + delta log replay + atomic lease cutover).
- [x] **FastAPI REST Endpoints:** Mounted `/v1/shards/topology`, `/v1/shards/query`, `/v1/shards/mutate`, `/v1/shards/raft/status`, `/v1/shards/election`, `/v1/shards/rebalance`, and `/v1/shards/{shard_id}/snapshot`.
- [x] **Decoupled API Client SDKs Extended:** Added full vector sharding, Raft status, and rebalance API parity to `@prat3010/retriever-client` (npm) and `retriever-python` (PyPI).
- [x] **Control Plane Studio Upgraded:** Integrated dedicated "Vector Shards & Raft" panel in `src/components/rag/VectorShardingPanel.tsx` in `/rag/app` under Design System 2.0.

### Milestone 118: Zero-Knowledge Proof (ZKP) Vector Attestation & Verifiable Grounding (v1.8.0-alpha1) — **Completed**
- [x] **Platform Battery #33 Registration:** Cataloged `zkp_vector_attestation` in `BatteryService` under `SAFETY_DEFENSE`.
- [x] **Deterministic Binary Merkle Trees:** Implemented canonical SHA-256 Merkle DAG construction with odd-leaf duplicate padding and leaf commitments ($h_i = \text{SHA256}(\text{tenant} \mathbin{\Vert} \text{doc} \mathbin{\Vert} i \mathbin{\Vert} \text{chunk\_sha256})$).
- [x] **Sub-Millisecond Inclusion Proofs:** Generated authenticated inclusion proof paths ($\pi_i$) allowing instant logarithmic verification without revealing sibling or leaf plaintext text.
- [x] **Ed25519-Signed Grounding Certificates:** Asymmetric digital signatures binding query turns, response hashes, similarity bounds, and Merkle root commitments into immutable tokens.
- [x] **Public Zero-Knowledge Verification Endpoint:** Mounted `POST /v1/zkp/verify` allowing independent auditors to verify grounding validity without authentication or confidential text disclosure.
- [x] **FastAPI REST Endpoints:** Mounted `/v1/zkp/health`, `/v1/tenants/{tenantId}/zkp/merkle-root/{documentId}`, `/v1/tenants/{tenantId}/zkp/proof/chunk/{chunkId}`, `/v1/tenants/{tenantId}/zkp/attest`, and `/v1/tenants/{tenantId}/zkp/certificates`.
- [x] **Decoupled API Client SDKs Extended:** Added full ZKP Merkle root, chunk proof, attestation, and verification API parity to `@prat3010/retriever-client` (npm) and `retriever-python` (PyPI).
- [x] **Control Plane Studio Upgraded:** Integrated dedicated "ZKP Verifiable Grounding" panel in `src/components/rag/ZkpAttestationPanel.tsx` in `/rag/app` under Design System 2.0.


---

## 📚 Technical Documentation Hub

- 🏛️ **Architecture & ADRs:** [`docs/architecture.md`](docs/architecture.md) • [`docs/decisions/`](docs/decisions/)
- 🔌 **REST & SSE API Reference:** [`docs/api/`](docs/api/) (29 endpoints)
- 🔒 **Enterprise Security Whitepaper:** [`docs/security/ENTERPRISE_RAG_SECURITY_WHITEPAPER.md`](docs/security/ENTERPRISE_RAG_SECURITY_WHITEPAPER.md)
- 🛡️ **Sovereign Edge Swarm Handbook:** [`docs/cognitive/SOVEREIGN_EDGE_SWARM_HANDBOOK.md`](docs/cognitive/SOVEREIGN_EDGE_SWARM_HANDBOOK.md)
- 🕸️ **Distributed MCP Mesh & Federation Handbook:** [`docs/cognitive/DISTRIBUTED_MCP_MESH_HANDBOOK.md`](docs/cognitive/DISTRIBUTED_MCP_MESH_HANDBOOK.md)
- ⚖️ **Mesh Load Balancing & Autoscaling Feature Guide:** [`docs/features/mesh-load-balancer.md`](docs/features/mesh-load-balancer.md)
- 💎 **Vector Sharding & Raft Consensus Feature Guide:** [`docs/features/vector-raft-sharding.md`](docs/features/vector-raft-sharding.md)
- 🚀 **Production Deployment Guides:** [`docs/infrastructure/DEPLOYMENT.md`](docs/infrastructure/DEPLOYMENT.md)
- 🤝 **Contributing Guidelines:** [`CONTRIBUTING.md`](CONTRIBUTING.md)
