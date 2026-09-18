# Retriever — The Open-Source Enterprise Cognitive Engine

<div align="center">

[![Release](https://img.shields.io/badge/release-v1.0.0--rc1-blueviolet.svg)](https://github.com/prat3010/retriever/releases)
[![License](https://img.shields.io/badge/license-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](pyproject.toml)
[![PostgreSQL](https://img.shields.io/badge/postgresql-16%20%2B%20pgvector-336791.svg)](https://github.com/pgvector/pgvector)
[![Tests](https://img.shields.io/badge/tests-821%2B%20passed%20%E2%9C%93-brightgreen.svg)](tests/)
[![Batteries](https://img.shields.io/badge/batteries-38%20included-ff69b4.svg)](#-the-38-platform-batteries)
[![SDKs](https://img.shields.io/badge/SDKs-Python%20%7C%20TypeScript-informational.svg)](#-decoupled-client-sdks)

**The un-bloated, Hexagonal alternative to LangChain + Pinecone + LiteLLM + Celery.**  
*Strict PostgreSQL Row-Level Security, ColBERT MaxSim reranking, GraphRAG, NeMo Guardrails, scale-to-zero vLLM serving, sovereign edge sync, multi-cloud failover, sovereign edge voice, autonomous ReAct loops, multi-agent swarm quorum debate, and cognitive long-horizon memory.*

[🚀 Live Production Demo](https://rag.prateeq.in) • [📊 Empirical Benchmarks](docs/benchmarks/EMPIRICAL_LOAD_BENCHMARK_REPORT.md) • [📚 Full Documentation](docs/) • [⚡ 30-Second Quickstart](#-quick-start-30-second-dopamine) • [🎯 Launch Playbook](docs/OPEN_SOURCE_LAUNCH_PLAYBOOK.md)

</div>

> ### 🤖 1-Word AI Onboarding (Zero Reading Required)
> **Don't waste time reading setup guides.** Open this repo in **Cursor**, **Windsurf**, **Claude Code**, or **Antigravity** and simply type:
> 
> ```text
> Setup
> ```
> 
> Your AI agent will inspect your machine, configure environment variables, boot local containers, and run a live demo query in <60 seconds.

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
| **Autonomous ReAct Loop**| **Cyclic State Machine & Anti-Loop (M104)**| None | Fragile wrappers | N/A | Simple chains |
| **Multi-Model Orchestrator**| **Dynamic Escalation & Savings Ledger (M105)**| None | None | Basic fallback | None |
| **Cognitive Agent Memory**| **Ebbinghaus Retention Decay (M108)**| None | None | None | None |
| **Multi-Agent Swarm Quorum**| **Dialectic Debate Consensus (M109)**| None | Complex graph DAGs | None | None |
| **Monthly Compute Cost** | **$0 - $15 (Scale-to-Zero)** | $100 - $1,000+ | High token waste | Subscription | Server rental |
| **Self-Hosted On-Prem** | **1-Click Docker (`compose up`)** | Closed Cloud | Code library | Self-hosted | Self-hosted |

---

## ⚡ Quick Start (30-Second Dopamine)

Spin up the entire platform locally with zero external API dependencies (runs 100% free with local Ollama embeddings):

### Option 0: AI Coding Assistant (Recommended)
Open this repository in Cursor, Windsurf, Claude Code, or Antigravity, and simply send:
```text
Setup
```
Your AI agent will sense your hardware, launch the stack, and test your first search query autonomously.

### Option A: The 1-Line Drop-In
```bash
curl -fsSL https://get.retriever.run | bash
```

### Option B: Docker Compose
```bash
# 1. Clone and launch full stack (PostgreSQL 16 + pgvector, Redis, Ollama, API, Web Studio)
git clone https://github.com/prat3010/retriever.git && cd retriever
docker compose up -d

# 2. Verify health readiness (<60 seconds)
curl http://localhost:8000/health/readiness
# {"status":"ready","environment":"production"}

# 3. Query the auto-seeded demo workspace
curl -X POST http://localhost:8000/v1/search \
  -H "Authorization: Bearer ret_live_demo_00000000000000000000000000000000" \
  -H "Content-Type: application/json" \
  -d '{"query": "How does ColBERT late interaction work?"}'
```

- **Interactive API Documentation:** Visit [`http://localhost:8000/docs`](http://localhost:8000/docs)
- **Control Plane & SaaS Studio:** Visit [`http://localhost:3000`](http://localhost:3000)

---

## 📦 Decoupled Client SDKs

Integrate Retriever natively into your applications with our official client SDKs:

### TypeScript / JavaScript (Node, Browser & Next.js)
```bash
npm install @prat3010/retriever-client
```
```typescript
import { RetrieverClient } from "@prat3010/retriever-client";

const client = new RetrieverClient({
  baseUrl: "http://localhost:8000",
  apiKey: "ret_live_demo_00000000000000000000000000000000",
  tenantId: "00000000-0000-0000-0000-000000000001",
});

const results = await client.search("How does hybrid search fusion work?");
console.log(results);
```

### Python (Sync & Async)
```bash
pip install retriever-python
```
```python
from retriever import RetrieverClient

client = RetrieverClient(
    base_url="http://localhost:8000",
    api_key="ret_live_demo_00000000000000000000000000000000",
    tenant_id="00000000-0000-0000-0000-000000000001",
)

results = client.search("How does hybrid search fusion work?")
print(results.results[0].content)
```

### ☸️ Enterprise Kubernetes (Helm 3 & Native Operator)
Deploy high-availability multi-replica clusters with HorizontalPodAutoscaler v2, cert-manager TLS, pgvector, and Redis:
```bash
helm install retriever ./deploy/helm/retriever --namespace retriever --create-namespace
```
Or manage clusters declaratively via the Kubernetes Operator:
```bash
kubectl apply -f deploy/operator/crds/retrieverclusters.retriever.run.crd.yaml
kubectl apply -f deploy/operator/samples/retriever_cluster_production.yaml
```
See the [Helm Chart Guide](deploy/helm/retriever/README.md) and [Kubernetes Operator Guide](deploy/operator/README.md).

---

### 🔋 The 38 Platform Batteries

Retriever ships with **38 production-grade batteries** pre-wired through Hexagonal dependency injection:

| # | Battery Name | Category | Architectural Capability |
|:---:|:---|:---|:---|
| **1** | `dense_vector_hnsw` | Core Retrieval | pgvector HNSW Cosine Indexing with Dynamic Dimensionality (768, 1536, 3072) |
| **2** | `sparse_lexical_bm25` | Core Retrieval | Native PostgreSQL Full-Text Search with English Stemming & RRF Fusion |
| **3** | `colbert_maxsim_reranker` | Late Interaction | Token-Level Cross-Attention Similarity over Query/Document Token Embeddings |
| **4** | `docling_ocr_parser` | Multimodal Ingestion | Vision Layout Parsing, Markdown Table Reconstruction & Bounding-Box Citations |
| **5** | `rlm_repl_sandbox` | Code Execution | Recursive Language Model Document Synthesis with Sandboxed Python REPL |
| **6** | `graphrag_topology` | Graph Reasoning | Dual-Engine GraphRAG with Neo4j Cypher and PostgreSQL Recursive CTEs |
| **7** | `isolation_forest_sentinel` | ML Operations | Scikit-Learn Unsupervised Behavioral Profiling with Automated Token-Quarantine |
| **8** | `quantile_effort_regressor` | ML Operations | Gradient Boosted Quantile Regressors ($P_{10}, P_{50}, P_{90}$) for Scope Estimation |
| **9** | `zero_cookie_persona_clusterer` | ML Operations | Unsupervised KMeans Buyer Intent Clustering with Conversion Propensity Scoring |
| **10** | `edge_token_shield` | Rate Limiting | Distributed Redis Sliding-Window Token Throttling with Resilient SSE Reconnections |
| **11** | `llama_guard_safety` | LLM Safety | Llama Guard 3 Prompt Injection Filtering and Zero-Trust PII Redaction |
| **12** | `longllmlingua_compressor` | Token Optimization | Perplexity-Directed Prompt Compression Removing up to 70% of Filler Tokens |
| **13** | `nemo_conversational_guardrails` | Conversational Safety | NVIDIA NeMo Colang Multi-Turn Topical Moderation and Jailbreak Prevention |
| **14** | `neo4j_cypher_engine` | Knowledge Graph | Enterprise Cypher Graph Engine with Hardware-Sensed Fallback to PostgreSQL CTEs |
| **15** | `durable_workflow_engine` | Async Workflows | Step-Memoized Fault-Tolerant Checkpoint State Machines with Exponential Backoff |
| **16** | `serverless_gpu_vllm` | ML Serving | Scale-to-Zero Serverless vLLM with Dynamic Multi-Tenant LoRA Tensor Swapping |
| **17** | `autonomous_fde_metaprogrammer` | Extensibility | AST-Verified Hexagonal Code Synthesis and Dynamic In-Process Plugin Mounting |
| **18** | `sovereign_edge_sync` | Edge Distribution | Embedded SQLite 3 FTS5, Binary Float32 Vectors & Differential Delta CRDT Sync |
| **19** | `multicloud_failover_libsql` | Edge Distribution | Monotonic Generation Raft Quorum + EWMA Circuit Breakers & Turso LibSQL Replication |
| **20** | `sovereign_edge_voice` | Sovereign Audio | Full-Duplex Neural Voice with Local Whisper ASR, RMS/ZCR VAD & WebRTC Streaming |
| **21** | `zero_trust_kms_enclave` | Hardware Security | Sub-Enclave AES-256-GCM Hardware Encryption with Cloud KMS Remote Attestation |
| **22** | `autonomous_edge_swarm` | Edge Distribution | Decentralized Anti-Entropy Gossip Mesh with Vector CRDT Sync & Split-Brain Quorum |
| **23** | `autonomous_react_loop` | Agentic Reasoning | Directed DAG Multi-Turn ReAct Tool Loop with Self-Healing Dynamic Ast Corrections |
| **24** | `smart_tool_gateway` | Gateway Economics | Heuristic Cost-Aware Semantic Tool Router with Model Escalation Routing |
| **25** | `studio_tool_cockpit` | Developer Experience | Visual Model Context Protocol (MCP) Tool Builder & Dynamic JSON-RPC Stdio Invoker |
| **26** | `zero_toy_conformance` | Architecture Safety | Static AST Hexagonal Boundary Enforcement & Anti-Toy Algorithmic Gatekeeper |
| **27** | `cdc_community_connectors` | System Extensibility | High-Watermark CDC Pipelines (PostgreSQL, S3, GitHub, Slack) with ETag Caching |
| **28** | `kubernetes_native_operator` | System Extensibility | Level-Triggered State Reconciler, RetrieverCluster CRD OpenAPI v3 & Helm 3 Charts |
| **29** | `multimodal_vision_graphrag` | Computation Graph | Architectural Schematic Parsing, Bounding-Box Graph Construction & Cross-Modal RRF |
| **30** | `distributed_mcp_mesh` | System Extensibility | P2P MCP Mesh Topology, HMAC-SHA256 Trust Envelopes & Dynamic ReAct Task Delegation |
| **31** | `mesh_load_balancer` | System Extensibility | Power-of-Two-Choices (P2C) + EWMA Latency Decay + Saturation Load Shedding & Scale-to-Zero Lifecycle |
| **32** | `vector_raft_sharding` | Edge Distribution | Consistent Virtual-Node Hash Partitioning + Raft Quorum Replication & Parallel Scatter-Gather Fusion |
| **33** | `zkp_vector_attestation` | Safety & Defense | Deterministic Binary Merkle Trees + Zero-Knowledge Leaf Commitments + Ed25519 Grounding Certificates |
| **34** | `enterprise_identity_federation` | Safety & Defense | SAML 2.0 Identity Provider SSO + RFC 7644 SCIM 2.0 Directory Sync & Pre-Retrieval RB-VAC Pruning |
| **35** | `continuous_preference_tuning` | ML Intelligence | Continuous DPO / ORPO Preference Fine-Tuning + Automated Validation Gate & Hot LoRA Rollback |
| **36** | `ephemeral_federated_sandbox` | Security | Ephemeral multi-tenant code execution sandbox with hard resource limits |
| **37** | `distributed_task_memoizer` | Resiliency | Step-memoized async task checkpointing with deterministic crash resumption |
| **38** | `graph_of_thought_engine` | Cognitive Reasoning | Autonomous Graph-of-Thought (GoT) cognitive reasoning, multi-path exploration & backtracking |

---

## 🛡️ Architectural Durability: Why Retriever is Future-Proof

A common question from engineering directors, CTOs, and technical evaluators is:  
> *"When frontier LLMs reach 10-million-token context windows, won't retrieval systems become obsolete?"*

The answer is an unequivocal **no**. Retriever was architected specifically to thrive across technological model transitions through **5 immutable architectural invariants**:

### 1. The "Infinite Context Window" Economic & Latency Fallacy
Dumping raw 500-page corporate repositories directly into an LLM's context window is economically and operationally non-viable in production:
- **Cost Economics:** Processing a 10M-token prompt on frontier models costs between **\$15 and \$50 per query**. Retriever retrieves and packs only the top-k relevant spans, executing queries for **<\$0.001**.
- **Time-to-First-Token (TTFT):** Ingesting millions of tokens incurs 25–45 seconds of pre-fill processing latency. Retriever's HNSW + BM25 + ColBERT late-interaction pipeline retrieves relevant passages in **<200ms**.
- **Needle-in-a-Haystack Degradation:** Empirical research demonstrates that LLM retrieval accuracy degrades sharply ("lost-in-the-middle") as prompt size expands. Retriever's **token-level ColBERT MaxSim cross-attention** and **4-Agent Quorum Consensus** pinpoints exact clauses with verified string-span grounding.

### 2. Model-Agnostic Hexagonal Boundaries (Zero Vendor Lock-in)
Retriever's core domain layer (`src/domain/`) enforces strictly **zero external framework or vendor SDK imports** (`0` imports from OpenAI, Anthropic, or proprietary APIs).  
Every model interaction executes across abstract domain protocols (`LLMProviderProtocol`, `EmbeddingProviderProtocol`). When a new frontier model (GPT-6, Claude 4, or open-weights Llama 5) is released, swapping models requires editing **one adapter class** without modifying business logic, memory systems, or database schemas.

### 3. The 30-Year PostgreSQL Foundation
While specialized vector database startups (Pinecone, Chroma, Milvus) face commercial volatility, acquisition risks, and aggressive pricing shifts, Retriever is anchored on **PostgreSQL 16 with `pgvector`**:
- The world's most battle-tested, ACID-compliant relational engine running in global production for over 30 years.
- Combines structured relational data, JSONB tenant configs, native BM25 full-text search, graph recursive CTEs, and HNSW vector indexes within a **single unified database**.

### 4. Universal Open Standards (Model Context Protocol - MCP)
Retriever is a native **Model Context Protocol (MCP)** server (Milestone 103). Rather than existing as an isolated software silo, all 34 platform batteries are exposed via standard JSON-RPC 2.0 (SSE and Stdio) transports. Any future AI model, IDE (Cursor, VS Code), or autonomous agent framework (Claude Desktop) can natively discover, authorize, and invoke Retriever tools out-of-the-box.

### 5. Sovereign Edge Immunity & Regulatory Durability
Data privacy legislation (GDPR, HIPAA, EU AI Act, India DPDP Act) is expanding globally, legally prohibiting the transmission of confidential corporate IP to public cloud AI endpoints. Retriever's **offline embedded SQLite FTS5 engine**, **local Ollama embedding pipeline**, and **hardware-rooted micro-enclave memory sealing** guarantee that your retrieval infrastructure remains compliant, air-gapped, and resilient against cloud policy mandates.

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
- **[Architecture Decision Records (ADRs)](docs/decisions/):** 32 accepted architectural decisions (PostgreSQL, pgvector, ColBERT, GraphRAG, NeMo, vLLM, LibSQL, WebRTC Voice, MCP Mesh, Vector Sharding).
- **[Production Operations Runbooks](docs/runbooks/):** Operational guides for SREs and MLOps teams.
- **[Project Health & Test Status](docs/operations/PROJECT_STATUS.md):** Continuous verification matrix across 125 test suites.
- **[Product Roadmap & Batteries Matrix](ROADMAP.md):** Platform roadmap and 34 production batteries overview.

---

## 🧪 Automated Testing & Benchmark Baselines

```bash
# 1. Zero-Toy & Anti-Mock Static Analysis Linter (ensures 0 mock classes, faked scores, or dummy frames)
python3 scripts/audit_zero_toy.py

# 2. Run Zero-Toy Invariant regression test
uv run pytest apps/api/tests/test_zero_toy_invariants.py -v

# 3. Run complete unit & integration test suite (730+ tests across 108 suites)
uv run pytest apps/api/tests/ -v

# 4. Verify strict Hexagonal import boundaries (0 framework imports in domain)
uv run pytest apps/api/tests/test_architecture.py -v

# 5. Code formatting & linting conformance
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
