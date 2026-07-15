# System Architecture Design Blueprint: Retriever Platform

---

## Part I: Logical Architecture

Part I defines the conceptual models, bounded contexts, domain dependencies, interface ports, and logical data flow paths of the Retriever platform. These designs are technology-neutral and MUST remain valid regardless of the physical deployment environment.

---

### 1. Architectural System Overview

The core architecture of Retriever is based on the **Ports and Adapters (Hexagonal)** model. The central application contains the core domain logic, completely isolated from communication frameworks, database systems, third-party libraries, and execution runtimes.

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
               |   |  pgvector   |      | SqlIdentity  |     |OpenAI/Cohere|  |
               |   +-------------+      +-------------+      +-----------+   |
               +-------------------------------------------------------------+
```

---

### 2. Bounded Contexts & Domain Dependency Map

Retriever is organized into five isolated bounded contexts, each owning its models, rules, and logic boundaries.

#### 2.1 Bounded Context Definitions

```mermaid
classDiagram
    class Tenant {
        +UUID tenantId
        +String status
        +String tier
        +TenantConfig configuration
    }
    class Document {
        +UUID documentId
        +UUID tenantId
        +String fileName
        +String fileHash
        +String storagePath
        +String mimeType
        +DateTime createdAt
    }
    class Chunk {
        +UUID chunkId
        +UUID documentId
        +UUID tenantId
        +String content
        +Integer tokenCount
        +Integer sequenceOrder
        +Map metadata
        +UUID parentChunkId
    }
    class ChatSession {
        +UUID sessionId
        +UUID tenantId
        +DateTime createdAt
        +List messages
    }
    class VectorRecord {
        +UUID chunkId
        +List~Float~ embedding
        +UUID tenantId
        +Map payload
    }

    Tenant "1" *-- "many" Document : owns
    Document "1" *-- "many" Chunk : decomposed into
    Chunk "0..1" <-- "many" Chunk : hierarchy (parent-child)
    Chunk "1" -- "1" VectorRecord : materialized as
    Tenant "1" *-- "many" ChatSession : maintains
```

*   **Ingestion Bounded Context (`domain.ingestion`):** Transforms binary data payloads (e.g., PDF, DOCX, HTML streams) into structured plaintext schemas. This context MUST remain isolated from indexing systems.
    *   *Key Entities:* `Document` (Entity), `FileHash` (Value Object).
*   **Knowledge Bounded Context (`domain.knowledge`):** Manages structural models of text chunks, embedding associations, tag assignments, parent-child relationships, and hierarchical structures.
    *   *Key Entities:* `Chunk` (Entity), `Embedding` (Value Object), `ChunkTree` (Value Object).
*   **Retrieval Bounded Context (`domain.retrieval`):** Merges vector similarity results and sparse keyword search queries. It executes metadata filtering, semantic matching, and reranking.
    *   *Key Entities:* `SearchQuery` (Value Object), `QueryResult` (Value Object).
*   **Inference Bounded Context (`domain.inference`):** Coordinates interactions with cognitive engines. It handles conversation history compression, prompt packaging, system prompt injection, tool calling orchestration, and token calculation.
    *   *Key Entities:* `ChatSession` (Entity), `ChatMessage` (Value Object), `PromptTemplate` (Value Object).
*   **Identity Bounded Context (`domain.identity`):** Enforces tenancy rules, resolves API keys, and validates access levels.
    *   *Key Entities:* `Tenant` (Entity), `UserContext` (Value Object).

#### 2.2 Bounded Context Dependency Map
To prevent architectural drift and maintain logical isolation, we enforce a strict dependency hierarchy between the core domains:

```mermaid
graph TD
    subgraph CoreDomains["Bounded Context Boundaries"]
        Identity["domain.identity"]
        Ingestion["domain.ingestion"]
        Knowledge["domain.knowledge"]
        Retrieval["domain.retrieval"]
        Inference["domain.inference"]
    end

    %% Dependency flows
    Ingestion -->|Resolves Tenant Identity| Identity
    Knowledge -->|References Document References| Ingestion
    Retrieval -->|Queries Chunk Schemas| Knowledge
    Inference -->|Requests Grounded Context| Retrieval

    %% Constraints Style
    classDef readOnly fill:#ffe6e6,stroke:#f85149,stroke-width:2px;
    classDef independent fill:#e6f2ff,stroke:#0066cc,stroke-width:2px;
    class Retrieval readOnly;
    class Identity independent;
```

The dependency relationships MUST comply with these rules:
1.  **Identity Bounded Context (`domain.identity`) MUST Remain Independent:** It MUST NOT import models or refer to logic from any other bounded context.
2.  **Ingestion Bounded Context (`domain.ingestion`) MAY Depend on Identity:** It resolves tenant details during document uploads to verify quotas and access.
3.  **Knowledge Bounded Context (`domain.knowledge`) MAY Depend on Ingestion:** Chunks are derived from, and link directly to, Document entities owned by Ingestion.
4.  **Retrieval Bounded Context (`domain.retrieval`) MAY Depend on Knowledge:** Retrieval query services search over Chunk indices managed by Knowledge.
5.  **Inference Bounded Context (`domain.inference`) MAY Depend on Retrieval:** Inference requires Retrieval ports to fetch grounding contexts for prompt assembly.
6.  **Retrieval MUST Remain Read-Only:** Retrieval MUST NOT perform write operations on Knowledge or Ingestion states.
7.  **Inference MUST NOT Directly Modify Knowledge:** All modifications to chunk indexing states MUST route through core commands in the Knowledge context.
8.  **Cross-Context Communication SHOULD Occur Through Ports or Domain Events** rather than direct implementation coupling.

---

### 3. Ports & Adapters (Hexagonal) Architecture Contracts

No third-party SDK or infrastructure library may leak into the core domains. Decoupling is enforced by mapping ports to adapters.

```
       +-----------------------------------------------------------------+
       |                         Core Domain                             |
       |                                                                 |
       |  [LlmProvider Port]   [VectorDatabasePort]   [StorageProvider]  |
       +----------|----------------------|----------------------|--------+
                  |                      |                      |
  ================|======================|======================|========= Dependency Boundary
                  v                      v                      v
        +-----------------------------------------------------------------+
        |                       Adapters Layer                            |
        |                                                                 |
        |  +---------------------------+   +-------------------+          |
        |  | RoutingLLMProvider        |   | PgVectorSearch    |          |
        |  |  - OpenAILLMAdapter       |   +-------------------+          |
        |  |  - AnthropicLLMAdapter    |   +-------------------+          |
        |  +---------------------------+   | Local / S3Storage |          |
        |  +---------------------------+   +-------------------+          |
        |  | CohereRerankerAdapter    |                                  |
        |  +---------------------------+                                  |
        |  +----------------------------+                                 |
        |  | RedisTenantConfigCache     |                                 |
        |  +----------------------------+                                 |
        +-----------------------------------------------------------------+
```

#### 3.1 Cognitive Service Interface (`domain.abstractions.inference`)
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

#### 3.2 Vector Store Interface (`domain.abstractions.retrieval`)
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

#### 3.3 File Storage Interface (`domain.abstractions.ingestion`)
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

#### 3.4 Identity & Access Interface (`domain.abstractions.identity`)
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

### 4. CQRS Read/Write Path Separation

To optimize system resource usage and ensure performance budgets are met, Retriever implements Command Query Responsibility Segregation (CQRS). The write path is optimized for consistency, validation, and metadata extraction, while the read path is optimized for minimal latency.

```
                      CQRS DATA PATH ARCHITECTURE
                      
   [WRITE PATH - COMMANDS]
   User Action -> Ingest API -> DB: Ingestion Job -> Worker -> Parsers -> Chunking -> Vectorizing -> Vector DB & relational store
   
   [READ PATH - QUERIES]
   User Action -> Query API -> Parallel Search (Vector + BM25) -> Reranking -> Prompt Assembly -> LLM Output -> Validator -> Client Stream (SSE)
```

#### 4.1 Write Path (Commands Pipeline)
1.  **Ingestion Request:** Client issues `UploadDocumentCommand` containing file streams and metadata.
2.  **Validation:** API Gateway checks tenant authentication and storage quotas. The command is recorded in the relational database with status `PENDING`.
3.  **Event Broadcast:** The system publishes a `DocumentUploadedEvent` containing storage endpoints and tenant context.
4.  **Parsing (Asynchronous Worker):** Workers parse the document inside sandbox containers, generating normalized text and layout indexes.
5.  **Chunking & Indexing:** The system runs tenant-specific chunking guidelines (e.g., semantic splits or fixed sliding windows) to write `Chunk` entities to the relational store.
6.  **Vectorization:** Embeddings are generated for new chunks and saved to the vector database.
7.  **Finalize:** The document status transitions to `INDEXED`, and the system publishes `DocumentIndexedEvent`.

#### 4.2 Read Path (Queries Pipeline)
1.  **Inquiry Request:** Client issues `ResolveQuery` via HTTP/SSE.
2.  **Context Resolution:** The API resolves the active tenant's `TenantConfig` dynamically from database cache memory.
3.  **Parallel Query Execution:**
    *   **Vector Search Port:** The query is vectorized, and the system executes similarity search on the vector database.
    *   **Keyword Search Port:** Relational tables run keyword matching against chunk content.
4.  **Merging & Reranking:** The retrieval engine merges matches using Reciprocal Rank Fusion (RRF), filters by tenant metadata, and routes candidates to the reranking model adapter.
5.  **Prompt Construction:** The system merges the top candidates into prompt templates resolved from the tenant configuration registry.
6.  **Model Dispatch:** The prompt is dispatched to the active `LlmProvider` adapter.
7.  **Stream Validation:** Generations stream via Server-Sent Events (SSE). The validation engine checks citations and JSON formatting constraints on the fly.

---

### 5. Detailed System Data Flows

#### 5.1 Ingestion & Indexing Flow (Write Path)

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as Ingest API (serving)
    participant Auth as Auth & Identity (domain.identity)
    participant Storage as File Storage Adapter
    participant Broker as Message Broker (out-of-process)
    participant Worker as Indexing Worker
    participant Parser as Sandbox Parser Adapter
    participant DB as Relational Database Adapter
    participant VectorDB as Vector Database Adapter

    rect rgb(240, 240, 240)
        Note over Client, API: Phase 1: Ingestion API Ingress (Synchronous)
        Client->>API: POST /v1/tenants/{tenantId}/documents (Binary Stream, Metadata)
        API->>Auth: Validate Request Context (Token)
        Auth-->>API: UserContext (TenantId, scopes)
        
        API->>DB: Check File Hash Idempotency
        DB-->>API: Unique / Duplicate Status
        
        API->>Storage: uploadFile(Path, Content, TenantId)
        Storage-->>API: File Storage URL
        
        API->>DB: insertDocument(DocumentEntity: PENDING)
        DB-->>API: DocumentId
    end

    rect rgb(225, 235, 245)
        Note over API, Broker: Phase 2: Asynchronous Worker Handoff
        API->>Broker: publishEvent(DocumentUploadedEvent)
        API-->>Client: HTTP 202 Accepted (DocumentId, Status: PENDING)
    end

    rect rgb(240, 240, 240)
        Note over Broker, VectorDB: Phase 3: Background Worker Processing (Asynchronous)
        Broker->>Worker: Consume DocumentUploadedEvent
        Worker->>Storage: downloadFile(Storage URL)
        Storage-->>Worker: Binary Content
        
        Worker->>Parser: parseBinary(Binary Content)
        Note over Worker,Parser: Parser runs inside isolated container sandboxes.
        Parser-->>Worker: ExtractedDocument (Raw Text, structural tags)
        
        Worker->>Worker: executeChunkingStrategy(Text, ChunkSize, Overlap)
        Worker->>DB: insertDocumentChunks(List[ChunkEntity])
        DB-->>Worker: List[ChunkIds]
        
        Worker->>Worker: generateEmbeddings(List[ChunkText])
        
        Worker->>VectorDB: upsertVectors(Collection, List[VectorEntity])
        VectorDB-->>Worker: Success
        
        Worker->>DB: updateDocumentStatus(DocumentId, Status: INDEXED)
        Worker->>Broker: publishEvent(DocumentIndexedEvent)
    end
```

#### 5.2 Retrieval & Inference Generation Flow (Read Path)

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as Query API (serving)
    participant Auth as Auth & Identity (domain.identity)
    participant Cache as Metadata Cache Adapter
    participant Retrieval as Retrieval Domain (domain.retrieval)
    participant VectorDB as Vector Database Adapter
    participant DB as Relational Database Adapter
    participant Inference as Inference Domain (domain.inference)
    participant Cognitive as Cognitive Model Adapter

    rect rgb(240, 240, 240)
        Note over Client, Cache: Phase 1: Authentication & Configuration Dynamic Setup
        Client->>API: POST /v1/tenants/{tenantId}/search (Query, filters)
        API->>Auth: Validate Token & Scope
        Auth-->>API: UserContext (TenantId)

        API->>Cache: fetchTenantConfig(TenantId)
        Cache-->>API: TenantConfig (active model, temperature, prompts, chunk limits)
    end

    rect rgb(225, 235, 245)
        Note over API, Retrieval: Phase 2: Dynamic Parallel Context Retrieval
        API->>Retrieval: retrieveContext(Query, TenantId, TenantConfig)
        
        par Vector Database Search
            Retrieval->>VectorDB: searchVectors(Query Vector, Limit, Filters)
            VectorDB-->>Retrieval: Vector candidates
        and Relational Database Keyword Search
            Retrieval->>DB: searchKeywordIndex(Query Text, Limit, Filters)
            DB-->>Retrieval: Sparse candidates
        end
        
        Retrieval->>Retrieval: applyReciprocalRankFusion(Vector candidates, Sparse candidates)
        Retrieval->>Retrieval: applyRerankerModel(Candidates list)
        Retrieval-->>API: List[ChunkEntities]
    end

    rect rgb(240, 240, 240)
        Note over API, Client: Phase 3: Context Compilation & Generative Inference Streaming
        API->>Inference: compileContextPayload(Query, List[ChunkEntities], TenantConfig)
        Inference->>Inference: packContextWindow(PromptTemplate, MessagesHistory, Chunks)
        Inference-->>API: InferenceRequest (SystemPrompt, FormattedContext)

        API->>Cognitive: generateStream(InferenceRequest)
        
        loop Stream Tokens (Asynchronous Token Push)
            Cognitive-->>API: Token / Delta Output
            API->>API: runStreamingOutputValidation(Token payload)
            Note over API: Verifies citations, validates schemas, redacts PII.
            API-->>Client: SSE Event (token)
        end
        
        Cognitive-->>API: Completion Done Event
        API->>DB: recordInferenceLog(InferenceLogEntity)
        API-->>Client: SSE Event (done)
    end
```

---

### 6. Configuration-as-Data (CAD) Flow

To keep the platform headless and customizable, all tenant-specific behaviors are stored as structured configuration in the database. Prompt templates, LLM routes, chunk sizes, and retrieval weights are resolved dynamically at runtime.

```mermaid
sequenceDiagram
    autonumber
    Client Request->>API Gateway: POST /v1/tenants/{tenantId}/chat/sessions/{sessionId}/messages (Headers: API Key)
    API Gateway->>Identity Domain: validateToken(API Key)
    Identity Domain-->>API Gateway: UserContext (TenantId: T-800)
    
    API Gateway->>DB Cache: fetchActiveConfig(TenantId: T-800)
    Note over DB Cache: Checks Redis. If missed, queries Postgres Tenant Config registry.
    DB Cache-->>API Gateway: TenantConfig (ActiveModel: Claude-3-5, Temperature: 0.2, SystemPromptId: SP-99)
    
    API Gateway->>DB Cache: fetchPromptTemplate(PromptId: SP-99)
    DB Cache-->>API Gateway: Raw Template String
    
    API Gateway->>API Gateway: Resolve Prompt Placeholders
    API Gateway->>LlmProvider Port: generateStream(InferencePayload, TenantConfig)
```

---

### 7. Extension Points & Platform Contracts

Retriever is designed as an extensible platform. Custom integrations MUST connect to the core through the following Ports. Implementation details are decoupled from the application domain.

| Extension Name | Port Contract Interface | Primary Responsibility |
|---|---|---|
| **Parser Plugin** | `IngestionParser` | Decodes custom binary file formats into normalized plaintext payloads. |
| **OCR Plugin** | `OcrExtractor` | Extracts text layouts from layout images when parsing documents. |
| **Embedding Provider** | `EmbeddingsService` | Maps plaintext blocks to numeric vectors using specific cognitive models. |
| **Vector Store Provider** | `VectorDatabaseProvider` | Manages vector persistence, indexing, metadata filtering, and semantic query matching. |
| **LLM Provider** | `LlmProvider` | Orchestrates generation API completions and real-time Server-Sent Event streaming. |
| **Authentication Provider** | `IdentityProvider` | Decodes JWTs or API keys, resolving tenant identities and request scopes. |
| **Storage Provider** | `StorageProvider` | Manages raw document storage and handles presigned URL generation. |
| **Tool Provider** | `ExternalToolExecutor` | Executes actions requested by agentic inference loops (e.g., fetching weather, running APIs). |
| **Guardrail Provider** | `SafetyGuardrail` | Inspects input queries (block injections) and checks outputs (redact PII). |
| **Reranker Provider** | `ContextReranker` | Re-orders retrieved candidates based on cross-encoder similarity scoring. |
| **Citation Validator** | `CitationValidator` | Verifies that claims in generated tokens match source chunk identifiers. |
| **Domain Event Consumer** | `DomainEventHandler` | Subscribes to transaction events on the message bus (e.g., generating alerts). |
| **Evaluation Pipeline** | `ContextEvaluator` | Computes faithfulness, answer relevance, and context recall scores. |
| **Telemetry Exporter** | `TelemetryExporter` | Forwards performance spans, token usages, and logs to external targets. |

---
---

## Part II: Physical & Deployment Architecture

Part II defines the physical components, folder structures, deployment topologies, multi-tenancy mappings, and operational telemetry designs required to deploy and run the platform.

---

### 8. Monorepo Folder & Package Structure

Retriever is structured as a monorepo to maintain strong typing across client-server boundaries while isolating build environments:

```
/Users/prateeksharma/Developer/retriever/
├── apps/
│   ├── api/                     # API Serving Node (FastAPI implementation example)
│   │   ├── src/
│   │   │   ├── domain/          # Hexagonal Application Core (Logical Domains)
│   │   │   │   ├── abstractions/ # Port interfaces (contracts between layers)
│   │   │   │   ├── config/       # Configuration-as-Data service
│   │   │   │   ├── identity/     # Tenant isolation, auth, and credential validation
│   │   │   │   ├── ingestion/    # Document upload and validation
│   │   │   │   ├── knowledge/    # Chunking and text indexing logic
│   │   │   │   ├── retrieval/    # Hybrid search and reranking
│   │   │   │   └── inference/    # Prompt templating, citation, SSE pipelines
│   │   │   ├── adapters/        # Database, LLM, and storage adapters (Physical)
│   │   │   └── main.py          # API entrypoint
│   │   ├── pyproject.toml
│   │   └── uv.lock
│   │
│   ├── web/                     # Admin Dashboard (Next.js)
│   │   ├── src/
│   │   │   └── app/             # Web Router layouts and pages
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   └── client-reference/        # Reference client integration example (Next.js)
│
├── workers/                     # Celery background workers (async ingestion)
│
├── packages/
│   └── processing-core/         # Shared processing primitives (PDF parse, chunk, embed)
│
├── docs/
│   ├── constitution/            # Master Vision and engineering rules
│   │   └── master-vision.md
│   ├── decisions/               # Architecture Decision Records
│   └── architecture.md          # Canonical Architectural Blueprint
```

---

### 9. Multi-Tenancy Mappings & Security Architecture

#### 9.1 Tenant Isolation Levels
Retriever supports three runtime isolation levels, configured in the platform registry:
1.  **Logical Isolation:** All tenant records reside in shared tables. PostgreSQL Row-Level Security (RLS) is enabled on all tables. Queries MUST execute through a transaction context setting `app.current_tenant_id`.
2.  **Schema Isolation:** Each tenant is assigned a distinct logical database schema (e.g., `tenant_a`, `tenant_b`). The database adapter switches the connection search path dynamically per request.
3.  **Physical Isolation:** Enterprise tenants utilize distinct database connection strings. The infrastructure router maps incoming request headers to dedicated database instances.

```
       TENANT DATA ISOLATION PATTERNS
       
       1. LOGICAL ISOLATION (Shared DB, RLS Protection)
          API Client (Tenant: A) -> Set Tenant Context Variable -> Postgres (RLS checks TenantId = Context)
          
       2. SCHEMA ISOLATION (Shared DB, Isolated Logical Schemas)
          API Client (Tenant: B) -> Select Tenant Schema Context -> Postgres (Executes queries inside schema_tenant_b)
          
       3. PHYSICAL ISOLATION (Distinct Database Instances)
          API Client (Tenant: C) -> Route Connection String -> Dedicated Postgres Cluster (Tenant C)
```

#### 9.2 Context Middleware & Breach Kill-Switch
*   **Context Injection:** Authentication middleware resolves the validated `TenantId` from the incoming token and injects it into a thread-safe local execution context.
*   **Isolation Assertions:** Database adapters MUST check that the target query parameters contain a tenant ID filter matching the authenticated request context.
*   **The Tenancy Breach Kill-Switch:** If the database adapter detects a tenant ID mismatch between the request context and the retrieved records, it MUST trigger the security protocol:
    1.  Terminate the active database connection pool.
    2.  Log a Severity-1 security incident.
    3.  Revoke the API keys associated with the caller.
    4.  Return a generic `403 Forbidden` response to the client.

---

### 10. Background Processing & Messaging Topology

Retriever uses an asynchronous event bus to manage long-running write operations (such as file parsing, metadata indexing, and vector processing) without degrading API responsiveness.

```mermaid
graph LR
    subgraph WriteAPI["API Ingestion Node"]
        API["Ingestion API Endpoints"]
        RelationalStore["PostgreSQL Relational Storage"]
    end

    subgraph EventBus["RabbitMQ / Event Bus Broker"]
        Exchange["Document Processing Exchange"]
        Queue["Processing Queue (Direct)"]
        DLX["Dead Letter Exchange"]
        DLQ["Dead Letter Queue"]
    end

    subgraph IndexingWorkers["Asynchronous Parsing Workers"]
        Worker1["Celery Parser Node 1"]
        Worker2["Celery Parser Node 2"]
    end

    API -->|1. Write Record: PENDING| RelationalStore
    API -->|2. Publish Event| Exchange
    Exchange -->|Route| Queue
    Queue -->|3. Consume Task| Worker1
    Queue -->|3. Consume Task| Worker2

    %% Failure Routing
    Worker1 -->|Failures / Max Retries| DLX
    DLX --> DLQ
```

*   **Message Broker:** Technology options like RabbitMQ or Redis PubSub handle out-of-process task coordination. The broker architecture MUST utilize persistent queues to prevent message loss during hardware outages.
*   **Durable Event Routing:** Task messages MUST use structured formats containing `document_id`, `tenant_id`, and `storage_url`. Message payloads MUST NOT contain raw binaries.
*   **Dead Letter Queues (DLQ):** Task processing failures that exceed maximum retry thresholds MUST route to a Dead Letter Queue (DLQ) for auditing.

---

### 11. Deployment Topology & Performance Budgets

Retriever is designed to deploy on container orchestration clusters (e.g., Kubernetes), separating stateful storage components from stateless serving APIs.

```mermaid
graph TB
    subgraph IngressLayer["Ingress & Routing Layer"]
        LB["External Load Balancer"]
        Ingress["Ingress Controller"]
    end

    subgraph ServiceLayer["API & Parsing Clusters (Stateless)"]
        APIPod1["FastAPI Pod 1"]
        APIPod2["FastAPI Pod 2"]
        WorkerPod1["Ingestion Parser Sandbox Pod 1"]
        WorkerPod2["Ingestion Parser Sandbox Pod 2"]
    end

    subgraph StateLayer["Data Storage & Event Clusters (Stateful)"]
        RedisCluster["Redis Cache (Tenant Config & Traces)"]
        RabbitMQ["RabbitMQ Broker (Task Queue)"]
        PostgresCluster["Primary Relational DB (PostgreSQL RLS)"]
        VectorStoreCluster["Vector Storage DB"]
    end

    %% Routing Flow
    LB --> Ingress
    Ingress --> APIPod1
    Ingress --> APIPod2

    %% API to Storage
    APIPod1 --> RedisCluster
    APIPod2 --> RedisCluster
    APIPod1 --> PostgresCluster
    APIPod2 --> PostgresCluster
    
    %% Async parsing trigger via RabbitMQ (ADR-004)
    APIPod1 -->|Publish tasks| RabbitMQ
    WorkerPod1 -->|Consume tasks| RabbitMQ
    WorkerPod2 -->|Consume tasks| RabbitMQ
    
    %% Workers to DB
    WorkerPod1 --> PostgresCluster
    WorkerPod2 --> PostgresCluster
    WorkerPod1 --> VectorStoreCluster
    WorkerPod2 --> VectorStoreCluster
```

#### 11.1 Deployment Architecture Rules
*   **Stateless Container Scaling:** API Pods and Workers MUST run in stateless configurations, scaling horizontally based on CPU utilization and request queues.
*   **Sandboxed Parsing Pods:** Worker pods parsing documents MUST execute in restricted sandbox environments. These sandboxes MUST block all egress traffic to prevent unauthorized data transmission.

#### 11.2 Performance Budget Rules
Every component in the query pipeline is allocated a latency budget, monitored through tracing.

| Execution Layer | Latency Target | Telemetry Span Name |
|---|---|---|
| Network & Request Routing | <= 20ms | `ingress.routing` |
| Authentication & Identity Validation | <= 30ms | `auth.tenant_resolve` |
| Parallel Vector & Sparse DB Search | <= 100ms | `retrieval.db_search` |
| RRF Context Fusion & Reranking | <= 50ms | `retrieval.reranking` |
| Inference Prep & System Prompt Compile | <= 100ms | `inference.prompt_compile` |
| LLM Time-To-First-Token | <= 500ms | `cognitive.llm_stream_start` |

---

### 12. Scalability & Telemetry Considerations

#### 12.1 Observability & Telemetry Tracing
To trace requests across asynchronous queues and LLM API completions:
*   **Trace Context Propagation:** API endpoints MUST generate a unique trace ID and inject it into the request headers. This trace ID MUST be propagated across messaging queues and external adapter calls.
*   **Structured Instrumentation:** Telemetry spans MUST record:
    *   Vector database similarity search score profiles.
    *   Tokenizer performance metrics and token usage tallies.
    *   Reranker confidence indices.
    *   Cognitive provider response times.
*   **OpenTelemetry Exports:** Spans MUST export to OpenTelemetry collectors, allowing integration with observability platforms (e.g., Datadog, Prometheus, or Jaeger).
*   **Error Tracking:** Sentry is initialized in the API and Celery worker processes (via `worker_process_init` signal) for exception grouping, release tracking, and breadcrumbs. Sentry integrates with OpenTelemetry so traces and errors appear in one view. Configured via `SENTRY_DSN`; skipped when DSN is empty. Parser sandbox containers are excluded from Sentry to maintain zero-egress security.

#### 12.2 Scalability Bottlenecks & Caching Architecture
*   **SSE Connection Management:** High concurrent streaming loads exhaust API server thread pools. The gateway MUST route SSE connections through asynchronous network workers, decoupling request threads from stream lifecycles.
*   **Caching Strategy:** The caching layer uses a multi-tier structure:
    *   **L1 In-Memory Cache:** Active tenant configurations and compiled prompts are cached in memory (e.g., Redis) with short TTLs (1 hour), minimizing relational database requests.
    *   **L2 Similarity Cache:** Search query vectors are matched against a cache of previous query coordinates. If an incoming query is semantically identical to a cached query (e.g., similarity > 0.99), the system returns cached retrieval results, avoiding redundant database lookups.

---
---

## Part III: Governance, Resilience, & Traceability

Part III documents resilience parameters, retry policies, system recovery procedures, and traces how architectural decisions comply with the Engineering Constitution.

---

### 13. Resilience & Failure Architecture

This section documents the expected behavior, retry strategies, and recovery procedures for major failure scenarios within Retriever's distributed topology.

| Failure Scenario | Expected System Behavior | Retry Strategy & Backoff | Circuit Breaker & Fallback | User-Visible Response | Recovery Process |
|---|---|---|---|---|---|
| **Parser Failure** | The worker halts binary processing, catches the exception, and marks the document status as `FAILED`. | Do NOT retry document syntax errors. Retry network timeout parser calls up to 3 times (linear 5s backoff). | Fall back to clean plaintext layout parsing. Skip OCR extraction if visual engines crash. | Ingestion interface displays status `Failed` with details. | User must resolve formatting issues and upload the document again. |
| **Embedding Generation Failure** | Indexing worker flags chunk state as `UNINDEXED`. Chunk text remains cached in DB. | Retry up to 5 times (exponential backoff starting at 2s with jitter). | Fall back to secondary configured embedding provider adapter (e.g., local backup engine). | Document remains in state `INDEXING`. Retrieval matches skip this chunk. | Background task reconciler periodically retries `UNINDEXED` chunks. |
| **Vector DB Outage** | Similarity searches raise network exceptions. Retrieval domain falls back to text. | Retry connection pool up to 3 times (1s backoff). | Break circuit. Fall back to sparse text keyword search inside relational database. | Searches execute successfully but with reduced semantic quality (degraded mode). | Alerts generated. Vector cluster is restarted; missing vectors are rebuilt from chunk store. |
| **Relational DB Outage** | Connection pools fail to acquire database transactions. Core API throws `503`. | Retry pool connection up to 5 times (exponential backoff). | Open circuit breaker. Severe write path; reject incoming commands. | API returns HTTP `503 Service Unavailable`. SSE streams report `SYSTEM_ERROR`. | Primary database fails over to read-replica or multi-region standby cluster. |
| **Message Broker Outage** | Ingest API fails to publish `DocumentUploadedEvent` task triggers. | Retry socket connection up to 5 times. | Cache events in primary database event log. Process logs using database triggers. | Ingest API accepts uploads but indexes do not process (stuck in `PENDING`). | Broker is restarted; ingestion workers consume events from database reconciler logs. |
| **LLM Outage / Timeout** | Client completion streams block. Inference engine raises network exception. | Retry once if timeout occurs. Do NOT retry on rate-limits (HTTP 429). | Break circuit. Route completion request to fallback model adapter. | Completion streams display fallback model tag or close stream with error. | Automatic model router updates latency weights dynamically. |
| **Worker Node Crash** | Parsing or indexing process crashes mid-task. Memory partition is lost. | Task message is returned to Queue via acknowledgement failure. | RabbitMQ re-queues task to secondary worker container. | Document remains in state `INDEXING` or `PENDING` longer than average. | Container orchestration restarts worker node container automatically. |
| **Duplicate Event Delivery** | Duplicate task messages are received by the event queue. | Discard event if document hash exists in database. | Handled via unique index constraint on `FileHash` parameter. | Document processes normally. No duplicate chunk entities are written. | None required. Deduplication logic handles duplicates silently. |
| **Retry Exhaustion** | Background indexing tasks fail repeatedly and exhaust retry attempts. | Halt processing. | Move task parameters from Queue to Dead Letter Queue (DLQ). | Document transitions from `INDEXING` state to `FAILED`. | Administrators review DLQ error dumps manually and trigger re-vectorization. |

---

### 14. Traceability Map (Mapping to the Engineering Constitution)

To guarantee alignment, this architecture design maps directly back to the [Engineering Constitution](file:///Users/prateeksharma/Developer/retriever/docs/constitution/master-vision.md).

| Architectural Pattern / Design Choice | Target Section of the Constitution | Rationale and Verification Method |
|---|---|---|
| Hexagonal application core architecture | Section 6.1 (Architectural Philosophy) | Core domains (`ingestion`, `knowledge`, `retrieval`, `inference`) interact with external databases and providers only through abstract ports, ensuring the platform remains provider-agnostic. |
| Ingestion parsing sandboxing | Section 8.1 (Ingestion, Knowledge, and Retrieval Engine) & Section 17.3 (Rule 15) | Binary parsing operations run inside isolated containers to prevent processing exploits from compromising main serving APIs. |
| CQRS Read/Write isolation | Section 6.4 (Command Query Responsibility Segregation (CQRS)) | Separate ingestion worker pipelines (Write path) from parallel retrieval engines (Read path), protecting search latency budgets. |
| Dynamic configuration cache | Section 9.1 (Configuration Philosophy) | All prompt strings and model routes are resolved dynamically from database tables based on tenant ID context. Hardcoded prompts are prohibited. |
| PostgreSQL RLS mapping | Section 14.1 (Tenant Isolation Models) | Logical data tables utilize PostgreSQL Row-Level Security policies to prevent cross-tenant access. |
| Tenancy Kill-Switch adapter validation | Section 17.1 (The Tenancy Breach Kill-Switch) | Database and vector store adapters verify the request tenant context against retrieved records. Any mismatch terminates the database connection. |
| OpenTelemetry trace tracking | Section 17.3 (Rule 8) | Trace IDs are generated at the API ingress and propagated across background queues and LLM client adapters to track performance. |
| Manual validation hooks | Section 8.4 (Model Routing, Guardrails, & Tool Execution) | The Inference engine pauses tool executions and registers verification tokens in the database, waiting for user approval. |

---

## 15. Client Integration Model

### 15.1 How Frontends Connect

Retriever is a headless RAG engine. Every client frontend — coaching portal, CA assistant, legal tool — connects through the same simple contract:

```
Client Frontend (Next.js, React, mobile app, etc.)
  │
  │  POST /v1/tenants/{tenantId}/chat/sessions
  │  Headers:
  │    X-API-Key: sk_client_abc123
  │    X-User-ID: user_42
  │    Content-Type: application/json
  │
  ▼
Retriever API
  ├── 1. Validate API key → resolve tenant_id, scope (admin | client)
  ├── 2. Set RLS context: app.current_tenant_id = tenant_id
  ├── 3. If client-scoped key: set app.current_user_id from X-User-ID
  ├── 4. Execute RAG pipeline (retrieve → rerank → prompt → LLM → stream)
  └── 5. Return SSE stream or JSON response
```

### 15.2 Authentication & Authorization

| Credential | Who carries it | What it grants |
|---|---|---|
| **Admin API Key** | Admin dashboard | Full CRUD across all tenants. Bypasses user filter. Can manage configs, prompts, keys. |
| **Client API Key** | Client frontend | Scoped to one tenant. `X-User-ID` header filters chat data. Cannot access other tenants. |
| **`X-User-ID` header** | Client frontend (passed per-request) | Identifies which user within the tenant is acting. The frontend is responsible for authenticating its own users. Retriever never creates or verifies user accounts. |

### 15.3 Data Isolation Boundaries

| Data | Scoped By | Accessible By |
|---|---|---|
| Documents, chunks, configs, prompts | `tenant_id` | All users within the client tenant + admin |
| Chat sessions, messages, inference logs | `tenant_id` + `user_id` | Only the owning user + admin (bypasses user filter) |
| API keys, tenant metadata | `tenant_id` (admin: all) | Admin sees all; client sees own |

### 15.4 Per-Client LLK Key Resolution

LLM API keys are resolved in the following priority (first match wins):

1. **Request header** `X-LLM-Key` — frontend override (for advanced clients who bring their own key)
2. **Tenant config** `llm_api_key` — stored encrypted in DB, configured via admin API
3. **Environment variable** `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` — deployment-wide fallback

This means a coaching portal can use the coaching institute's own OpenAI key, while the admin dashboard uses the platform key, and an advanced client can override per-request. All without code changes.
