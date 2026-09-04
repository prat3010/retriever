# Admin Dashboard Architecture & Operational Roadmap
**System:** Retriever RAG Engine — Control Panel (`apps/web`)  
**Deployment URL:** `https://admin.rag.prateeq.in`  
**Target Audience:** Platform Administrator (Prateek Sharma)  
**Cross-Reference:** Linked directly with the **[Client Dashboard & SaaS Studio Ecosystem Roadmap](../../Prateek_website/docs/CLIENT_DASHBOARD_ROADMAP.md)** in `Prateek_website`.

---

## 1. Executive Overview & Strategic Purpose

The **Admin Dashboard** (`apps/web` in the `retriever` repository) is a dedicated Next.js 16 web application engineered to serve as the **Single Operational Helm** for managing the global multi-tenant infrastructure, configuration, and security bounds of the Retriever platform.

### Strategic Boundaries
* **Decoupled Control Panel:** The Admin Dashboard is restricted to platform administrators. End-user clients and RAG subscribers never access this dashboard; they interact exclusively through the **Client SaaS Studio** (`prateeq.in/rag/app`) and **Client Workspace** (`prateeq.in/dashboard`).
* **Root System Oversight:** Operating with administrative master privileges, the dashboard can monitor, configure, suspend, or provision any customer workspace across the entire platform.

---

## 2. Cross-Repository Integration Contract

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ CONTROL PLANE: Prateek_website (prateeq.in) on Vercel                                 │
│ ┌───────────────────────────┐   ┌─────────────────────────┐   ┌─────────────────────┐  │
│ │ Supabase Auth             │   │ Razorpay Subscriptions  │   │ Supabase DB         │  │
│ │ (Google OAuth / Session)  │   │ (Starter / Growth / Ent)│   │ rag_tenants/members │  │
│ └─────────────┬─────────────┘   └────────────┬────────────┘   └──────────┬──────────┘  │
└───────────────┼──────────────────────────────┼───────────────────────────┼─────────────┘
                │                              │                           │
                │ Webhook Tenant Provisioning  │ Administrative Sync       │
                ▼                              ▼                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ RESOURCE SERVER & ADMIN GATEWAY: retriever (rag.prateeq.in) on Oracle VPS              │
│ ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│ │ FastAPI Admin Gateway (apps/api/src/routers/admin.py)                             │  │
│ │ • Security Header: X-Admin-Master-Key                                             │  │
│ │ • Execution Context: app.bypass_rls = 'true' (Bypasses PostgreSQL RLS)            │  │
│ └─────────────────────────────────────┬─────────────────────────────────────────────┘  │
│                                       ▼                                                │
│ ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│ │ Admin Dashboard UI (apps/web) ──► admin.rag.prateeq.in                            │  │
│ │ • KPI Metrics, 4-Step Onboard, 8-Tab Tenant Cockpit, GraphRAG, AI Config, Logs    │  │
│ └───────────────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Authorization & Security Model
1. **Master Secret Header:** All requests from the Admin UI include the HTTP header:
   ```http
   X-Admin-Master-Key: <ADMIN_MASTER_KEY>
   ```
2. **RLS Bypass Context:** The backend FastAPI gateway catches this header via [`verify_admin_key`](../apps/api/src/adapters/api/security.py#L233) and sets `app.bypass_rls = 'true'` on the database session context. This grants root visibility across all tenant boundaries in `TenantDb`, `UserDb`, `ApiKeyDb`, and `DocumentDb`.
3. **Control Plane Provisioning Webhook:** When a client purchases a subscription on `prateeq.in`, `prateeq.in`'s server-side Razorpay webhook handler calls `POST /v1/admin/tenants` using the `X-Admin-Master-Key` to automatically bootstrap the tenant in `retriever`.

---

## 3. Core Feature Directory & System Capabilities

The Admin Dashboard provides **100% administrative control** through 7 main route sections:

### 1. 🚪 `/login` — System Authentication Gate
* **Inputs:** Admin Master Key (Password Input).
* **Behavior:** Validates key against backend `GET /v1/admin/verify-key`. Stores token in `sessionStorage` and redirects to overview.

### 2. 📊 `/` — Platform Operational Overview
* **KPI Metrics Cards:** Real-time totals for **Active Tenants**, **Indexed Document Chunks**, **Total Vector Records**, and **Generated API Keys**.
* **System Infrastructure Health:** Live ping monitors checking PostgreSQL connection pools, Redis cache status, and Celery worker health via `/health/readiness`.

### 3. 🚀 `/onboard` — 4-Step Guided Client Onboarding Wizard
* **Step 1: Workspace Profile:** Input business name and select tier (`standard`, `premium`, `enterprise`).
* **Step 2: Generate API Key:** Create initial client key with custom label and scope (`client` vs `admin`).
* **Step 3: Register Root User:** Create primary user (`display_name`, `external_id`).
* **Step 4: Credentials Summary:** Pre-filled `curl` commands and copyable credentials (`apiUrl`, `tenantId`, `userId`, `apiKey`).

### 4. 🏢 `/tenants` — Platform Tenant Directory
* Live searchable table of all customer workspaces with status indicators (`active`, `suspended`, `pending`).

### 5. 🔍 `/tenants/[id]` — 16-Tab Tenant Control Cockpit
* **Tab 1: Overview:** Workspace UUID, tier, creation date, and **Instant Kill-Switch** buttons (**Suspend Workspace** / **Re-activate**). Suspending instantly blocks all API requests for that tenant.
* **Tab 2: Documents:** Raw file grid with processing status (`PENDING`, `INDEXED`, `FAILED`), file upload, delete, and **Dual Target Engine Embedding**:
  * **⚡ Laptop Button:** Runs parsing & vector embedding on your local laptop via Ollama (`http://localhost:11434`), fetching file bytes from Oracle VM to preserve low VPS RAM.
  * **☁️ Cloud Button:** Runs embedding directly on the Oracle Cloud VPS.
* **Tab 3: 🌌 Vector Space (High-Dimensional Manifold Visualizer):** PCA / t-SNE / UMAP 2D/3D manifold coordinate projections, topic clusters, Silhouette coefficient quality score ($S$), PCA variance retained indicators, and **Dynamic Query Vector Projection** to simulate where test search queries embed in vector space.
* **Tab 4: 🧬 LoRA Adapters (Fine-Tuning Hub):** Dedicated Low-Rank Adaptation cockpit with contrastive pair training, rank selection ($r \in \{4, 8, 16\}$), epochs, loss tracking, and 1-click active serving deployment.
* **Tab 5: 🧠 Cognitive Labs (RLM & Multi-Agent Consensus):**
  * **🐍 RLM Python REPL:** Recursive document decomposition, context minimization, and sandboxed Python AST REPL execution traces with stdout and return values.
  * **🤝 Multi-Agent Consensus Calibration:** Generator vs Critic/Auditor reflection loop with fact-checking iterations and unsupported claims breakdown.
* **Tab 6: Knowledge Graph (GraphRAG):** Hardware capabilities banner (`oracle_vm_lean` vs `macbook`), storage engine toggle (PostgreSQL SQL vs Neo4j Cypher), multi-hop entity graph inspector (1–5 hops), and triple deletion.
* **Tab 7: Sandbox:** Interactive administrative RAG chat window to test tenant vector indexes in real-time.
* **Tab 8: Users:** List, register, edit roles (`admin`, `developer`, `client`), or deactivate tenant user profiles.
* **Tab 9: API Keys:** Issue new token pairs, inspect key prefixes (`ret_live_...`), and instantly revoke key hashes.
* **Tab 10: System Prompts:** Custom system prompt editor (e.g., *"You are an expert contract lawyer..."*), variable substitution, and preview mode without incurring LLM cost.
* **Tab 11: Configuration:** Provider selector (12 AI Providers), `top_k`, reranking thresholds, semantic cache threshold slider ($\tau \in [0.70, 0.99]$), OCR toggles, and Safety Guardrails.
* **Tab 12: 🛰️ Observability & Telemetry:** Real-time token consumption, latency saved, and 1-click **"Purge Semantic Cache"** button.
* **Tab 13: 📈 Hallucinations & Quality:** Real-time Faithfulness & Context Relevance analytics cockpit, unfaithful response log table with diff inspector, and min-faithfulness threshold slider.
* **Tab 14: 🛡️ Compliance & Sovereignty:** PII anonymization rule toggles, One-Click GDPR Hard Purge trigger button, Data Retention SLA scheduler, and PII audit log.
* **Tab 15: 💳 Billing & Payment Ledger:** Commercial transaction ledger table (Stripe/Razorpay/PhonePe), active quota allocation meters, and manual deposit Checkout Link Generator.
* **Tab 16: ⚡ n8n & Workflow Automation:** Outbound n8n Webhook URL configuration, Test Webhook Ping trigger, copyable n8n OpenAPI spec JSON, and inbound webhook log viewer.


### 6. 🛠️ `/settings` — Global Default Configuration Editor
* Set platform-wide defaults for LLM models, embedding dimensions (768, 1536, 3072), default vector distance metrics (Cosine/Euclidean), and default security policies.

### 7. 📝 `/audit-log` — Immutable Security Audit Log
* Append-only compliance log tracking API key creation, tenant suspension/reactivation, document deletion, and configuration overrides across all tenants.

### 8. 🔋 `/batteries` — Platform Batteries & Engine Capabilities Matrix (M86.5)
* Real-time operational command center providing unified visibility across all 14 platform retrieval, ML intelligence, safety defense, and graph computation batteries (including Neo4j Cypher Graph Engine and NeMo Conversational Guardrails).
* Displays algorithmic foundations, live memory statuses (`active`, `standby`, `disabled`), latency benchmarks (`<5ms` to `<15ms`), category filter pills, and active hyperparameters.

### 9. 🔌 `/integrations` — Universal Ecosystem Plugins & Surface Connectors (M90)
* Central management cockpit for **Slack Workspace Bots** (slash commands, webhook signatures), **1-Click Chrome Ingestion Extension** (ZIP bundle generator and token pairing), and **Google Drive 2-Way Sync** (service account permissions, folder webhooks).

### 10. 🤖 `/orchestration` — LangGraph Cyclic Multi-Agent Workflows & HITL Cockpit (M91)
* Real-time workflow state graph visualizer with live node executions, cyclic tool routing, human-in-the-loop (HITL) approval gates, and time-travel state checkpoint browser.

### 11. ✨ `/prompts` — DSPy Declarative Prompt Compilation & Teleprompter Studio (M92)
* Algorithmic prompt optimization studio supporting `BootstrapFewShot` and `MIPROv2` teleprompters.
* Features score lift delta cards ($\Delta > 0$), few-shot demonstration drawer, and 1-click atomic production hot-activation.

### 12. 🔀 `/gateway` — Enterprise LLM Gateway & Multi-Model Smart Router (M93)
* Universal multi-provider proxying across 100+ models (OpenAI, Anthropic, Gemini, Groq, Mistral, and local Ollama/vLLM).
* Live upstream provider latency and connectivity probes, visual fallback cascade editor, circuit-breaker cooldown controls, and virtual tenant spending caps.

### 13. 💾 `/system-data` — Automated Database Snapshots & PITR Recovery Engine (M87)
* Cloud storage snapshot management (S3 / Cloudflare R2), continuous WAL segment archival monitoring, point-in-time recovery (PITR) drills, and atomic database state restoration.

---

## 4. Operational Roadmap & Development Phases

```mermaid
timeline
    title Admin Dashboard Operational Roadmap
    Phase 1 : Completed Baseline M10 Dashboard Setup
    Phase 2 : Control Plane Integration & Auth Harmonization (M39 Alignment)
    Phase 3 : SaaS Resource Quotas & Cost Analytics (M26)
    Phase 4 : Enterprise Security & Compliance Automation (M15 / M51)
    Phase 5 : 2026 World-Class RAG Controls (M54–M60 Alignment)
    Phase 6 : Active Engine Batteries & Observability Matrix (M86.5)
    Phase 7 : Enterprise Ecosystem Plugins & Compliance Vault (M87–M90)
    Phase 8 : LangGraph Orchestration, DSPy Compilation & Smart Gateway (M91–M93)
    Phase 9 : NeMo Guardrails & Durable Asynchronous Workflows (M94–M95)

### Phase 1: Completed Baseline Dashboard (Current State - M10)
- ✅ Next.js 16 scaffold with shadcn/ui, Tailwind v4, TanStack Query, and Zustand.
- ✅ Full implementation of all 7 routes and 8 tenant cockpit tabs.
- ✅ Dual Target Engine embedding integration (Laptop local Ollama vs Cloud VPS).
- ✅ Knowledge Graph (GraphRAG) tab with Neo4j/Postgres engine toggles.

### Phase 2: Control Plane Integration & Auth Harmonization (M39 Alignment)
- **Deprecate Independent Auth:** Remove standalone Google login from `/v1/auth/google` in `retriever`.
- **Supabase OIDC/JWKS Verification:** Configure FastAPI security middleware to validate Supabase Auth RS256 JWTs using public keys from `https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json`.
- **Control Plane Provisioning Webhook Receiver:** Ensure `POST /v1/admin/tenants` handles automated provisioning calls triggered by Razorpay subscription webhooks from `prateeq.in`.

### Phase 3: SaaS Resource Quotas & Cost Analytics (M26)
- **Resource Limits UI:** Add quota management controls in the Tenant Config tab (`max_storage_mb`, `max_documents`, `monthly_token_budget`).
- **Real-Time Token & Cost Breakdown:** Visual graphs displaying input/output token usage per tenant, monthly spend calculations (`cost_usd`), and semantic cache hit rates.
- **Quota Exceeded Hook Controls:** Configure tenant behavior upon reaching 100% quota (return `HTTP 402 Payment Required` vs auto-overage billing).

### Phase 4: Enterprise Security & Compliance Automation (M15 / M51)
- **GDPR Vector Purge Scheduler:** One-click hard delete cascade removing tenant documents across PostgreSQL, vector indexes, Redis semantic cache, and local storage.
- **Immutable Audit Trail Verification:** Cryptographic hash-chain verification for audit log entries.
- **SOC 2 Evidence Package Exporter:** Export system security posture and compliance audit logs as a downloadable ZIP package.

### Phase 5: 2026 World-Class RAG Controls (M54–M60 Alignment)
- **Contextual Retrieval Ingestion Controls (M56):** UI toggles for async Contextual Pre-Chunking headers during document upload.
- **ColBERT Late-Interaction Engine Selector (M57):** Admin selector for Token-Level MaxSim Reranker (Local TEI container vs. Cloud API).
- **Corrective RAG (CRAG) Threshold Configurator (M58):** Confidence score slider for triggering auto-query rewriting and web search fallbacks.
- **Closed-Loop Telemetry Cockpit (M60):** Real-time dashboard panel mapping M50 faithfulness scores directly to automated retrieval parameter auto-tuning (`top_k`, `reranking_threshold`, `rrf_k`).

### Phase 6: Active Engine Batteries & Observability Matrix (M86.5)
- ✅ Dedicated `/batteries` operational command center with live query hooks and auto-refresh.
- ✅ Full inventory of 15 platform batteries (BM25, pgvector HNSW, ColBERT MaxSim, Docling OCR, RLM Sandbox, GraphRAG HDBSCAN, Anomaly Sentinel, Effort Regressor, Persona Clusterer, Token Shield, LlamaGuard 3, LongLLMLingua, NeMo Conversational Guardrails, Neo4j Cypher Graph Engine, Durable Workflow Engine).
- ✅ Real-time metric cards, pulsing status indicators, dynamic hardware sensing, and category filter pills (`Retrieval`, `ML Intelligence`, `Safety & Defense`, `Computation & Graph`, `Background Workflows`).

### Phase 7: Enterprise Ecosystem Plugins & Compliance Vault (M87–M90)
- ✅ `/system-data`: Automated daily cloud database snapshots (Cloudflare R2 / AWS S3) and Point-in-Time Recovery (PITR) engine (M87).
- ✅ `/compliance`: Enterprise compliance vault with Presidio PII redaction and cryptographic GDPR erasure certificate generation (M88).
- ✅ `/system-data`: Multi-region edge read-replica connection pooler and Geo-IP latency routing (M89).
- ✅ `/integrations`: Universal ecosystem plugins for Slack workspace bots (`/ask-retriever`), Manifest V3 Chrome Extension, and 2-way Google Drive / Notion sync (M90).

### Phase 8: LangGraph Orchestration, DSPy Compilation & Smart Gateway (M91–M93)
- ✅ `/orchestration`: LangGraph cyclic multi-agent workflow visualizer with live node executions and Human-in-the-Loop (HITL) approval gates (M91).
- ✅ `/prompts`: DSPy declarative prompt compilation and teleprompter studio with score lift metrics and atomic hot-activation (M92).
- ✅ `/gateway`: Enterprise LLM Gateway and multi-model smart router across 100+ models with live latency probes and virtual tenant spending caps (M93).

### Phase 9: NeMo Guardrails & Durable Asynchronous Workflows (M94–M95)
- ✅ Guardrails & Conversational Safety: NVIDIA NeMo Guardrails integration with Colang dialogue flows and factual grounding checks (M94).
- ✅ Durable Asynchronous AI Workflows: Step-level memoization (<2ms replay), fault-tolerant retry backoff, and execution ledger overview (M95).

---

## 5. Admin API Reference Table

| Endpoint | Method | Security | Purpose |
| :--- | :--- | :--- | :--- |
| `/v1/admin/verify-key` | `GET` | `X-Admin-Master-Key` | Validate admin password credential |
| `/v1/admin/tenants` | `GET` / `POST` | `X-Admin-Master-Key` | List all tenants / Provision new customer tenant |
| `/v1/admin/tenants/{id}` | `GET` / `PUT` | `X-Admin-Master-Key` | Fetch tenant details / Update tenant status or tier |
| `/v1/admin/tenants/{id}/users` | `GET` / `POST` | `X-Admin-Master-Key` | List / Register users within a tenant workspace |
| `/v1/admin/tenants/{id}/api-keys` | `GET` / `POST` | `X-Admin-Master-Key` | List / Generate tenant client API keys |
| `/v1/admin/tenants/{id}/documents` | `GET` / `POST` | `X-Admin-Master-Key` | List / Upload raw documents for tenant |
| `/v1/admin/tenants/{id}/documents/{docId}/process` | `POST` | `X-Admin-Master-Key` | Trigger vector embedding (`?targetEngine=laptop\|oracle`) |
| `/v1/admin/tenants/{id}/prompts` | `GET` / `POST` | `X-Admin-Master-Key` | List / Create tenant system prompt templates |
| `/v1/admin/tenants/{id}/config` | `GET` / `PUT` | `X-Admin-Master-Key` | Fetch / Update tenant LLM settings, rates & quotas |
| `/v1/admin/tenants/{id}/graph` | `GET` / `POST` | `X-Admin-Master-Key` | Query GraphRAG entities & triples / Toggle storage engine |
| `/v1/admin/audit-log` | `GET` | `X-Admin-Master-Key` | Retrieve system compliance mutation logs |

---
*Refer to `Prateek_website/docs/CLIENT_DASHBOARD_ROADMAP.md` for the corresponding Client Dashboard & SaaS Studio specifications.*

---

## **Related Architecture & Cross-References**

- [Admin Dashboard User Guide](ADMIN_DASHBOARD_GUIDE.md)
- [Client Dashboard Specification](../../Prateek_website/docs/CLIENT_DASHBOARD_ROADMAP.md)
- [Retriever Backend Roadmap](../ROADMAP.md)
- [Unified Master Roadmap (SSoT)](../../Prateek_website/docs/UNIFIED_MASTER_ROADMAP.md)
