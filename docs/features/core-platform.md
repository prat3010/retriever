# Feature Specification: Retriever Core Platform

---

## 1. Product Overview

Retriever is a reusable RAG engine that powers client-specific frontends. A coaching institute uploads its textbooks → the coaching portal answers students in the teacher's style. A CA firm configures their data → their automation tool retrieves client records instantly. An advocate uploads case law → their legal assistant finds relevant precedents.

Each frontend is a unique product. Retriever is the shared engine behind all of them — accessed through a single API key and an `X-User-ID` header. It handles document ingestion, chunking, indexing, hybrid search, and LLM generation. It never manages user authentication, sessions, or the frontend's UI decisions — that's the frontend's job.

At its core, Retriever provides a standard REST API to ingest unstructured documentation, decompose it into semantic chunks, execute high-performance hybrid queries, and orchestrate grounded generative answers with strict citation enforcement and security boundaries.

### 1.1 Out of Scope (What Retriever is NOT)
To maintain architectural focus and prevent scope creep, Retriever explicitly excludes:
*   **Default User Interface:** No static chatbot interface or document dashboard is provided in the core platform; Retriever is API-driven (reference implementations exist separately).
*   **User Authentication:** Retriever does not authenticate end users. Client frontends authenticate their own users and pass `X-User-ID` to scope data access. Retriever trusts this header.
*   **Workflow Automation:** Retriever does not orchestrate business logic flows, conditional system integrations, or multi-app actions.
*   **Business Intelligence (BI):** Retriever does not generate reporting charts, metrics dashboards, or data aggregation analytics.
*   **Model Training or Hosting:** Retriever does not train, fine-tune, or host base LLMs or embedding models; it connects to external endpoints via abstraction adapters.

---

## 2. Primary User Personas

The platform serves two distinct user personas.

| Persona | Role | Primary Objective | Key Requirements |
|---|---|---|---|
| **Platform Operator (You)** | Builds and operates the Retriever engine, creates tenants, generates API keys, monitors usage. | Deliver a reliable RAG engine that powers client products. | - Admin API for tenant CRUD, key management, config<br>- Telemetry and observability<br>- Data isolation guarantees<br>- Async queue monitoring |
| **Client (Tenant)** | The customer. Signs up, configures prompts/models, uploads documents, builds a frontend (or uses Retriever directly). | Add RAG-powered search and LLM generation to their product. | - Stable REST API with API key auth<br>- Per-user isolation via `X-User-ID`<br>- Configurable prompts and models per tenant<br>- SDKs for common languages |

A client can be a solo practitioner (they ARE the end user, `X-User-ID` is their own) or an organization with many end users (frontend authenticates users, passes `X-User-ID` on each request). Retriever treats both identically — `X-User-ID` scopes chat sessions and logs irrespective of who the user is.

---

## 3. End-to-End User Journey

The diagram below details the operational sequence from tenant initialization to grounded document search and chat:

```mermaid
sequenceDiagram
    autonumber
    actor Operator as Platform Operator
    actor Client as Client App
    actor User as End User
    participant Platform as Retriever Platform

    %% Phase 1: Onboarding
    rect rgb(240, 245, 250)
        Note over Operator, Platform: Phase 1: Tenant Provisioning & Configuration
        Operator->>Platform: Register new tenant
        Platform-->>Operator: Tenant ID
        Operator->>Platform: Create client API key (scoped to tenant)
        Platform-->>Operator: API Key (X-API-Key)
        Operator->>Platform: Configure prompts, model, chunk limits
    end

    %% Phase 2: Client Integration
    rect rgb(245, 240, 250)
        Note over Client, Platform: Phase 2: Client Onboards Their Frontend
        Operator->>Client: Give API Key + Tenant ID
        Note over Client: Client builds their frontend<br/>Authenticates their own users
        Client->>Platform: Upload documents (PDF, DOCX, HTML) with API key
        Platform-->>Client: Return 202 Accepted (Document ID)
        Note over Platform: Parses, chunks, indexes, vectorizes
    end

    %% Phase 3: Query & Grounding
    rect rgb(240, 250, 240)
        Note over User, Platform: Phase 3: Grounded Query with User Isolation
        User->>Client: Submit question via frontend
        Client->>Platform: POST /v1/search with X-API-Key + X-User-ID
        Note over Platform: Resolves tenant from API key<br/>Filters results to user's documents<br/>Runs hybrid search + RRF + reranking<br/>Packs prompt with tenant template & streams
        Platform-->>Client: Stream tokens (SSE) + inline citations
        Client-->>User: Render grounded answer with citations
    end
```

---

## 4. Core Features

Retriever's capabilities are divided into five logical feature groups:

1.  **Multi-Tenant Identity & Config Registry (`identity`):** Authentication of requests, enforcement of security boundaries, and dynamic lookup of runtime configuration schemas.
2.  **Asynchronous Document Ingestion (`ingestion`):** Parallel document upload parsing, sandboxed layouts extraction, duplicate file detection, and PII sanitization.
3.  **Knowledge Indexing & Hierarchical Chunking (`knowledge`):** Text segmentation strategies, parent-child context trees, and automatic vector synchronization.
4.  **Hybrid Retrieval & Fusion (`retrieval`):** Merged vector-semantic and relational-keyword queries, metadata classification filters, and relevance reranking.
5.  **Grounded Generative Inference (`inference`):** Session history retention, context compilation, citation-first generation, safety guardrails, structured JSON generation, tool orchestration, and human-in-the-loop approvals.

---

## 5. Functional Requirements

### 5.1 Multi-Tenant Identity & Config Registry
*   **FR-1.1: Multi-Tenant Data Separation:** The platform MUST enforce strict data isolation between tenants. Under no circumstance may queries or documents belonging to Tenant A be exposed to Tenant B.
*   **FR-1.2: API Key Authentication:** The platform MUST authenticate every API request using unique credentials associated with a tenant ID.
*   **FR-1.3: Dynamic Configuration (CAD):** The platform MUST resolve prompt templates, cognitive model choices, temperature, chunk sizes, and retrieval weights dynamically at runtime based on the authenticated tenant context.
*   **FR-1.4: Isolation Level Configurations:** The system MUST support configurable database multi-tenancy mappings, allowing logical separation (Row-Level Security), logical database schemas separation, or physical server database separation per tenant.

### 5.2 Asynchronous Document Ingestion Pipeline
*   **FR-2.1: Multi-Format Upload:** The system MUST support uploading document formats including PDF, HTML, DOCX, and raw Text.
*   **FR-2.2: Asynchronous Parsing Sandbox:** The system MUST process document parsing asynchronously in a restricted container sandbox environment.
*   **FR-2.3: Structural Extraction:** The parsing process MUST preserve document metadata and structural elements, such as tables, headers, and bulleted lists.
*   **FR-2.4: Duplicate Detection:** The system MUST compute a content hash for every uploaded file. If the hash matches an existing document in the tenant's registry, the system MUST skip parsing and link to the existing asset.
*   **FR-2.5: PII Redaction:** The ingestion system MUST scan extracted text for Personally Identifiable Information (PII) and redact it based on tenant security policies prior to chunk indexing.
*   **FR-2.6: Status Monitoring:** The system MUST provide status tracking endpoints (`PENDING`, `PARSING`, `INDEXING`, `INDEXED`, `FAILED`) for document ingestion processes.

### 5.3 Knowledge Indexing & Chunk Management
*   **FR-3.1: Chunking Strategies:** The system MUST decompose documents into chunks based on tenant-configured parameters (e.g., token limits, overlap sizes, or semantic paragraph boundaries).
*   **FR-3.2: Parent-Child Hierarchies:** The system MUST record parent-child relationships between small semantic chunks (children, e.g., 200 tokens) and their surrounding context blocks (parents, e.g., 1000 tokens) to allow precise matches to retrieve broader context.
*   **FR-3.3: Automatic Vectorization:** The system MUST generate mathematical vectors (embeddings) for chunks automatically when a document is indexed.
*   **FR-3.4: Dynamic Vector Synchronization:** The system MUST update the vector database and relational chunk registries in a single transactional state to prevent orphan vectors.

### 5.4 Hybrid Retrieval & Fusion Engine
*   **FR-4.1: Parallel Search Execution:** The retrieval system MUST run a vector search query and a sparse-text keyword query in parallel.
*   **FR-4.2: Reciprocal Rank Fusion (RRF):** The retrieval system MUST merge parallel search results into a single ranked list using a Reciprocal Rank Fusion (RRF) algorithm.
*   **FR-4.3: Metadata Filtering:** The system MUST filter search candidate lists using metadata tags (e.g., source file date, custom categories, document type) before applying ranking algorithms.
*   **FR-4.4: Context Reranking:** The system MUST route the top fused candidates to a cross-encoder model to compute relevance scores and prune chunks below a tenant-configured similarity threshold.
*   **FR-4.5: BM25 Two-Stage Scoring:** The keyword leg MUST use `ts_rank_cd` (length-normalized) for fast candidate retrieval. Optionally, an in-app pure-Python BM25 re-ranks fused candidates using local IDF.
*   **FR-4.6: MMR Diversity Sampling:** The system SHOULD apply Maximum Marginal Relevance (TF-IDF cosine) after reranking to ensure result diversity across documents.
*   **FR-4.7: HyDE Query Rewriting:** The system SHOULD generate a hypothetical document via LLM and use its embedding for the vector search leg, improving semantic recall for underspecified queries.

### 5.5 Grounded Generative Inference
*   **FR-5.1: Chat Session Tracking:** The system MUST manage conversation histories, saving user inputs and system responses in session logs.
*   **FR-5.2: Prompt Construction:** The system MUST construct prompts dynamically by combining system guidelines, tenant persona configurations, retrieved context chunks, and user inputs.
*   **FR-5.3: Context Window Management:** The system MUST check the token counts of compiled prompts. If the prompt exceeds the target model's limits, it MUST automatically apply compression policies (e.g., summarizing older history or selecting only highest-scoring chunks).
*   **FR-5.4: Citation Enforcement:** Generated responses MUST include inline citations referring to specific source chunk IDs. The system MUST validate citations; responses containing unresolvable citations MUST trigger correction logic or throw a validation error.
*   **FR-5.5: Structured Output Generation:** The system SHOULD attempt structured JSON generation via prompt hints and `response_format` where supported; output JSON schema validation is best-effort.
*   **FR-5.6: Input/Output Guardrails:** The system MUST check input queries for prompt injection attempts and check output tokens for safety violations.
*   **FR-5.7: Tool Execution Scope:** If the cognitive model requests tool execution, the system MUST validate the tool schemas against the tenant's allowed scopes.
*   **FR-5.8: Human-in-the-Loop Hooks:** The platform MUST support pausing tool executions or high-risk generations to register token hooks in the database, waiting for external user approval before completing the operation.

---

## 6. Non-Functional Requirements (NFRs)

### 6.1 Performance
*   **Search Latency:** The system MUST execute hybrid searches, fusion, and reranking in under 150ms.
*   **Inference Startup:** The Generative Inference pipeline MUST achieve a Time-To-First-Token (TTFT) of under 500ms (excluding model endpoint response time).
*   **Ingestion Processing:** Standard documents (under 50 pages) MUST be processed, chunked, vectorized, and queryable in under 10 seconds.

### 6.2 Scalability
*   **Stateless Serving Nodes:** The API and serving layers MUST remain completely stateless to support horizontal scaling.
*   **Asynchronous Queuing:** Document processing tasks MUST run out-of-process via event messaging queues to protect API gateway threads.
*   **Dynamic Cache System:** The system MUST use L1 in-memory caches for active configurations and L2 semantic similarity caches for search queries to reduce database workloads.

### 6.3 Security
*   **Tenancy Breach Kill-Switch:** If the database adapter detects a tenant ID mismatch between the request context and retrieved records, it MUST terminate the database connection pool, revoke the caller's credentials, and flag a Severity-1 security incident.
*   **Egress Sandbox Security:** Parsing workers MUST run inside sandboxed environments with no internet egress traffic permitted to prevent PII leakage.
*   **PII Sanitization:** The system MUST support dynamic encryption or redaction of text sequences classified as PII (e.g., social security numbers, credit card details).

### 6.4 Accessibility (Playground Reference UI)
*   **WCAG 2.1 Compliance:** Reference interfaces provided alongside the platform MUST comply with WCAG 2.1 Level AA guidelines.
*   **Keyboard Navigation:** All interactive controls in reference dashboards MUST support full keyboard accessibility.
*   **ARIA Labels:** Semantic markup and ARIA tags MUST be defined on all reactive components.

---

## 7. Permissions and API Key Scoping

Retriever enforces access controls via two API key roles.

| Role | Scope | Permissions | Constraints |
|---|---|---|---|
| **admin** | System-wide | - Provision and suspend tenants<br>- CRUD any tenant's config<br>- Generate and revoke any tenant's API keys<br>- View system telemetry | Cannot read raw document chunks or query text within individual tenant databases. |
| **client** | Single tenant | - Upload and delete documents<br>- Query search and chat endpoints<br>- Open inference sessions | Scoped to a single tenant. All queries auto-filtered by `tenant_id`. `X-User-ID` further scopes chat sessions and logs to a specific user. Cannot modify tenant config or manage keys. |

End users never hold a Retriever API key. The client frontend authenticates users and passes `X-User-ID` on their behalf.

---

## 8. Data Entities Involved

Below are the logical entities tracked by Retriever:

```mermaid
erDiagram
    TENANT ||--o{ TENANT_CONFIG : has
    TENANT ||--o{ DOCUMENT : owns
    TENANT ||--o{ CHAT_SESSION : maintains
    TENANT ||--o{ USER : has
    TENANT ||--o{ API_KEY : has
    TENANT ||--o{ EVAL_DATASET : maintains
    DOCUMENT ||--o{ CHUNK : contains
    CHUNK ||--|| VECTOR_RECORD : materializes
    TENANT ||--o{ PROMPT_TEMPLATE : registers
    CHAT_SESSION ||--o{ CHAT_MESSAGE : records
    CHAT_SESSION ||--o{ INFERENCE_LOG : logs
    USER ||--o{ CHAT_SESSION : initiates
    EVAL_DATASET ||--o{ EVAL_QUESTION : contains
    EVAL_DATASET ||--o{ EVAL_RUN : triggers
    EVAL_RUN ||--o{ EVAL_RUN_RESULT : produces
```

*   **Tenant:** Represents isolated enterprise workspace bounds.
    *   *Fields:* `tenantId` (UUID), `status` (`Active`, `Suspended`, `Terminated`), `tier` (`Standard`, `Enterprise`), `allowedModels` (List), `createdAt` (Timestamp).
*   **TenantConfig:** Runtime behavior settings for each tenant.
    *   *Fields:* `tenantId` (UUID), `activeModel` (String), `temperature` (Float), `chunkSize` (Integer), `chunkOverlap` (Integer), `rrfWeights` (JSON), `rerankingThreshold` (Float), `systemPromptTemplateId` (UUID).
*   **User:** Sub-client identity scoped to a tenant.
    *   *Fields:* `userId` (UUID), `tenantId` (UUID), `externalId` (String), `metadata` (JSON), `createdAt` (Timestamp).
*   **ApiKey:** Named credentials with role scoping.
    *   *Fields:* `keyId` (UUID), `tenantId` (UUID, nullable for admin keys), `name` (String), `keyHash` (String), `role` (`admin`, `client`), `isActive` (Boolean), `createdAt` (Timestamp).
*   **Document:** Raw document tracking metadata.
    *   *Fields:* `documentId` (UUID), `tenantId` (UUID), `fileName` (String), `fileHash` (String), `storagePath` (String), `mimeType` (String), `status` (`Pending`, `Parsing`, `Indexing`, `Indexed`, `Failed`), `createdAt` (Timestamp).
*   **Chunk:** Text snippets extracted from documents.
    *   *Fields:* `chunkId` (UUID), `documentId` (UUID), `tenantId` (UUID), `content` (Text), `tokenCount` (Integer), `sequenceOrder` (Integer), `metadata` (JSON), `parentChunkId` (UUID).
*   **VectorRecord:** Mathematical embeddings for chunks.
    *   *Fields:* `chunkId` (UUID), `tenantId` (UUID), `embedding` (Array of Floats), `payload` (JSON).
*   **PromptTemplate:** Dynamic instructions stored in the database.
    *   *Fields:* `promptId` (UUID), `tenantId` (UUID), `name` (String), `content` (Text), `isSystemPrompt` (Boolean), `createdAt` (Timestamp).
*   **ChatSession:** Chat tracking record, scoped to a user.
    *   *Fields:* `sessionId` (UUID), `tenantId` (UUID), `userId` (UUID), `createdAt` (Timestamp).
*   **ChatMessage:** Conversational text steps.
    *   *Fields:* `messageId` (UUID), `sessionId` (UUID), `userId` (UUID), `role` (`System`, `User`, `Assistant`, `Tool`), `content` (Text), `toolCalls` (JSON), `createdAt` (Timestamp).
*   **InferenceLog:** Operational log for cost and audit tracing.
    *   *Fields:* `logId` (UUID), `tenantId` (UUID), `sessionId` (UUID), `userId` (UUID), `modelUsed` (String), `inputTokens` (Integer), `outputTokens` (Integer), `latencyMs` (Integer), `createdAt` (Timestamp).
*   **EvalDataset:** Ground-truth question sets for RAG evaluation.
    *   *Fields:* `datasetId` (UUID), `tenantId` (UUID), `name` (String), `description` (Text), `createdAt` (Timestamp).
*   **EvalQuestion:** Individual Q&A pair within a dataset.
    *   *Fields:* `questionId` (UUID), `datasetId` (UUID), `question` (Text), `groundTruthAnswer` (Text), `relevantChunkIds` (JSONB).
*   **EvalRun:** Execution record of an evaluation pass.
    *   *Fields:* `runId` (UUID), `tenantId` (UUID), `datasetId` (UUID), `status` (`pending`, `running`, `completed`), `trigger` (`manual`, `scheduled`), `aggregateScores` (JSONB).
*   **EvalRunResult:** Per-question scores from an eval run.
    *   *Fields:* `resultId` (UUID), `runId` (UUID), `questionId` (UUID), `generatedAnswer` (Text), `retrievedChunkIds` (JSONB), `scores` (JSONB), `latencyMs` (Integer).

---

## 9. Error States and Edge Cases

The table below defines how the system handles critical error states:

| Scenario | System Detection Mechanism | Action/Response | Fallback Strategy | User-Visible Notification |
|---|---|---|---|---|
| **Mismatched Tenant Data Access** | Database adapters verify requested tenant ID against execution context. | **Tenancy Breach Kill-Switch:** Immediately sever DB connection pool, flag Severity-1 alert. | Revoke credentials of the calling key. | HTTP `403 Forbidden` response. |
| **Duplicate Document Upload** | Hash check matches `fileHash` of an uploaded document. | Skip processing pipeline. | Return reference link to existing document schema. | HTTP `200 OK` showing file already indexed. |
| **Corrupt or Unreadable Document** | Ingestion parser throws processing exception. | Set document status to `FAILED`. | Log details to audit database. | Document list shows status `Failed` with diagnostic message. |
| **Vector DB Outage** | Vector store queries return connection timeouts or errors. | Open circuit breaker. | Fall back to text keyword search in relational database. | API returns query successfully (reduced semantic quality mode). |
| **Context Window Overflow** | Prompt builder counts tokens and detects limit breach. | Apply context compression. | Compress conversation history and prune low-scoring chunks. | Warning header in response details token trimming. |
| **Citation Validation Failure** | Verification engine flags inline citations that do not exist in source chunks. | Reject output. | Trigger dynamic auto-correct generation pass using LLM. | HTTP `500 Server Error` (if auto-correct fails). |
| **Guardrail Safety Breach** | Content scanner flags input prompt or output text. | Terminate processing. | Return safety rejection message. | API returns error detailing policy block. |

---

## 10. Acceptance Criteria

### 10.1 Multi-Tenant Config Registry
*   [ ] **AC 1.1:** Any API request missing an authorization header or using an invalid API key MUST be rejected with HTTP `401 Unauthorized`.
*   [ ] **AC 1.2:** Database queries MUST automatically apply filters restricting results to the caller's tenant ID context.
*   [ ] **AC 1.3:** Changes to a tenant's config registry (e.g., switching model names) MUST apply to subsequent API calls within 60 seconds without server restarts.

### 10.2 Asynchronous Document Ingestion Pipeline
*   [ ] **AC 2.1:** Uploading a document MUST write a database record with status `PENDING` and return an HTTP `202 Accepted` response with the document ID.
*   [ ] **AC 2.2:** Uploading a duplicate file MUST skip parsing and return HTTP `202 Accepted` with the existing document's ID (same status as first upload, differing response body).
*   [ ] **AC 2.3:** Document parsing failures MUST transition the document status to `FAILED` and log error details to the database.

### 10.3 Knowledge Indexing & Chunk Management
*   [ ] **AC 3.1:** Document text MUST be segmented into chunks matching the tenant's configuration limits.
*   [x] **AC 3.2:** Sub-chunks (children) MUST be saved with `parentChunkId` referencing their parent context block.
*   [ ] **AC 3.3:** Indexed chunks MUST have corresponding mathematical vectors generated and saved in the vector database.

### 10.4 Hybrid Retrieval & Fusion Engine
*   [ ] **AC 4.1:** Search queries MUST run semantic similarity match and keyword match in parallel.
*   [ ] **AC 4.2:** Search result listings MUST contain only chunk entities associated with the requesting tenant.
*   [ ] **AC 4.3:** Merged search results MUST be ordered according to RRF and filtered by metadata constraints.

### 10.5 Grounded Generative Inference
*   [ ] **AC 5.1:** Generative responses MUST include inline citation tags (e.g., `[Source ID]`) that resolve to active chunks.
*   [ ] **AC 5.2:** Generated responses containing unresolvable citations MUST be rejected.
*   [ ] **AC 5.3:** Outputs violating target JSON schemas or safety guardrails MUST be blocked.
*   [ ] **AC 5.4:** The system MUST compress prompt inputs when total tokens exceed 95% of target model context limits.

### 10.6 Client Integration & Sub-Client Isolation
*   [ ] **AC 6.1:** Requests with an `admin` API key MUST bypass user scoping and return data for the entire tenant.
*   [ ] **AC 6.2:** Requests with a `client` API key MUST auto-filter all results to the key's tenant.
*   [ ] **AC 6.3:** Chat sessions and messages created with `X-User-ID` set MUST be scoped to that user. Queries without `X-User-ID` MUST be rejected for `client` keys.
*   [ ] **AC 6.4:** Admin endpoints (tenant CRUD, key management, config) MUST reject `client` API keys with HTTP `403 Forbidden`.
*   [ ] **AC 6.5:** Missing or invalid API keys MUST be rejected with HTTP `401 Unauthorized`.

---

## 11. Future Expansion Ideas (Out of Scope)

*   **No-Code Visual Workflow Builder:** Provide a drag-and-drop dashboard to build custom multi-model processing chains.
*   **Auto-Tuning Chunking Engine:** Automate optimization pipelines that adjust chunk boundaries and overlap sizes based on user search feedback.
*   **Multimodal Embedding & Parsing:** Extend the ingestion pipeline to parse, index, and retrieve video files, voice clips, and images directly.
*   **Federated Data Sovereignty:** Allow enterprise tenants to host vector databases in their own cloud accounts while using Retriever's central orchestration engine.

---

## 12. Open Questions and Assumptions

*   **Q-1: Reranking Config Routing:** Do we support tenant-configured reranking models (e.g., Tenant A uses Cohere, Tenant B uses local Cross-Encoder), or does the platform run a single shared reranker service?
    *   *Decision:* Shared Cohere `rerank-v3.5` instance. `rerank_candidate_multiplier` is per-tenant configurable. Model choice is shared platform-wide.
*   **Q-2: Chunk Deletion Synchronization:** When a document is deleted, should the chunk deletion in relational and vector databases run synchronously or eventually?
    *   *Assumption:* Deleting a document removes metadata synchronously, and background workers clean up chunk databases and vector stores asynchronously.
*   **Q-3: Human-in-the-Loop Expiry:** How long should a paused, human-in-the-loop inference session wait for approval before timing out?
    *   *Assumption:* Approval tokens remain valid for 24 hours. If no approval is received, the session transitions to an expired error state.
