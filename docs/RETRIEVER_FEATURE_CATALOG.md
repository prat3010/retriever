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
| Milestone | Feature / Capability | Technical Description | Backend API / Module | Admin UI (`apps/web`) | Client RAG App |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M1** | **Multi-Tenant RLS** | PostgreSQL Row-Level Security (`tenant_isolation_policy`) enforcing strict workspace data isolation. | `setup.py` | ✅ Tenant Directory (`/tenants`) | ✅ Auto-scoped session |
| **M3, M4** | **API Key Management** | SHA-256 hashed API key issuance (`ret_live_...`), prefix verification, and instant revocation. | `/v1/admin/tenants/{id}/api-keys` | ✅ API Keys Tab | ✅ Embed Configurator |
| **M39** | **Auth Harmonization** | Supabase RS256 JWT validation, PKCE session restoration, and single sign-on integration. | `/v1/auth/callback`, `verify_admin_key` | ✅ `/login` Master Key Gate | ✅ Supabase OAuth |
| **M40** | **LLM Safety Guardrails** | Llama Guard 3 taxonomy, pre-execution prompt injection blocking, and post-execution output PII redactor. | `LlamaGuardService`, middleware | ⚠️ Config Tab (Needs UI block log) | ✅ Safety alert banners |
| **M41** | **Granular Chunk ACL** | `allowed_roles` and `allowed_users` chunk metadata enforcement during vector search. | `document_chunks` table, DB engine | ✅ Users/Docs Role Editor | ✅ Role-scoped retrieval |
| **M49** | **Context Compression & Zero-Trust Encryption** | LongLLMLingua prompt compression and AES-GCM envelope encryption for stored vectors/texts. | `/v1/security-compression` | ⚠️ Config Tab (Needs slider controls) | ✅ Compressed token badge |

---

### 📄 Domain B: Ingestion, OCR & Document Processing
| Milestone | Feature / Capability | Technical Description | Backend API / Module | Admin UI (`apps/web`) | Client RAG App |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M13, M18** | **Multi-Format Ingestion** | Async and sync parsing for PDF, Docx, Markdown, TXT, and JSON files into document chunks. | `/v1/admin/tenants/{id}/documents` | ✅ Documents Tab Grid | ✅ Document Library |
| **M14** | **Dual Target Embedding Engine** | Dual execution target: local laptop Ollama (`http://localhost:11434`) vs Cloud VPS CPU/GPU workers. | `/documents/{id}/process?targetEngine=...` | ✅ **⚡ Laptop** / **☁️ Cloud** buttons | ⚡ Cloud Default |
| **M15–M17** | **Document Lifecycle** | Document hashing, duplicate detection, metadata tracking, and soft-deletion cascades. | `DocumentRepository` | ✅ Documents Tab | ✅ Document Library |
| **M42** | **Layout-Aware Vision OCR** | Docling / Unstructured layout-aware OCR for scanned PDFs and complex multi-column table extraction. | `extract_layout_from_pdf` | ✅ Config Tab (OCR toggle) | ✅ Parsing status indicator |

---

### 🔍 Domain C: Vector Search, Reranking & Hybrid Retrieval
| Milestone | Feature / Capability | Technical Description | Backend API / Module | Admin UI (`apps/web`) | Client RAG App |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M5, M6** | **Hybrid Search & RRF** | Reciprocal Rank Fusion (RRF) combining pgvector HNSW dense search with BM25/SPLADE sparse keyword search. | `/v1/search`, `/v1/chat` | ✅ Config Tab (`search_mode`) | ✅ Search Inspector |
| **M9, M43** | **Multi-Embedding Schemas** | Dynamic vector table partitioning for 768, 1536, and 3072 dimension embedding models. | `vector_records_1536`, `vector_records_3072` | ✅ Config & Settings Page | ⚡ Auto-managed |
| **M19, M45** | **Cross-Encoder Reranking** | GPU worker microservice offloading Cross-Encoder inference for high-precision result reranking. | `/v1/search` (`reranker_model`) | ✅ Config Tab (`score_threshold`) | ✅ Search Inspector |

---

### 🕸️ Domain D: Knowledge Graph & GraphRAG
| Milestone | Feature / Capability | Technical Description | Backend API / Module | Admin UI (`apps/web`) | Client RAG App |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M37, M44** | **GraphRAG Triples & Entity Extraction** | Dual graph storage engine (PostgreSQL SQL vs Neo4j Cypher), multi-hop entity graph traversal (1–5 hops). | `/v1/admin/tenants/{id}/graph` | ✅ Knowledge Graph Tab | ✅ Graph Citation Badges |

---

### 🤖 Domain E: Agentic Workflows, RLM & Reflection
| Milestone | Feature / Capability | Technical Description | Backend API / Module | Admin UI (`apps/web`) | Client RAG App |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M2, M10** | **Dynamic 12 LLM Providers** | Support for OpenAI, Gemini, Anthropic, OpenRouter, DeepSeek, Groq, Mistral, xAI, Ollama, Cohere, Bedrock, Azure. | `llm_factory.py`, `/v1/chat` | ✅ Config Tab | ✅ SaaS Studio Config Panel |
| **M7, M8** | **System Prompt Templates** | Dynamic system prompt templating with runtime variable substitution and cost-free preview mode. | `/v1/admin/tenants/{id}/prompts` | ✅ Prompts Tab | ✅ Chat Studio |
| **M46** | **Agentic Execution Engine** | Multi-step tool-calling execution loop for autonomous agentic reasoning. | `/v1/agentic` | ⚠️ Needs Agent Log Panel | ✅ Chat Studio Agent Mode |
| **M47** | **RLM & REPL Sandbox** | Python REPL execution sandbox for active programmatic document traversal and subroutines. | `/v1/rlm` | ⚠️ Needs REPL Limit Controls | ✅ Chat Studio RLM View |
| **M48** | **Multi-Agent Consensus** | Generator vs. Critic reflection loops for high-stakes enterprise answer verification. | `/v1/consensus` | ⚠️ Needs Critic Controls | ✅ Consensus Score Badge |

---

### 📈 Domain F: Quality, Hallucinations, Compliance & Billing
| Milestone | Feature / Capability | Technical Description | Backend API / Module | Admin UI (`apps/web`) | Client RAG App |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **M26** | **SaaS Quotas & Token Budget** | Storage MB limits, document count caps, token rate limiters, and monthly budget enforcement. | `TenantQuotaSettings` | ⚠️ Needs Visual Meters | ✅ Telemetry Panel |
| **M50** | **Hallucination Tracing** | Real-time Faithfulness & Context Relevance scoring on live chat streams (`OnlineHallucinationEvaluator`). | `/v1/admin/tenants/{id}/evaluations` | ❌ Needs Quality Tab | ✅ 👍/👎 Feedback Buttons |
| **M51** | **Compliance & Sovereignty** | Zero-footprint PII anonymization (`PiiAnonymizer`), hard deletion cascades (`HardPurgeService`), retention SLA scheduler. | `/v1/admin/tenants/{id}/compliance/*` | ❌ Needs Compliance Tab | ✅ Purge Request Button |
| **M52** | **Payments & Deposit Billing** | Webhook receivers (Stripe, Razorpay, PhonePe), HMAC signature verification, transaction ledger, auto-quota upgrade. | `/v1/payments/*`, `/ledger` | ❌ Needs Billing Tab | ✅ Checkout & Invoices |
| **M53** | **n8n Workflow Automation** | Outbound n8n webhook dispatcher (`N8nWebhookDispatcher`), inbound auto-ingest webhook, n8n OpenAPI spec generator. | `/v1/ingest/webhook`, `/n8n-spec` | ❌ Needs n8n Automation Tab | ✅ 1-Click Snippet Generator |

---

## 3. Operational Implementation Action Plan for Admin Dashboard (`apps/web`)

To achieve complete parity between the backend capability layer and the Admin Dashboard UI, `/tenants/[id]` will be expanded to a **12-Tab Tenant Control Cockpit**:

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
