# Retriever Platform — Comprehensive Feature & Capability Catalog (M1–M53)

**System:** Retriever Enterprise RAG Engine  
**Repository:** `retriever`  
**Document Version:** `v0.51.0`  
**Target Audience:** Platform Architects, System Administrators, & Engineering Team  

---

## 1. Executive Summary

This document serves as the authoritative single source of truth detailing every feature, architectural mechanism, API endpoint, and UI component built into the Retriever platform across all **53 Engineering Milestones (M1 through M53)**.

Each capability is categorized into its primary operational domain and mapped against its execution layer:
- **Admin Dashboard UI** (`apps/web` at `admin.rag.prateeq.in`)
- **Client RAG App UI** (`Prateek_website` at `prateeq.in/rag/app`)
- **Backend Engine & Middleware** (PostgreSQL RLS, FastAPI, Celery, Redis, Pytest)

---

## 2. Feature Directory by Operational Domain

### 🔐 Domain A: Authentication, Security & Multi-Tenancy
| Milestone | Feature / Capability | Technical Description | Backend API / Module | Documentation | Admin UI | Client App |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **M1** | **Multi-Tenant RLS** | PostgreSQL Row-Level Security (`tenant_isolation_policy`) enforcing strict workspace data isolation. | `setup.py` | [`database_and_schemas.md`](infrastructure/database_and_schemas.md) | ✅ Directory | ✅ Scoped |
| **M3, M4** | **API Key Management** | SHA-256 hashed API key issuance (`ret_live_...`), prefix verification, and instant revocation. | [`/v1/tenant.py`](api/tenant.md) | [`auth.md`](api/auth.md) | ✅ Keys Tab | ✅ Embed |
| **M39** | **Auth Harmonization** | Supabase RS256 JWT validation, PKCE session restoration, and single sign-on integration. | [`/v1/auth.py`](api/auth.md) | [`auth.md`](api/auth.md) | ✅ Key Gate | ✅ OAuth |
| **M40** | **LLM Safety Guardrails** | Llama Guard 3 taxonomy, pre-execution prompt injection blocking, and output PII redactor. | `LlamaGuardService` | [`guardrails_and_safety.md`](cognitive/guardrails_and_safety.md) | ⚠️ Config Tab | ✅ Alerts |
| **M41** | **Granular Chunk ACL** | `allowed_roles` and `allowed_users` chunk metadata enforcement during vector search. | `document_chunks` table | [`database_and_schemas.md`](infrastructure/database_and_schemas.md) | ✅ Role Editor | ✅ Scoped |
| **M49** | **Context Compression & Zero-Trust Encryption** | LongLLMLingua prompt compression and AES-GCM envelope encryption for stored vectors/texts. | [`/v1/security_compression.py`](api/security_compression.md) | [`context_compression.md`](cognitive/context_compression.md) | ⚠️ Sliders | ✅ Badge |

---

### 📄 Domain B: Ingestion, OCR & Document Processing
| Milestone | Feature / Capability | Technical Description | Backend API / Module | Documentation | Admin UI | Client App |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **M13, M18** | **Multi-Format Ingestion** | Async and sync parsing for PDF, DOCX, XLSX, PPTX, Markdown, TXT, CSV, Code AST, and JSON files into document chunks. | [`/v1/document.py`](api/document.md) | [`chunking_and_parsing.md`](cognitive/chunking_and_parsing.md) | ✅ Grid | ✅ Library |
| **M14** | **Dual Target Embedding Engine** | Dual execution target: local laptop Ollama (`http://localhost:11434`) vs Cloud VPS CPU/GPU workers. | `/documents/{id}/process` | [`async_workers_and_queues.md`](infrastructure/async_workers_and_queues.md) | ✅ Switch | ⚡ Cloud |
| **M15–M17** | **Document Lifecycle** | Document hashing, duplicate detection, metadata tracking, and soft-deletion cascades. | `DocumentRepository` | [`document.md`](api/document.md) | ✅ Docs Tab | ✅ Library |
| **M42** | **Layout-Aware Vision OCR** | Docling / Unstructured layout-aware OCR for scanned PDFs and complex multi-column table extraction. | `extract_layout_from_pdf` | [`chunking_and_parsing.md`](cognitive/chunking_and_parsing.md) | ✅ OCR toggle | ✅ Status |

---

### 🔍 Domain C: Vector Search, Reranking & Hybrid Retrieval
| Milestone | Feature / Capability | Technical Description | Backend API / Module | Documentation | Admin UI | Client App |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **M5, M6** | **Hybrid Search & RRF** | Reciprocal Rank Fusion (RRF) combining pgvector HNSW dense search with BM25/SPLADE sparse keyword search. | [`/v1/search.py`](api/search.md) | [`hybrid_search_and_fusion.md`](cognitive/hybrid_search_and_fusion.md) | ✅ Config Tab | ✅ Inspector |
| **M9, M43** | **Multi-Embedding Schemas** | Dynamic vector table partitioning for 768, 1024 (BGE-M3/Snowflake), 1536, and 3072 dimension embedding models. | `vector_records_...` | [`database_and_schemas.md`](infrastructure/database_and_schemas.md) | ✅ Settings | ⚡ Auto |
| **M19, M45** | **Cross-Encoder Reranking** | GPU worker microservice offloading Cross-Encoder inference for high-precision result reranking. | `/v1/search` (`reranker_model`) | [`hybrid_search_and_fusion.md`](cognitive/hybrid_search_and_fusion.md) | ✅ Threshold | ✅ Inspector |
| **M44** | **Query Intelligence & CRAG** | Intent routing, HyDE hypothetical embeddings, Self-Querying metadata AST, and Tavily/Brave search. | `QueryIntentAdapter` | [`query_intelligence.md`](cognitive/query_intelligence.md) | ✅ Web Toggle | ✅ Badges |

---

### 🕸️ Domain D: Knowledge Graph & GraphRAG
| Milestone | Feature / Capability | Technical Description | Backend API / Module | Documentation | Admin UI | Client App |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **M37, M44** | **GraphRAG Triples & Entity Extraction** | Dual graph storage engine (PostgreSQL SQL vs Neo4j Cypher), multi-hop entity graph traversal (1–5 hops). | [`/v1/admin.py`](api/admin.md) | [`graphrag.md`](cognitive/graphrag.md) | ✅ Graph Tab | ✅ Citations |

---

### 🤖 Domain E: Agentic Workflows, RLM & Reflection
| Milestone | Feature / Capability | Technical Description | Backend API / Module | Documentation | Admin UI | Client App |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **M2, M10** | **Dynamic 12 LLM Providers** | Support for OpenAI, Gemini, Anthropic, OpenRouter, DeepSeek, Groq, Mistral, xAI, Ollama, Cohere, Bedrock, Azure. | `routing_provider.py` | [`chat.md`](api/chat.md) | ✅ Config Tab | ✅ Panel |
| **M7, M8** | **System Prompt Templates** | Dynamic system prompt templating with runtime variable substitution and cost-free preview mode. | [`/v1/admin.py`](api/admin.md) | [`admin.md`](api/admin.md) | ✅ Prompts | ✅ Studio |
| **M46** | **Agentic Execution Engine** | Multi-step tool-calling execution loop for autonomous agentic reasoning. | [`/v1/agentic.py`](api/agentic.md) | [`agentic_workflows_and_repl.md`](cognitive/agentic_workflows_and_repl.md) | ⚠️ Agent Log | ✅ Mode |
| **M47** | **RLM & REPL Sandbox** | Python REPL execution sandbox for active programmatic document traversal and subroutines. | [`/v1/rlm.py`](api/rlm.md) | [`agentic_workflows_and_repl.md`](cognitive/agentic_workflows_and_repl.md) | ⚠️ Limits | ✅ View |
| **M48** | **Multi-Agent Consensus** | Generator vs. Critic reflection loops for high-stakes enterprise answer verification. | [`/v1/consensus.py`](api/consensus.md) | [`consensus_and_reflection.md`](cognitive/consensus_and_reflection.md) | ⚠️ Critic UI | ✅ Badge |

---

### 📈 Domain F: Quality, Hallucinations, Compliance & Billing
| Milestone | Feature / Capability | Technical Description | Backend API / Module | Documentation | Admin UI | Client App |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **M26** | **SaaS Quotas & Token Budget** | Storage MB limits, document count caps, token rate limiters, and monthly budget enforcement. | `quota_service.py` | [`caching_and_performance.md`](infrastructure/caching_and_performance.md) | ⚠️ Meters | ✅ Telemetry |
| **M50** | **Hallucination Tracing** | Real-time Faithfulness & Context Relevance scoring on live chat streams (`OnlineHallucinationEvaluator`). | [`/v1/admin.py`](api/admin.md) | [`evaluation_and_hallucinations.md`](cognitive/evaluation_and_hallucinations.md) | ❌ Quality Tab | ✅ Feedback |
| **M51** | **Compliance & Sovereignty** | Zero-footprint PII anonymization (`PiiAnonymizer`), hard deletion cascades (`HardPurgeService`), retention SLA. | [`/v1/admin.py`](api/admin.md) | [`storage_and_encryption.md`](infrastructure/storage_and_encryption.md) | ❌ Purge Tab | ✅ Purge CTA |
| **M52** | **Payments & Deposit Billing** | Webhook receivers (Stripe, Razorpay, PhonePe), HMAC signature verification, transaction ledger, auto-upgrade. | [`/v1/payments.py`](api/payments.md) | [`commercial_billing_integration.md`](integrations/commercial_billing_integration.md) | ❌ Ledger Tab | ✅ Invoices |
| **M53** | **n8n Workflow Automation** | Outbound n8n webhook dispatcher (`N8nWebhookDispatcher`), inbound auto-ingest webhook, n8n OpenAPI spec. | [`/v1/workflow.py`](api/workflow.md) | [`n8n_workflow_integration.md`](integrations/n8n_workflow_integration.md) | ❌ n8n Tab | ✅ Snippet |

---

## 3. Operational Implementation Action Plan for Admin Dashboard (`apps/web`)

To achieve complete parity between the backend capability layer and the Admin Dashboard UI, `/tenants/[id]` is organized as a **12-Tab Tenant Control Cockpit**:

1. **Tab 1: Overview** (Kill-switch & workspace metadata)
2. **Tab 2: Documents** (Dual Engine Laptop/Cloud ingestion grid)
3. **Tab 3: Users** (Role assignments & user directory)
4. **Tab 4: API Keys** (Token creation & instant revocation)
5. **Tab 5: System Prompts** (Template editor & variable preview)
6. **Tab 6: Sandbox** (Administrative live RAG chat console)
7. **Tab 7: Knowledge Graph** (GraphRAG Neo4j/Pg inspector & triple editor)
8. **Tab 8: Configuration** (12 Providers, Safety Guardrails, Consensus, RLM & Compression controls)
9. **Tab 9: 📈 Hallucinations & Quality (M50)** (Faithfulness analytics, unfaithful response diff inspector)
10. **Tab 10: 🛡️ Compliance & Sovereignty (M51)** (PII rules, GDPR Hard Purge trigger, retention SLA scheduler)
11: **Tab 11: 💳 Billing & Payment Ledger (M52)** (Transaction log, active quota meters, Checkout Link Generator)
12: **Tab 12: ⚡ n8n & Workflow Automation (M53)** (Outbound webhook config, Ping test, n8n OpenAPI spec viewer)

---

## 4. Platform Batteries Matrix (21 Registered Batteries — v0.86.0)

Every battery in [`BatteryService`](../apps/api/src/domain/batteries/battery_service.py) is documented with an architectural feature guide:

| # | Battery ID | Battery Name | Category | Milestone | Dedicated Feature Guide |
|---|---|---|---|---|---|
| **1** | `bm25_sparse_retrieval` | Sublinear BM25 Keyword Search | `RETRIEVAL` | M12 (v0.12.0) | [`features/bm25-sparse-retrieval.md`](features/bm25-sparse-retrieval.md) |
| **2** | `pgvector_hnsw_dense` | pgvector HNSW Dense Embeddings | `RETRIEVAL` | M1 (v0.1.0) | [`features/pgvector-hnsw-dense.md`](features/pgvector-hnsw-dense.md) |
| **3** | `colbert_maxsim_reranker` | ColBERT MaxSim Late-Interaction Reranker | `RETRIEVAL` | M80 (v0.65.0) | [`features/colbert-maxsim-reranker.md`](features/colbert-maxsim-reranker.md) |
| **4** | `docling_layout_ocr` | Docling Layout-Aware OCR & Table Parser | `RETRIEVAL` | M72 (v0.58.0) | [`features/docling-layout-ocr.md`](features/docling-layout-ocr.md) |
| **5** | `rlm_python_repl` | RLM Python REPL Execution Sandbox | `COMPUTATION_GRAPH` | M48/M56 (v0.45.0) | [`features/rlm-python-repl-sandbox.md`](features/rlm-python-repl-sandbox.md) |
| **6** | `graphrag_hdbscan_clustering` | GraphRAG HDBSCAN Community Clustering | `COMPUTATION_GRAPH` | M81 (v0.66.0) | [`features/graphrag-hdbscan-clustering.md`](features/graphrag-hdbscan-clustering.md) |
| **7** | `neo4j_cypher_graph` | Neo4j Cypher Property Graph Engine | `COMPUTATION_GRAPH` | M37/M44 (v0.35.0) | [`features/neo4j-cypher-property-graph.md`](features/neo4j-cypher-property-graph.md) |
| **8** | `isolation_forest_sentinel` | Telemetry Anomaly Sentinel | `ML_INTELLIGENCE` | M83 (v0.68.0) | [`features/isolation-forest-sentinel.md`](features/isolation-forest-sentinel.md) |
| **9** | `quantile_effort_regressor` | Project Effort & Timeline Regressor | `ML_INTELLIGENCE` | M84 (v0.69.0) | [`features/quantile-effort-regressor.md`](features/quantile-effort-regressor.md) |
| **10** | `kmeans_persona_classifier` | Zero-Cookie Visitor & Lead Scorer | `ML_INTELLIGENCE` | M85 (v0.70.0) | [`features/kmeans-persona-classifier.md`](features/kmeans-persona-classifier.md) |
| **11** | `token_shield_rate_limiter` | Edge AI Token Shield & Rate Limiter | `SAFETY_DEFENSE` | M86 (v0.71.0) | [`features/token-shield-rate-limiter.md`](features/token-shield-rate-limiter.md) |
| **12** | `llama_guard_safety_rails` | Structured LlamaGuard 3 Safety Rails | `SAFETY_DEFENSE` | M85.1 (v0.70.1) | [`features/llama-guard-safety-rails.md`](features/llama-guard-safety-rails.md) |
| **13** | `longllmlingua_compression` | LongLLMLingua Context Compression | `SAFETY_DEFENSE` | M85.2 (v0.70.2) | [`features/longllmlingua-context-compression.md`](features/longllmlingua-context-compression.md) |
| **14** | `nemo_conversational_guardrails` | NVIDIA NeMo Conversational Safety Rails | `SAFETY_DEFENSE` | M94 (v0.79.0) | [`features/nemo-conversational-guardrails.md`](features/nemo-conversational-guardrails.md) |
| **15** | `durable_workflow_engine` | Durable Asynchronous Workflow Engine | `BACKGROUND_WORKFLOWS` | M95 (v0.80.0) | [`features/durable-asynchronous-execution.md`](features/durable-asynchronous-execution.md) |
| **16** | `serverless_gpu_vllm` | Serverless Dedicated GPU & Multi-LoRA | `ML_INTELLIGENCE` | M96 (v0.81.0) | [`features/serverless-gpu-vllm-lora.md`](features/serverless-gpu-vllm-lora.md) |
| **17** | `autonomous_fde_metaprogrammer` | Autonomous FDE Metaprogrammer Studio | `SYSTEM_EXTENSIBILITY` | M97 (v0.82.0) | [`features/scaffolding-metaprogrammer.md`](features/scaffolding-metaprogrammer.md) |
| **18** | `sovereign_edge_sync` | Sovereign Edge SQLite & Vector Sync | `EDGE_DISTRIBUTION` | M98 (v0.83.0) | [`features/sovereign-edge-sync.md`](features/sovereign-edge-sync.md) |
| **19** | `multicloud_failover_libsql` | Multi-Cloud Failover & LibSQL Replicas | `EDGE_DISTRIBUTION` | M99 (v0.84.0) | [`features/multicloud-failover-libsql.md`](features/multicloud-failover-libsql.md) |
| **20** | `sovereign_edge_voice` | Sovereign Edge Voice & Whisper WebRTC | `EDGE_DISTRIBUTION` | M100 (v0.85.0) | [`features/sovereign-edge-voice.md`](features/sovereign-edge-voice.md) |
| **21** | `zero_trust_micro_enclave` | Zero-Trust Micro-Enclave KMS & Attestation | `SAFETY_DEFENSE` | M101 (v0.86.0) | [`features/confidential-micro-enclave.md`](features/confidential-micro-enclave.md) |
