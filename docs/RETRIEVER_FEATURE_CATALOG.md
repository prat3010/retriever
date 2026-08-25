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
| **M13, M18** | **Multi-Format Ingestion** | Async and sync parsing for PDF, Docx, Markdown, TXT, and JSON files into document chunks. | [`/v1/document.py`](api/document.md) | [`chunking_and_parsing.md`](cognitive/chunking_and_parsing.md) | ✅ Grid | ✅ Library |
| **M14** | **Dual Target Embedding Engine** | Dual execution target: local laptop Ollama (`http://localhost:11434`) vs Cloud VPS CPU/GPU workers. | `/documents/{id}/process` | [`async_workers_and_queues.md`](infrastructure/async_workers_and_queues.md) | ✅ Switch | ⚡ Cloud |
| **M15–M17** | **Document Lifecycle** | Document hashing, duplicate detection, metadata tracking, and soft-deletion cascades. | `DocumentRepository` | [`document.md`](api/document.md) | ✅ Docs Tab | ✅ Library |
| **M42** | **Layout-Aware Vision OCR** | Docling / Unstructured layout-aware OCR for scanned PDFs and complex multi-column table extraction. | `extract_layout_from_pdf` | [`chunking_and_parsing.md`](cognitive/chunking_and_parsing.md) | ✅ OCR toggle | ✅ Status |

---

### 🔍 Domain C: Vector Search, Reranking & Hybrid Retrieval
| Milestone | Feature / Capability | Technical Description | Backend API / Module | Documentation | Admin UI | Client App |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **M5, M6** | **Hybrid Search & RRF** | Reciprocal Rank Fusion (RRF) combining pgvector HNSW dense search with BM25/SPLADE sparse keyword search. | [`/v1/search.py`](api/search.md) | [`hybrid_search_and_fusion.md`](cognitive/hybrid_search_and_fusion.md) | ✅ Config Tab | ✅ Inspector |
| **M9, M43** | **Multi-Embedding Schemas** | Dynamic vector table partitioning for 768, 1536, and 3072 dimension embedding models. | `vector_records_...` | [`database_and_schemas.md`](infrastructure/database_and_schemas.md) | ✅ Settings | ⚡ Auto |
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
11. **Tab 11: 💳 Billing & Payment Ledger (M52)** (Transaction log, active quota meters, Checkout Link Generator)
12. **Tab 12: ⚡ n8n & Workflow Automation (M53)** (Outbound webhook config, Ping test, n8n OpenAPI spec viewer)
