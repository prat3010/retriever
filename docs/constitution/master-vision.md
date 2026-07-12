# The Engineering Constitution of Retriever

---

## 1. The Retriever Manifesto & Guiding Principles

### 1.1 Core Ethos
As the founding Principal Architects and Engineering Directors of the Retriever project, we establish this Constitution as the supreme technical law of our platform. This document defines the immutable architectural boundaries, operational constraints, design guidelines, and engineering philosophies that MUST govern all development, refactoring, and AI-assisted changes.

We write code in a landscape defined by rapid commoditization of cognitive models and continuous shifts in data storage technologies. In this environment, raw intelligence is a utility. The permanent value of an enterprise platform lies in its **data orchestrations, security boundaries, multi-tenant isolation, architectural abstraction layers, and the resilience with which it ingests, indexes, and synthesizes context**. Retriever MUST serve as the permanent, secure memory layer of the enterprise.

### 1.2 Core Manifestos
Every engineer, contributor, and AI coding agent MUST adhere to the following five foundational truths:
*   **Decoupling MUST Be Absolute:** Vendor integration MUST be hidden behind abstract interfaces. No third-party SDK, database client, or LLM-specific interface shall leak into core business logic.
*   **Code MUST Serve Two Intellects:** Code MUST be structured with obvious, flat composition to ensure readability for both human software engineers and parsing correctness for AI coding agents.
*   **Tenancy is an Inviolable Sanctuary:** The separation between tenant data spaces is absolute. Any cross-tenant data leakage, logic overlap, or configuration bleed MUST be treated as a system-critical, build-blocking failure.
*   **Performance is a Core Quality Attribute:** High-performance indexing, parallel query resolution, and fast response times are functional requirements, not secondary optimizations.
*   **Configuration Determines Personality:** The platform MUST remain fully headless and configurable at runtime. Behavior variations (such as prompts, models, chunks, and brand themes) MUST resolve dynamically from the configuration store per tenant, without modifying static code.

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
To establish Retriever as the industry-standard, multi-tenant AI Knowledge Platform. We envision a future where corporate knowledge is completely decoupled from the cognitive engines that reason over it. Retriever serves as the secure, high-performance, and resilient memory layer for all enterprise AI applications, enabling any downstream client to query, search, and synthesize proprietary data instantly across multiple modalities, independent of underlying vector databases, LLM engines, or cloud deployment providers.

As cognitive models transition from simple chat interfaces to autonomous, multi-step agentic systems, Retriever shall remain the primary interface through which those agents interact with corporate knowledge. By structuring context as a first-class citizen, Retriever ensures that future agent systems operate within strict grounding boundaries, eliminating hallucinations, enforcing corporate compliance, and maintaining data privacy.

### 2.2 Mission Statement
Our mission is to construct a modular, provider-agnostic, and configuration-driven platform that abstracts document ingestion, chunking, indexing, retrieval, and inference orchestration. We provide downstream teams with standard APIs, SDKs, and event-driven interfaces to instantiate secure, isolated, and domain-specific AI SaaS products in minutes, purely through metadata definition and prompt layering.

To achieve this, we commit to building an engineering ecosystem that prioritizes structural predictability, strict type enforcement, rigorous security models, and thorough performance budgeting. We reject short-term convenience in favor of long-term architectural stability.

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
*   **Not a CA (Credit Analyst) Assistant:** Retriever is not a single-purpose tool built for credit analysis, legal document parsing, or medical diagnostic summarization. It is the platform upon which those specific assistants are constructed.
*   **Not a Hardcoded User Interface:** Retriever is not a static web chat application. While we provide reference interfaces using Next.js and shadcn/ui, the core product is the headless context and inference engine.
*   **Not a Wrapper-as-a-Service:** We do not simply forward raw HTTP requests to OpenAI or Anthropic. We build internal intelligence around chunking hierarchies, retrieval algorithms, and schema-enforced output generation.
*   **Not a Model Hosting Provider:** Retriever does not train or host base foundation models. We interface with external model providers (commercial APIs and self-hosted open-weights engines) through standardized adapter layers.
*   **Not an ETL/Data Warehouse:** Retriever is not designed to perform bulk analytics or data warehouse computations. It does not replace Snowflake, BigQuery, or transactional systems. It is an indexer and context synthesizer optimized for reasoning.

---

## 4. Goals & Non-Goals

### 4.1 Long-Term Goals (5+ Years)
1.  **API Stability & Longevity:** The core contracts and APIs of Retriever must remain structurally backward-compatible for at least five years, ensuring downstream applications can run without code churn.
2.  **Sub-100ms Ingestion-to-Search Availability:** Documents ingested into the platform must be processed, embedded, indexed, and queryable in less than 100 milliseconds at scale.
3.  **Decoupled Data Sovereignty:** The platform must allow enterprise customers to store their vector indexes and raw document chunks in their own cloud accounts (e.g., their own PostgreSQL database or S3 bucket) while utilizing Retriever's central orchestration engine.
4.  **Autonomous Self-Optimization:** The platform will feature automated pipelines that continuously analyze retrieval success, dynamically adjusting chunk boundaries and reranking thresholds based on user feedback loops.
5.  **Multimodal Foundation Ready:** The system must seamlessly ingest, index, and retrieve contexts containing mixed modalities (text, structured tables, layouts, vector elements, and raw image schemas) without modifying core domain interfaces.

### 4.2 Non-Goals
1.  **Building Custom Core Infrastructure:** We will not write custom vector database engines or custom parsing libraries from scratch. We leverage existing high-quality open-source and cloud infrastructure.
2.  **Serving General-Purpose Web Pages:** Retriever will not serve standard web pages, marketing sites, or user blogs. It is strictly an API-driven knowledge platform.
3.  **Direct Integration with Legacy ERP/CRM Systems:** Retriever will not build hundreds of bespoke connectors for legacy enterprise software. Instead, it defines a standard webhook and ingestion API format, pushing the responsibility of push-based synchronization to the data source or middleware.
4.  **Training Custom Base Models:** We do not engage in the research, training, or base fine-tuning of generative language models. We orchestrate existing models.

### 4.3 Architectural Anti-Goals
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
We build Retriever with a product philosophy centered on composability, developer enablement, and configuration-driven systems.
*   **Composability:** Every domain component MUST be structured to function independently. Downstream teams MUST be able to utilize our ingestion pipeline without using our inference engine, or use our retrieval domain with their own custom UI orchestration.
*   **Developer-First Design:** The APIs, SDKs, and configuration schemas are our core products. They MUST be intuitive, self-documenting, and strongly typed.
*   **Configuration Over Code:** System changes MUST be driven by data stored in configurations, not code modifications. Prompt revisions, chunking variations, similarity weights, and LLM routes MUST be adjustable in the database at runtime.

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

#### 1. Cognitive Service Interface (`domain.abstractions.llm`)
```typescript
export interface ChatMessage {
  readonly role: 'system' | 'user' | 'assistant' | 'tool';
  readonly content: string;
  readonly name?: string;
  readonly toolCalls?: readonly ToolCall[];
}

export interface ToolCall {
  readonly id: string;
  readonly type: 'function';
  readonly function: {
    readonly name: string;
    readonly arguments: string;
  };
}

export interface InferenceRequest {
  readonly messages: readonly ChatMessage[];
  readonly temperature: number;
  readonly maxTokens?: number;
  readonly jsonSchema?: Record<string, any>;
  readonly tools?: readonly Record<string, any>[];
}

export interface InferenceResponse {
  readonly content: string;
  readonly usage: {
    readonly inputTokens: number;
    readonly outputTokens: number;
    readonly totalTokens: number;
  };
  readonly finishReason: 'stop' | 'length' | 'tool_calls' | 'content_filter';
}

export interface LlmProvider {
  generate(request: InferenceRequest, configuration: Record<string, any>): Promise<InferenceResponse>;
  generateStream(request: InferenceRequest, configuration: Record<string, any>): AsyncIterable<string>;
}
```

#### 2. Vector Store Interface (`domain.abstractions.vector`)
```typescript
export interface VectorEntity {
  readonly id: string;
  readonly vector: readonly number[];
  readonly payload: Record<string, any>;
  readonly tenantId: string;
}

export interface VectorQuery {
  readonly vector: readonly number[];
  readonly limit: number;
  readonly tenantId: string;
  readonly filters?: Record<string, any>;
  readonly minSimilarityScore?: number;
}

export interface VectorDatabaseProvider {
  upsertVectors(collection: string, entities: readonly VectorEntity[]): Promise<void>;
  searchVectors(collection: string, query: VectorQuery): Promise<readonly VectorEntity[]>;
  deleteVectors(collection: string, ids: readonly string[]): Promise<void>;
  createCollectionIfMissing(collection: string, dimensions: number): Promise<void>;
}
```

#### 3. File Storage Interface (`domain.abstractions.storage`)
```typescript
export interface FileUploadRequest {
  readonly path: string;
  readonly content: Buffer;
  readonly contentType: string;
  readonly tenantId: string;
}

export interface StorageProvider {
  uploadFile(request: FileUploadRequest): Promise<string>;
  downloadFile(path: string, tenantId: string): Promise<Buffer>;
  deleteFile(path: string, tenantId: string): Promise<void>;
  getPresignedUrl(path: string, tenantId: string, ttlSeconds: number): Promise<string>;
}
```

#### 4. Identity & Access Interface (`domain.abstractions.identity`)
```typescript
export interface TenantIdentity {
  readonly tenantId: string;
  readonly status: 'active' | 'suspended' | 'terminated';
  readonly tier: 'standard' | 'enterprise';
  readonly allowedModels: readonly string[];
}

export interface UserContext {
  readonly userId: string;
  readonly tenantId: string;
  readonly roles: readonly string[];
  readonly scopes: readonly string[];
}

export interface IdentityProvider {
  validateToken(token: string): Promise<UserContext>;
  getTenantContext(tenantId: string): Promise<TenantIdentity>;
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
*   **Ingestion Pipeline:** Binary documents MUST be parsed within an isolated sandbox environment. Parsing converts files to standard intermediate formats, extracts metadata, identifies structural layouts, and redacts PII.
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
Since LLM outputs are probabilistic, traditional assert statements fail. We mandate the implementation of an automated evaluation pipeline:
*   **Retrieval Evaluation (RAG Evals):** We test retrieval accuracy using metrics such as **Context Precision** and **Context Recall**. We verify that the retrieval domain returns relevant chunks for a synthetic query dataset.
*   **Generation Evaluation:** We use LLM-as-a-judge methodologies to evaluate generated answers based on:
  *   **Faithfulness (Groundedness):** Ensuring the LLM does not hallucinate information outside the retrieved context.
  *   **Answer Relevance:** Ensuring the generated response directly addresses the user query.
*   **Regression Testing:** A golden evaluation dataset of 200 standard user queries MUST be evaluated before every release to production. Any drop in evaluation scores is a build-blocking event.

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
Retriever MUST support three tiers of tenant isolation, selectable via configuration:

| Isolation Tier | Description | Use Case | Implementation Details |
|---|---|---|---|
| **Logical Isolation** | Single database, shared schemas. Row-Level Security (RLS) filters all reads and writes. | Standard SaaS / Low-cost tier | PostgreSQL RLS enabled on all tables. Queries MUST use `tenant_id` context. |
| **Schema Isolation** | Single database, isolated logical schemas per tenant. | Mid-market Enterprise | Dynamically created database schemas. Connection pool switches schema context per request. |
| **Physical Isolation** | Dedicated database clusters per tenant. | High-security Enterprise | Configuration maps tenant ID to distinct connection strings. |

> [!CAUTION]
> **RLS Bypass Prevention:** All database queries MUST run through transaction contexts that explicitly set the user and tenant variables. Direct connection to the database with the superuser role is strictly forbidden in application runtime.

### 14.2 Privacy by Design & Compliance Readiness
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

### 17.2 Automated Architectural Linter
An automated architectural linter MUST run on every pull request. The build pipeline will block if:
*   Core domain business logic directly imports external database libraries or service SDKs.
*   Circular package dependencies are detected.
*   An API endpoint lacks matching unit or integration tests.
*   A dependency lockfile contains mismatching packages or duplicate version listings.

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

Retriever succeeds when downstream engineering teams can construct and deploy secure, enterprise-grade AI applications without needing to understand embeddings, vector distance metrics, retrieval pipelines, prompt engineering, or cognitive model providers. The ultimate purpose of Retriever is to abstract the complex, shifting landscape of AI infrastructure into a stable, secure, composable, and future-proof interface. By shielding developers from the mechanics of context assembly and model integration, Retriever enables organizations to focus on their domain logic, confident that their enterprise knowledge is managed under strict isolation, performance budgets, and architectural discipline.
