# The Engineering Constitution of Retriever

---

## 1. The Retriever Manifesto & Guiding Principles

### 1.1 Core Ethos
As the founding architect of the Retriever project, we establish this Constitution as the supreme technical law of our platform. This document defines immutable architectural boundaries, operational constraints, design guidelines, and engineering philosophies that MUST govern all development, refactoring, and AI-assisted changes.

Retriever is a **reusable RAG engine** that powers client-specific frontends. It is not a single assistant, not a chat UI, not a turnkey SaaS product. It is the modular backend that coaching portals, CA assistants, legal tools, and custom apps all talk to through a simple API key. Each frontend is its own product with its own branding, user auth, and UX — Retriever handles the data ingestion, indexing, search, and generation.

The permanent value of Retriever lies in its **data orchestrations, security boundaries, multi-tenant isolation, architectural abstraction layers, and the resilience with which it ingests, indexes, and synthesizes context**. It MUST serve as the reliable, reusable engine behind every client app.

### 1.2 Core Manifestos
Every engineer, contributor, and AI coding agent MUST adhere to the following foundational truths:
*   **Decoupling MUST Be Absolute:** Vendor integration MUST be hidden behind abstract interfaces. No third-party SDK, database client, or LLM-specific interface shall leak into core business logic.
*   **Code MUST Serve Two Intellects:** Code MUST be structured with obvious, flat composition to ensure readability for both human software engineers and parsing correctness for AI coding agents.
*   **Tenancy is an Inviolable Sanctuary:** The separation between tenant data spaces is absolute. Any cross-tenant data leakage, logic overlap, or configuration bleed MUST be treated as a system-critical, build-blocking failure.
*   **Performance is a Core Quality Attribute:** High-performance indexing, parallel query resolution, and fast response times are functional requirements, not secondary optimizations.
*   **Configuration Determines Personality:** The platform MUST remain fully headless and configurable at runtime. Behavior variations (such as prompts, models, chunks, and brand themes) MUST resolve dynamically from the configuration store per tenant, without modifying static code.
*   **API Key Is the Contract:** A single API key authenticates a client frontend. User identity within that frontend is the frontend's responsibility — passed as `X-User-ID` on every request. Retriever never manages user login, sessions, or passwords.

### 1.3 Guiding Principles
*   **Fail Fast and Loudly:** The system MUST fail immediately and throw explicit, structured errors at the point of failure, rather than passing null values downstream or hiding exceptions.
*   **Design for Disconnection:** Network calls to LLM providers and external databases will fail. Every adapter MUST implement strict timeout, retry, and circuit-breaker patterns.
*   **Stateless Execution:** The serving layer MUST remain completely stateless. All state (user sessions, chat history, transaction logs) MUST live in external cache or database systems to allow horizontal scaling.
*   **Acyclic Architecture:** Package dependencies MUST always flow in one direction. Circular dependencies are a sign of architectural decay and are strictly prohibited.
*   **Immutable Domain Models:** Core domain data models SHOULD represent immutable states of facts. Once a document chunk or inference log is written, it MUST NOT be modified in place. Changes MUST be managed through revision histories.

### 1.4 Engineering Decision Hierarchy
Whenever design principles or requirements conflict, engineers and AI coding agents MUST resolve the conflict by applying the following strict precedence:
1.  **Security:** Data encryption, access control, vulnerability management, and threat mitigation.
2.  **Correctness:** Functional accuracy of retrieval, deterministic processing, and validation of output states.
3.  **Tenant Isolation:** Complete separation of data, index metadata, cache space, and execution context between distinct organizations.
4.  **Reliability:** System availability, fault tolerance, connection pooling, and circuit breaker operation.
5.  **Maintainability:** Code readability, low package coupling, domain isolation, and comprehensive testing paths.
6.  **Simplicity:** Composition over inheritance, avoidance of magic/implicit variables, and ease of understanding.
7.  **Performance:** Optimization of parallel query paths, caching, latency budgets, and ingestion rates.
8.  **Developer Experience:** Intuitive APIs, self-documenting parameters, clean SDK designs, and comprehensive documentation.
9.  **Cost Optimization:** Model routing budgets, vector index sizing, and hardware/computational efficiency.

Under no circumstances MUST a lower-priority concern compromise or override a higher-priority concern. For example, performance optimizations MUST NOT introduce tenant isolation risks; developer convenience MUST NOT lead to maintainability regression; and cost reduction measures MUST NOT weaken correctness or security bounds.

---

## 2. Vision & Mission

### 2.1 Vision Statement
Retriever is the reusable backend engine that powers client-specific AI applications. A coaching institute uploads its textbooks → the coaching portal uses Retriever's RAG pipeline to answer students in the teacher's style. A CA firm configures their data → their automation tool retrieves client records instantly. An advocate uploads case law → their legal assistant finds relevant precedents.

Each frontend is a unique product. Retriever is the shared engine behind all of them, accessed through a single API key.

The platform must abstract document ingestion, indexing, retrieval, and generation into a simple API — so frontend developers can integrate it in one line of config and never think about embeddings, chunk boundaries, or vector search.

### 2.2 Mission Statement
Our mission is to build a modular, provider-agnostic, configuration-driven RAG engine that:

1. **Ingests, indexes, and retrieves** any client's data — documents, text, structured records.
2. **Isolates every client** (and their sub-clients) with strict RLS boundaries.
3. **Resolves all per-client configuration at runtime** — prompts, LLM keys, chunking, models — from the database, never from code.
4. **Exposes a simple REST API** that any frontend can call with one API key and an `X-User-ID` header.

We reject short-term convenience in favor of long-term architectural stability. Every engineering decision must ask: *does this make Retriever easier to integrate, harder to leak data across tenants, and simpler to deploy for a new client?*

---

## 3. Scope: What Retriever Is and Is Not

Scope boundaries prevent technical debt and guide development focus.

```
+---------------------------------------------------------------------------------+
|                                 RETRIEVER PLATFORM                              |
+---------------------------------------------------------------------------------+
|  +--------------------+   +---------------------+   +------------------------+  |
|  | Ingestion Pipeline |-->| Knowledge Indexing  |-->| Context Retrieval      |  |
|  | (Parsers/Sync)     |   | (Vector/Graph/Text) |   | (Hybrid/Re-ranking)    |  |
|  +--------------------+   +---------------------+   +------------------------+  |
|                                                                                 |
|  +--------------------+   +---------------------+   +------------------------+  |
|  | Inference Engine   |   | Multi-Tenant Auth   |   | Configuration Engine   |  |
|  | (LLM Orchestrator) |   | (RLS Enforcement)   |   | (Runtime Prompts/Brnd) |  |
|  +--------------------+   +---------------------+   +------------------------+  |
+---------------------------------------------------------------------------------+
        ^                                                                  ^
        | API Boundaries                                                   | API Boundaries
        v                                                                  v
+-----------------------+                                          +---------------------+
|   Downstream Clients  |                                          | Third-Party Vendors |
| (Web UI, SDKs, Slack) |                                          | (OpenAI, Pinecone)  |
+-----------------------+                                          +---------------------+
```

### 3.1 What Retriever Is
Retriever is a reusable, multi-tenant AI Knowledge Platform. It consists of:
*   **A Bounded Context for Ingestion (`domain.ingestion`):** An asynchronous pipeline designed to parse documents, extract layout information, convert binaries to standardized schemas, and redact PII.
*   **A Bounded Context for Knowledge (`domain.knowledge`):** An indexing management system that handles chunking boundaries, parent-child hierarchies, document relationships, and metadata classification.
*   **A Bounded Context for Retrieval (`domain.retrieval`):** A high-performance query service executing hybrid search, combining vector embeddings and sparse text matching, and applying reranking and reciprocal rank fusion.
*   **A Bounded Context for Inference (`domain.inference`):** An orchestration engine managing conversation histories, model routing, system prompt composition, tool definitions, and schema verification.
*   **A Headless Service Layer:** A collection of versioned REST endpoints, Server-Sent Events (SSE) channels, and SDKs.

### 3.2 What Retriever Is NOT
To prevent scope creep, we define what Retriever is not:
*   **Not a Client-Specific Assistant:** Retriever is not a coaching assistant, a CA (Credit Analyst) tool, a legal document parser, or a medical diagnostic summarizer. It is the *engine* upon which those specific assistants are constructed. Client frontends own the UX, branding, and user auth. Retriever owns the data pipeline and RAG logic.
*   **Not a Frontend or User Interface:** Retriever has no client-facing UI, no login page, no signup flow. It has an admin dashboard (for platform management) and a REST API. Client frontends are separate products built by you or your clients.
*   **Not a Wrapper-as-a-Service:** We do not simply forward raw HTTP requests to OpenAI. We build internal intelligence around chunking hierarchies, retrieval algorithms, and schema-enforced output generation.
*   **Not a Model Hosting Provider:** Retriever does not train or host base foundation models. We interface with external model providers through standardized adapter layers.
*   **Not an ETL/Data Warehouse:** Retriever is not designed to perform bulk analytics or data warehouse computations. It is an indexer and context synthesizer optimized for reasoning.

---

## 4. Goals & Non-Goals

### 4.1 Short-Term Goals (Next 3 Milestones)
1.  **Client Hierarchy & Admin API:** Introduce a `users` table with `user_id` and `tenant_id`. Chat data isolated by `user_id` within a tenant. Admin API scoping (admin keys bypass user filter, client keys are scoped to their tenant). Per-tenant LLM key storage (encrypted) configurable via admin API.
2.  **Admin Dashboard:** A Next.js admin UI for platform management — create tenants, manage users, configure prompt templates, set per-client LLM keys and models, browse documents uploaded by each client, preview RAG responses using a tenant's current config.
3.  **Client SDK & API Surface:** A lightweight JS/TS `RetrieverClient` that frontend developers integrate in one line. Cursor-based pagination, rate limit headers, OpenAPI 3.1 spec.

### 4.2 Long-Term Goals (1+ Years)
1.  **API Stability & Longevity:** The core contracts and APIs of Retriever must remain structurally backward-compatible for at least five years, ensuring downstream applications can run without code churn.
2.  **Sub-100ms Ingestion-to-Search Availability:** Documents ingested into the platform must be processed, embedded, indexed, and queryable in less than 100 milliseconds at scale.
3.  **Production Storage:** Swap local filesystem for S3/MinIO with tenant-prefixed buckets. Encrypted LLM key persistence. Connection pool auto-tuning.
4.  **Multi-Industry Configurability:** Per-tenant chunking strategies, metadata extractors, input/output guardrails, citation formatting, and model routing — all configured at runtime, not hardcoded.
5.  **Performance & Scale:** HNSW index tuning, semantic query cache, bulk document ingest, SSE lifecycle management. Handle 200 concurrent search requests under 150ms latency budget.
6.  **Enterprise Readiness:** Audit log writer, SSO/OIDC, RBAC expansion, data retention/backup/restore, immutable audit trail. SOC2 alignment for regulated clients.

### 4.3 Non-Goals
1.  **Building Custom Core Infrastructure:** We will not write custom vector database engines or custom parsing libraries from scratch. We leverage existing high-quality open-source and cloud infrastructure.
2.  **Serving General-Purpose Web Pages:** Retriever will not serve standard web pages, marketing sites, or user blogs. It is strictly an API-driven knowledge platform.
3.  **Direct Integration with Legacy ERP/CRM Systems:** Retriever will not build hundreds of bespoke connectors for legacy enterprise software. Instead, it defines a standard webhook and ingestion API format, pushing the responsibility of push-based synchronization to the data source or middleware.
4.  **User Authentication or Session Management:** Retriever does not manage user login, passwords, sessions, or MFA. Client frontends own their authentication. Retriever requires only an API key (identifies the client tenant) and an `X-User-ID` header (identifies the user within that tenant).
5.  **Training Custom Base Models:** We do not engage in the research, training, or base fine-tuning of generative language models. We orchestrate existing models.

### 4.4 Architectural Anti-Goals
To prevent long-term scope creep and maintain architectural focus, Retriever MUST NOT evolve into any of the following systems:
*   **A Workflow Automation Platform:** Retriever MUST NOT implement dynamic visual workflow builders, business process orchestration layers, or multi-app integration triggers.
*   **A Business Intelligence (BI) Platform:** Retriever MUST NOT provide charting dashboards, analytical reporting tools, aggregators, or custom metrics engines.
*   **A Custom Database:** Retriever MUST NOT write custom storage engines, indexing algorithms, or raw database runtimes.
*   **A General Backend Framework:** Retriever MUST NOT function as a generic API framework for serving blogs, managing general-user commerce, or handling unrelated web application backends.
*   **A Low-Code / No-Code App Builder:** Retriever MUST NOT implement visual UI drag-and-drop interfaces, form builders, or application generation portals.
*   **An AI Model Training Platform:** Retriever MUST NOT build fine-tuning tools, hyperparameter optimization clusters, or model training execution pipelines.

Features, pull requests, or proposed modifications that steer the platform toward these directions SHOULD be rejected unless they directly strengthen Retriever's core mission as an AI Knowledge Platform.

---

## 5. Product & Design Philosophy

### 5.1 Product Philosophy
*   **Platform + Client App Model:** Retriever is the engine. Client frontends are the products. Each frontend integrates via a single API key + `X-User-ID` header. Retriever never manages user auth, sessions, or the frontend's UI decisions.
*   **Composability:** Every domain component MUST be structured to function independently. Downstream teams MUST be able to utilize our ingestion pipeline without using our inference engine, or use our retrieval domain with their own custom UI orchestration.
*   **Developer-First Design:** The APIs, SDKs, and configuration schemas are our core products. They MUST be intuitive, self-documenting, and strongly typed.
*   **Configuration Over Code:** System changes MUST be driven by data stored in configurations, not code modifications. Prompt revisions, chunking variations, similarity weights, and LLM routes MUST be adjustable in the database at runtime.
*   **API Key Is the Contract:** A client frontend authenticates with a single API key. That key identifies the tenant. The frontend passes `X-User-ID` to distinguish sub-clients. Per-tenant LLM keys and model selection are stored in the database, configurable via admin API — the frontend doesn't need to know about them. On override: a frontend can pass `X-LLM-Key` to use their own provider without admin involvement.

### 5.2 Design Principles for Reference UIs
Although Retriever is headless, we provide starter applications and playground UIs. These reference systems MUST follow these visual design rules:
*   **Aesthetic Quality:** Interfaces MUST feel premium and clean. Typography MUST use modern sans-serif fonts (e.g., Inter, Geist, or Outfit) loaded from reliable sources.
*   **Consistent Design Tokens:** Use a unified system of CSS tokens for layouts, gaps, border radii, and color palettes. Avoid hardcoded tailwind values or CSS overrides.
*   **Adaptive Theme System:** Dark mode and light mode MUST use refined HSL-tailored slate, charcoal, and warm gray backdrops, avoiding plain black and white. Use subtle contrast markers (e.g., subtle card borders, glassmorphic backdrop filters) to establish layout hierarchy.
*   **Responsive Adaptation:** Reference layouts MUST adapt cleanly to all mobile, tablet, and desktop viewports, using CSS container queries for components.
*   **Micro-Animations:** Interactive elements MUST use smooth transition curves (sub-200ms) on hover and focus states. Long-running actions (such as file processing or embedding updates) MUST use custom progress indicators, not generic loading spinners.

---

## 6. Architectural & Structural Philosophy

### 6.1 Architectural Philosophy
The core architecture of Retriever is based on the **Ports and Adapters (Hexagonal)** model. The central application contains the core domain logic, entirely isolated from communication frameworks, database systems, third-party libraries, and execution runtimes.

By maintaining a strict hexagonal boundary, we ensure that changes in external infrastructure (such as moving from a cloud-hosted vector database to a self-hosted vector database cluster) do not require a single line of modification to the business rules. The application core exposes formal "Ports" (Interfaces). External systems connect to these ports using "Adapters".

```
                                  PORTS & ADAPTERS ARCHITECTURE
               
               +-------------------------------------------------------------+
               |                       Adapters Layer                        |
               |                                                             |
               |   +-------------+      +-------------+      +-----------+   |
               |   |   FastAPI   |      |  Next.js    |      | CLI Tool  |   |
               |   +-------------+      +-------------+      +-----------+   |
               +----------|--------------------|-------------------|---------+
                          |                    |                   |
                          | (HTTP/SSE)         | (JSON/RPC)        | (Exec)
                          v                    v                   v
               +-------------------------------------------------------------+
               |                         Ports Layer                         |
               |                                                             |
               |     [IngestionPort]  [RetrievalPort]  [InferencePort]       |
               +-----------------------------|-------------------------------+
                                             |
                                             v
               +-------------------------------------------------------------+
               |                          Core Domain                        |
               |                                                             |
               |    +------------+      +------------+      +------------+   |
               |    | Ingestion  |      | Retrieval  |      | Inference  |   |
               |    |   Logic    |      |   Logic    |      |   Logic    |   |
               |    +------------+      +------------+      +------------+   |
               |          |                   |                   |          |
               |          +-------------------+-------------------+          |
               |                              |                              |
               |                              v                              |
               |                     [Identity Boundary]                     |
               +------------------------------|------------------------------+
                                              |
                                              v
               +-------------------------------------------------------------+
               |                  Infrastructure Ports                       |
               |                                                             |
               |    [VectorPort]      [IdentityPort]     [CognitivePort]     |
               +-----------------------------|-------------------------------+
                                             |
                                             v
               +-------------------------------------------------------------+
               |                  Infrastructure Adapters                    |
               |                                                             |
               |   +-------------+      +-------------+      +-----------+   |
               |   |  pgvector   |      | Supabase Auth|     |OpenAI/Anth|   |
               |   +-------------+      +-------------+      +-----------+   |
               +-------------------------------------------------------------+
```

### 6.2 Domain-Driven Modular Architecture (DDMA)
We organize Retriever into isolated, bounded contexts, each owning its models, rules, and logic boundaries.
*   **Ingestion Bounded Context (`domain.ingestion`):** Transforms binary data payloads (e.g., PDF, DOCX, HTML streams) into structured plaintext schemas. This context MUST remain isolated from indexing systems.
*   **Knowledge Bounded Context (`domain.knowledge`):** Manages structural models of text chunks, embedding associations, tag assignments, parent-child relationships, and hierarchical structures.
*   **Retrieval Bounded Context (`domain.retrieval`):** Merges vector similarity results and sparse keyword search queries. It executes metadata filtering, semantic matching, and reranking.
*   **Inference Bounded Context (`domain.inference`):** Coordinates interactions with cognitive engines. It handles conversation history compression, prompt packaging, system prompt injection, tool calling orchestration, and token calculation.
*   **Identity Bounded Context (`domain.identity`):** Enforces tenancy rules, resolves API keys, and validates access levels.

#### Directional Dependency Rules
1.  Dependencies MUST flow strictly downward toward abstractions (`domain.abstractions`).
2.  No core domain context shall import database models, client libraries, or connection details from other domains. Inter-domain communication MUST use defined interfaces or domain events.
3.  No domain module shall import code from the presentation or serving layers. The serving layer is strictly an entry point.

### 6.3 Event-Driven Architecture (EDA) & Eventual Consistency
To ensure scalability and decouple ingestion, indexing, and retrieval tasks, Retriever utilizes an Event-Driven Architecture.
*   **Asynchronous Event Bus:** Core domains publish domain events (e.g., `DocumentIngested`, `ChunkIndexed`, `InferenceCompleted`) to a message bus. Message delivery MUST implement at-least-once delivery guarantees.
*   **Eventual Consistency:** Document ingestion and vector indexing operate under an eventual consistency model. After a document is uploaded, it is parsed, chunked, and indexed asynchronously. Downstream clients MUST be designed to handle the delay between upload and query availability.
*   **Idempotency:** All event handlers MUST be idempotent. The Ingestion and Indexing domains MUST check document hashes and chunk content hashes before running parsing or embedding tasks, preventing duplicate computations.

### 6.4 Command Query Responsibility Segregation (CQRS)
Retriever implements CQRS to separate read and write operations, optimizing performance and throughput:
*   **Write Path:** Document ingestion, chunk parsing, metadata enrichment, and vector database updates flow through a dedicated write pipeline. This pipeline MUST prioritize data validation, security checks, audit logging, and reliability.
*   **Read Path:** Similarity searches, hybrid queries, reranking, and synthesis routing flow through a read pipeline. This pipeline MUST be optimized for latency, using connection pools, query caching, parallel search executions, and streaming serving.
*   **Data Isolation:** The database schemas MUST support separate query indices and read-replica routing to ensure heavy write operations (e.g., indexing a new document library) do not degrade the performance of real-time search queries.

---

## 7. Provider Abstraction & Technology Neutrality

### 7.1 Provider Abstraction Philosophy
Retriever MUST remain technology-neutral. Technology decisions (such as Next.js, TypeScript, Tailwind, shadcn/ui, FastAPI, PostgreSQL, Supabase, pgvector, Supabase Auth, SSE, local or cloud embeddings, and LLM providers) represent the initial implementation choices and references, not architectural foundations.

Every external service, database, or API MUST connect to the core through abstract ports. Changing an underlying system (e.g., switching database engines or model endpoints) MUST only require writing a new adapter class, without modifying the core business logic.

```
       +-------------------------------------------------------------+
       |                         Core Domain                         |
       +-------------------------------------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |             [LlmProvider Interface (Port)]                  |
       +-------------------------------------------------------------+
                        /                           \
                       v                             v
       +-------------------------------+   +-------------------------+
       |    OpenAiLlmAdapter           |   |   AnthropicLlmAdapter   |
       |  (Translates to OpenAI API)   |   | (Translates to Claude)  |
       +-------------------------------+   +-------------------------+
```

### 7.2 Core Interface Contracts

The actual port interfaces live in `apps/api/src/domain/abstractions/`. Below are the target interface signatures — aspirational design contracts that the codebase grows toward. The actual Python classes may have fewer methods; see the individual files for the current implementation.

**Current port locations:**
- LLM/Cognitive: `domain/abstractions/inference.py` (`LlmProvider`)
- Vector Store: `domain/abstractions/retrieval.py` (`VectorSearchProvider`, `EmbeddingProvider`, `RerankerProvider`)
- File Storage: `domain/abstractions/ingestion.py` (`DocumentStorage`)
- Identity & Tenant: `domain/abstractions/identity.py` (`IdentityProvider`, `UserContext`)
- Configuration: `domain/abstractions/config.py` (`ConfigRegistry`, `TenantConfiguration`)
- Events: `domain/abstractions/events.py` (`EventPublisher`)
- Telemetry: `domain/abstractions/telemetry.py` (`Tracer`, `MetricsRegistry`, `RateLimiter`)

**Aspirational target interfaces:**

#### 1. Cognitive Service Interface (`domain.abstractions.inference`)
```typescript
export interface ChatMessage {
  readonly role: 'system' | 'user' | 'assistant' | 'tool';
  readonly content: string;
  readonly name?: string;
  readonly toolCalls?: readonly ToolCall[];
}

export interface LlmProvider {
  generate(request: InferenceRequest): Promise<InferenceResponse>;
  generateStream(request: InferenceRequest): AsyncIterable<string>;
}
```

#### 2. Vector Store Interface (`domain.abstractions.retrieval`)
```typescript
export interface VectorSearchProvider {
  searchSimilar(query: VectorQuery): Promise<readonly SearchResult[]>;
}
```

#### 3. File Storage Interface (`domain.abstractions.ingestion`)
```typescript
export interface DocumentStorage {
  save_file(path: string, content: bytes, tenant_id: str) -> str;
  delete_file(path: string, tenant_id: str) -> None;
}
```

#### 4. Identity & Access Interface (`domain.abstractions.identity`)
```typescript
export interface IdentityProvider {
  validate_token(token: str) -> UserContext;
  create_api_key(tenant_id: str, scope: str) -> ApiKey;
  revoke_api_key(key_id: str) -> None;
}
```

---

## 8. Context Assembly & Inference Execution Philosophy

Retriever is designed as an AI infrastructure platform, not a simple wrapper for chatbot interactions. The compilation, routing, execution, and validation of context MUST follow precise architectural guidelines.

```
       INGESTION AND INDEXING PIPELINE (WRITE PATH)
       [Binary PDF/HTML] -> [Parsed Schema] -> [Hierarchical Chunks] -> [Embeddings Engine] -> [Vector Store]
       
       RETRIEVAL AND SYNTHESIS PIPELINE (READ PATH)
       [User Query] -> [Hybrid Retrieval & Metadata Filter] -> [Reranking Engine] -> [Context Assembly] -> [Guardrails] -> [LLM Route] -> [Structured Output Verification] -> [SSE Stream]
```

### 8.1 Ingestion, Knowledge, and Retrieval Engine
The write path handles unstructured text transformation, while the read path handles real-time contextual synthesis.
*   **Ingestion Pipeline:** Binary documents are parsed in-process by default. A sandboxed parsing environment (container-based isolation) is planned for untrusted document handling in production.
*   **Knowledge Indexing:** Text chunks MUST be organized hierarchically. Parent-child relationships MUST link small chunks (e.g., 200 tokens) to larger context blocks (e.g., 1000 tokens), allowing precise semantic matches to retrieve surrounding context.
*   **Hybrid Search:** Queries MUST run keyword search (sparse BM25 indexing) and semantic search (dense vector indexing) in parallel. The results MUST be merged using Reciprocal Rank Fusion (RRF) and metadata filters before reranking.

### 8.2 Prompt Architecture & Context Assembly
Prompt composition MUST be handled systematically, separating instructions from context variables.
*   **Dynamic Prompt Registry:** Prompt templates MUST be stored as structured configuration in the database. Hardcoding prompts in application source code is prohibited.
*   **Prompt Layering:** Prompt templates MUST be composed of four isolated layers:
    1.  **System Guidelines:** Permanent behavioral instructions (e.g., code output formatting, compliance limits).
    2.  **Persona Definitions:** Role definition parameters configured at the tenant level (e.g., Tone, Scope).
    3.  **Context Blocks:** Grounding data retrieved from the vector or document stores.
    4.  **User Inputs:** Raw user query strings.
*   **Context Window Packaging:** The Inference domain MUST check the token usage of context documents before calling the LLM. If the payload size exceeds the model's limit, the system MUST apply a context compression policy (e.g., prioritizing highest-scoring chunks, summarizing older chat history) to fit within safety limits.

### 8.3 Grounding & Citation-First Generation
To minimize hallucinations and verify outputs, generated answers MUST be directly grounded in retrieved context:
*   **Grounding Verification:** Every generated response MUST refer directly to retrieved context documents. The system MUST verify that claims in the output match specific document sources.
*   **Citation-First Generation:** Prompts MUST instruct the LLM to format citations inline (e.g., `[Source ID]`). The Inference domain MUST verify these citation links before sending the output to the client. Responses containing unresolvable citations MUST trigger an auto-correction pass or return a validation error.
*   **Structured Outputs:** When structured data is required (e.g., JSON schemas), the platform MUST enforce strict formatting using model-guided routing (e.g., JSON mode) and validate the resulting output against JSON schema schemas before returning it.

### 8.4 Model Routing, Guardrails, & Tool Execution
*   **Model Routing:** The system MUST resolve the optimal model route dynamically per query. Routing choices MUST balance cost, latency, and capability requirements (e.g., routing simple queries to lightweight models, and complex reasoning to larger models).
*   **Dynamic Guardrails:** Inputs and outputs MUST be checked by real-time safety guardrails. Input guardrails MUST block prompt injections, while output guardrails MUST redact PII and flag potential hallucinations.
*   **Structured Tool Execution:** When a model requests tool execution, the orchestration engine MUST validate the request against tenant permission scopes. The execution environment MUST run tools in isolated contexts with strict resource limits.
*   **Human-in-the-Loop Workflows:** If a tool call or action requires verification (e.g., modifying database records), the Inference engine MUST pause execution, persist state, and wait for manual approval through a standard API hook.

---

## 9. Configuration & Repository Philosophy

### 9.1 Configuration Philosophy
We enforce a strict separation between boot-level system configuration and runtime tenant configuration:
*   **Boot-Level System Configuration:** Handled via environment variables or cloud secret managers at startup. This configuration manages infrastructure connection strings, base API keys, log levels, and cloud regions.
*   **Runtime Tenant Configuration (Configuration as Data - CAD):** Stored in the database and loaded dynamically per request based on the tenant context.

CAD parameters manage tenant-specific behavior, including:
*   Prompt templates and system guidelines.
*   Cognitive models, temperatures, and token limits.
*   Chunking parameters (e.g., sizes, overlap, parsing options).
*   Retrieval settings (e.g., RRF weights, reranking models, metadata filters).
*   Downstream brand variables and reference UI styling settings.

### 9.2 Repository Organization Philosophy
Retriever is structured as a monorepo to maintain strong typing across client-server boundaries while isolating build environments:
*   **Strict Monorepo Boundary Enforcement:** The backend API codebase (`apps/api` in Python) and the frontend codebase (`apps/web` in Next.js) MUST be fully isolated. They MUST share information only through type contracts and client libraries.
*   **Clean Dependency Lockfiles:** A shared lockfile MUST manage dependencies in each language context. Independent builds MUST be deployable as isolated docker containers.
*   **Artifacts and Documentation Isolation:** Configuration documents, ADRs, engineering diagrams, and design rules MUST live under `docs/` and be versioned alongside the code.

### 9.3 Versioning & Migration Philosophy
API contracts and database schemas MUST follow a clear evolution path:
*   **Semantic API Versioning:** External APIs MUST use versioned paths (e.g., `/v1/query`, `/v2/query`). Breaking changes to an endpoint require the creation of a new path.
*   **Database Schema Evolution:** All database changes MUST be managed via migration files. Schema updates MUST support backwards compatibility, allowing older API service instances to continue operating during a rolling deployment.
*   **Data Migration Paths:** Migration plans MUST include a fallback strategy to reverse database schema updates if an issue occurs.
*   **API Deprecation Policy:** When an API version is deprecated, it MUST trigger warnings in logs and API headers. Deprecated features MUST be maintained for at least six months or until the next major release.

---

## 10. Developer, Code, & Documentation Philosophy

### 10.1 Human-First Code Philosophy
Code MUST be designed for readability and simplicity.
*   **No Dynamic Metaprogramming:** Avoid decorator-heavy magic, monkey-patching, or dynamic runtime variable creation. Explicit imports, manual dependency injection, and clean function signatures are preferred.
*   **Small Functions:** Functions MUST be small, focused, and perform exactly one logical action. If a function is longer than 40 lines, it MUST be evaluated for decomposition.
*   **Obvious Naming Over Short Names:** Do not use short, cryptic variable names. Use `documentInvertedIndex` instead of `dIdx`.
*   **Explicit Error Definitions:** Avoid raising general assertions. Create domain-specific exceptions (e.g., `ChunkingBoundaryOverlapError`) and document them.

### 10.2 AI-First Development Philosophy
To enable AI coding agents to edit and verify code safely:
*   **No Code Without Types:** In TypeScript, the `any` keyword is banned. In Python, all functions MUST have type hints for every parameter and return value.
*   **Strict Standard Layout:** Every module file MUST follow an identical structural layout:
    1.  Imports (Standard Libraries, External Packages, Local Imports).
    2.  Constant definitions.
    3.  Interface definitions.
    4.  Class definitions (Properties, Constructor, Private methods, Public methods).
    5.  Export declarations.
*   **Small File Boundaries:** Keep files small. Avoid modules containing thousands of lines of code. This allows AI tools to parse, analyze, and write replacements without hitting context limits or making truncation mistakes.

### 10.3 Documentation Philosophy
Documentation is treated as code. If a feature is not documented, it does not exist.
*   **Architecture Decision Records (ADRs):** Any change affecting directory structure, tech stack, database schemas, or API boundaries MUST be documented via an ADR under `docs/adr/`.
*   **Inline Documentation:** Every public module, class, and method MUST contain clear docstrings explaining its parameters, return values, exceptions raised, and usage examples.
*   **Continuous Updates:** README files and architecture plans MUST be updated in the same pull request that introduces the code changes.
*   **Visual Documentation:** Complex system interactions (such as the flow of multi-step retrieval or tenancy authentication cycles) MUST be documented using Mermaid diagrams embedded directly within the markdown documentation.

### 10.4 Engineering Decision & Technical Debt Philosophy
*   **Engineering Decision Process:** Architectural adjustments MUST be proposed via RFC (Request For Comments) documents and recorded in ADRs. Changes require review and approval from at least two core maintainers.
*   **Technical Debt Management:** We allocate a fixed capacity (e.g., 20% of engineering resources) to addressing technical debt and upgrading dependencies.
*   **Refactoring Boundaries:** Refactoring MUST focus on improving code readability and structural isolation, rather than changing functional behavior.

---

## 11. Dependency & Library Management Philosophy

Dependencies are technical debt in disguise. Unmanaged third-party libraries introduce vulnerabilities, performance bloat, and build instabilities.

1.  **The Dependency Tax:** Before introducing any new third-party dependency, the developer MUST justify why the code cannot be written using standard library functions or existing codebase utilities.
2.  **Strict Lockfiles:** All environments MUST use strict lockfiles. Floating dependency versions (e.g., `^1.2.0`) in production builds are banned.
3.  **No Direct Import of Vendor SDKs in Domain Code:** No file outside the `adapters` folder may import an external SDK package. If you need to parse a PDF, you do not import parsing libraries in the ingestion logic. You import `IngestionParser` interface, which is implemented in `adapters.parsers`.

---

## 12. Testing & Quality Evaluation Philosophy

A platform orchestrating non-deterministic models (LLMs) requires a multi-tiered testing strategy. We divide testing into three distinct layers: deterministic code testing, integration testing, and non-deterministic evaluation.

```
       +---------------------------------------------+
       |   LLM Evaluation (Ragas, LLM-as-a-Judge)    | <-- Non-deterministic
       +---------------------------------------------+
                              |
       +---------------------------------------------+
       |   Integration & Contract (E2E API Tests)    |
       +---------------------------------------------+
                              |
       +---------------------------------------------+
       |   Unit & Property (Mock Adapters, Pure logic)| <-- Fully deterministic
       +---------------------------------------------+
```

### 12.1 Deterministic Testing (Unit & Integration)
*   **100% Coverage on Core Logic:** All business rule components in `domain.ingestion`, `domain.knowledge`, and `domain.identity` MUST maintain 100% unit test coverage.
*   **Mocking Adapters:** Unit tests MUST use mock implementations of adapters (e.g., an in-memory vector database mock) to ensure unit tests run in milliseconds without network calls.
*   **Contract Testing:** All API endpoints MUST run automated integration tests validating that responses match the OpenAPI contract.

### 12.2 Non-Deterministic Testing (LLM Evaluation)
Since LLM outputs are probabilistic, traditional assert statements fail. We now implement an automated evaluation pipeline:

*   **Frameworks (both active):**
    *   **RAGAS** — Evaluates faithfulness, answer_relevancy, context_precision, context_recall.
    *   **DeepEval** — Evaluates hallucination, toxicity, bias.
*   **Search Metrics (pure math, no LLM needed):** nDCG@10, MRR, hit_rate@10 computed per query.
*   **Ground-Truth Datasets:** Per-tenant `eval_datasets` + `eval_questions` tables with admin CRUD API.
*   **Execution:** On-demand via admin API (`POST /v1/admin/tenants/{t}/eval-datasets/{d}/run`) and scheduled nightly via Celery beat.
*   **LLM-as-Judge:** Both RAGAS and DeepEval use `gemini-1.5-flash` as the lightweight judge model.
*   **Regression Testing (aspirational):** A golden evaluation dataset of 200 standard user queries evaluated before every release. Any drop in evaluation scores is a build-blocking event. Not yet automated in CI — requires admin API call to trigger.

---

## 13. Performance & Scalability Philosophy

### 13.1 Performance Budgets
We establish clear latency targets for our core pipelines, measured under concurrent request loads:

```
Total Latency Target: <= 800ms
├── Network & Auth Resolution : 50ms
├── Vector Retrieval & Rerank : 150ms
└── LLM Time-to-First-Token   : 600ms (Stream begins)
```

These values represent design performance budgets, not rigid runtime guarantees. The platform MUST design interfaces to degrade gracefully if these targets are exceeded (e.g., by returning cached retrieval results or falling back to lightweight models).

### 13.2 Concurrency & Backpressure
*   **Parallel Query Resolution:** Hybrid searches (keyword + semantic) MUST run concurrently using async-await libraries, combining results using RRF.
*   **Throttling and Circuit Breakers:** To protect external services, adapters MUST implement rate-limiting checks and circuit breakers. If an external service fails repeatedly, the adapter MUST open the circuit and route queries to a fallback provider.
*   **Asynchronous Processing:** Long-running write path jobs (such as document ingestion or bulk vector updates) MUST execute asynchronously in background task queues, keeping the main HTTP threads free to handle search queries.

### 13.3 Caching & Resource Optimization
*   **Dynamic Caching Policies:** Avoid duplicate embedding calculations. The system MUST cache document chunks based on their content hash. If a document changes, the indexing pipeline only generates embeddings for modified chunks.
*   **Retrieval Cache:** The platform SHOULD support a cache layer for search results. Identical queries within a configured time limit SHOULD resolve from the cache, avoiding redundant database indexing and vector search costs.

---

## 14. Security, Privacy, & Compliance Philosophy

### 14.1 Tenant Isolation Models
Retriever uses PostgreSQL Row-Level Security (RLS) for tenant isolation — the only isolation tier currently implemented. Schema-level and physical isolation are aspirational targets for enterprise clients.

| Isolation Tier | Status | Description | Implementation Details |
|---|---|---|---|
| **Logical Isolation** | **Implemented** | Single database, shared schemas. RLS filters all reads and writes. | PostgreSQL RLS enabled on all customer-data tables. Queries run through `tenant_session()` context setting `app.current_tenant_id` and `app.current_user_id`. |
| **Schema Isolation** | Planned | Single database, isolated schemas per tenant. | Dynamically created database schemas. Connection pool switches schema context per request. |
| **Physical Isolation** | Planned | Dedicated database clusters per tenant. | Configuration maps tenant ID to distinct connection strings. |

> [!CAUTION]
> **RLS Bypass Prevention:** All database queries MUST run through transaction contexts that explicitly set the user and tenant variables. Direct connection to the database with the superuser role is strictly forbidden in application runtime.

### 14.2 User-Level Isolation (Sub-Client Model)
Within a tenant, individual users have private chat data:
*   **Data scoped by `user_id`:** `chat_sessions`, `chat_messages`, and `inference_logs` are filtered by `user_id` within the tenant.
*   **Documents remain at tenant level:** All users within a client tenant share access to the client's knowledge base.
*   **Admin API bypasses user filter:** Admin-scoped API keys see all users' data. Client-scoped keys see their tenant's data, filtered by the `X-User-ID` header value.
*   **Frontend owns user identity:** Retriever never creates, authenticates, or manages users. The client frontend passes `X-User-ID` on every request.

### 14.3 Privacy by Design & Compliance Readiness
*   **PII Sanitization:** The ingestion pipeline MUST scan incoming documents for PII (Personally Identifiable Information) and apply dynamic redaction rules before text is vectorized and stored.
*   **Data Lifecycle Policies (Data Retention & TTL):** Customer data MUST have configurable Time-To-Live (TTL) values. Expired documents, chunks, and chat history MUST be scrubbed automatically from relational tables and vector databases.
*   **Erasure Requests:** The storage and retrieval domains MUST implement API endpoints to support "Right to be Forgotten" requests, ensuring complete removal of a user's data from vector indexes, cached buffers, and primary storage systems.
*   **Compliance Readiness (SOC2 / HIPAA):** System designs MUST maintain immutable audit logs of all access requests, model configurations, and ingestion jobs. Encryption at rest and encryption in transit are required across all communication paths.

---

## 15. Resilience, Reliability, & Disaster Recovery

### 15.1 Resilience Engineering
*   **Rate Limiting & Backpressure:** The API serving layer MUST enforce tenant-specific rate limits to prevent resource exhaustion. If client requests exceed limits, the system MUST apply backpressure by returning HTTP `429 Too Many Requests`.
*   **Graceful Degradation:** If downstream dependencies fail (such as a reranking service or custom translation service), the system MUST degrade gracefully (e.g., returning hybrid search results without reranking), rather than failing the entire request.
*   **Outage Failovers:** The system MUST implement circuit breakers on external cognitive model APIs. If a provider experiences an outage, the system MUST redirect queries to a fallback model or self-hosted model gateway.

### 15.2 Disaster Recovery (DR) & Business Continuity
*   **Database and Storage Backup:** Periodic backups of databases and configuration registries are required. Backups MUST be replicated to distinct regions to support disaster recovery scenarios.
*   **Re-vectorization from Relational Database:** Retriever stores raw document chunks in relational tables separate from the vector database. If a vector store index is corrupted or lost, the system MUST run automated re-vectorization scripts to rebuild the index from the relational database without requiring users to upload documents again.
*   **Recovery Time Objective (RTO) and Recovery Point Objective (RPO):** The platform MUST establish design targets for disaster recovery: RTO under 4 hours and RPO under 1 hour.

---

## 16. System Failure & Recovery Protocols

Systems fail. In the world of distributed AI applications, failure patterns are more complex due to the combination of network latency, rate limits, model degradation, and structured format violations. We define clear procedures to handle these failures gracefully.

### 16.1 Cognitive Engine Outage Protocol
When an LLM provider endpoint encounters an outage, latency spike, or persistent rate-limiting (HTTP `429 Too Many Requests`), the Inference domain MUST execute an automatic failover:
1.  **Fallback to High-Availability Local Engines:** If the tenant configuration specifies fallback options, requests MUST route to a secondary local or self-hosted model adapter in under 500ms.
2.  **User-Facing Degraded Mode:** If no secondary adapter is available or responsive, the API MUST abort generation and send a structured event payload indicating `PROVIDER_UNAVAILABLE` over the SSE stream, rather than timing out the HTTP channel.

### 16.2 Memory and Vector Index Loss Recovery
In the event of a vector database index corruption or complete hardware loss:
1.  **Re-vectorization from Raw Store:** Retriever's core architecture maintains a primary document chunk store (in relational tables) distinct from the vector database. In case of index loss, the platform MUST support an automated command execution pipeline that reads raw chunks and broadcasts re-indexing jobs across workers, restoring search functionality without requesting document re-ingestion.

---

## 17. Non-Negotiable Engineering Rules & System Failure Protocols

To prevent technical debt and protect tenant data, we define fifteen non-negotiable rules.

### 17.1 The Tenancy Breach Kill-Switch
If the system detects that a query context, document chunk, or database operation contains a `TenantId` that does not match the active authenticated tenant:
1.  **Halt execution immediately.** Severe active database connections and abort transactions.
2.  **Log a Severity-1 incident.** Send a structured JSON payload to the logging backend marked as `CRITICAL_SECURITY_BREACH`. Do not log the actual data payload to prevent secondary leakage.
3.  **Invalidate authentication credentials.** Instantly block the API key or authentication token associated with the caller immediately.
4.  **Raise a TenantIsolationViolationError.** Return a generic `403 Forbidden` response to the client.

### 17.2 Architecture Conformance Tests
Architecture conformance tests live in `tests/test_architecture.py` and run as part of `pytest tests/`. These enforce:
*   Domain files must not import adapters, FastAPI, SQLAlchemy, or other infrastructure frameworks.
*   No hardcoded system prompt strings exist in source code.
*   (Extend this file when adding new architectural rules — it's cheaper than docs.)

The CI pipeline runs all tests on every push. Architecture violations block the build.

### 17.3 The Fifteen Non-Negotiable Rules
1.  **Every Integration MUST Be Abstracted:** No raw vendor SDK imports are allowed in business logic.
2.  **All Database Tables Containing Customer Data MUST Have RLS Active:** The default database migration MUST enforce policy restrictions.
3.  **All API Communications Containing AI Completions MUST Stream Over Server-Sent Events.**
4.  **Circular Package Dependencies are Build-Blocking Compilation Errors.**
5.  **All API Endpoints MUST Run Integration Tests Validating OpenAPI Compliance.**
6.  **Raw Prompt Strings MUST NOT Be Hardcoded in the Source Code:** They MUST be loaded from DB configuration tables.
7.  **Secrets, Customer Keys, and PII MUST NOT Be Output to Application Logs.**
8.  **Every Transaction MUST Generate, Pass, and Log a Unique Trace ID.**
9.  **No Code May Be Merged if the Golden Test Dataset Evaluation Score Drops Below the Established Baseline.**
10. **The Web Frontend MUST NOT Directly Access the Relational Database:** All data access MUST pass through the API gateway.
11. **Idempotency checks are required on the document ingestion write path.**
12. **All network calls to external APIs MUST implement timeouts (maximum 10 seconds) and retry budgets.**
13. **Every domain model MUST be immutable once persisted to storage.**
14. **Structured JSON completions MUST be validated against JSON Schema definitions prior to client delivery.**
15. **The ingestion pipeline MUST execute binary document parsing inside isolated sandbox containers.**

---

## 18. The North Star Statement

Retriever succeeds when you can spin up a new client frontend — coaching portal, CA assistant, legal tool — by creating a tenant, generating an API key, and pointing the frontend at the API. No code changes. No new deployments. No understanding of embeddings, vector search, or prompt engineering required from the frontend developer.

The ultimate purpose of Retriever is to abstract the complex landscape of RAG infrastructure into a stable, secure, reusable API. By shielding every frontend from the mechanics of context assembly and model integration, Retriever enables you to focus on building client-specific products, confident that data isolation, prompt configurability, and architectural discipline are enforced at the engine level.
