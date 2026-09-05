# ADR-020: Sovereign Edge SQLite & Vector Synchronization Architecture

**Status:** Accepted  
**Date:** 2026-09-05  
**Deciders:** Core Engineering Team, Distributed Systems Architects, Mobile/Edge Specialists  
**Consulted:** Security Auditors, Enterprise Solution Architects, Multi-Tenancy Leads  
**Informed:** Enterprise Clients, Field Operations Teams, Platform Tenants  

---

## 1. Context and Problem Statement

As Retriever expanded to enterprise and industrial deployments, clients increasingly deployed AI copilots, field inspection tools, and autonomous agent swarms in environments characterized by:
1. **Network Disconnections & High Latency:** Mining operations, maritime vessels, defense field devices, aircraft maintenance hangars, and factory floors experience frequent WAN dropouts. A cloud-only pgvector architecture halts all reasoning when the internet drops.
2. **Sub-5ms Latency Requirements:** High-frequency robotic agents and local voice assistants cannot tolerate 100–300ms cloud network roundtrips for iterative retrieval loops.
3. **Data Sovereignty & Air-Gapped Compliance:** Strict jurisdictional compliance (e.g. EU GDPR sovereign borders, healthcare HIPAA air-gapped enclaves, defense ITAR constraints) forbids egress of raw vectorized embeddings or sensitive documents to public cloud infrastructure.
4. **Heavy Edge Daemon Fragility:** Running separate client-side vector database daemons (such as Milvus, Qdrant, or Pinecone local agents) on edge machines (e.g. Raspberry Pi, iPad, field laptops, Point-of-Sale terminals) incurs high memory footprints (>500MB), complex process supervisors, and fragile cross-compilation hurdles.

To solve this, Retriever required **Platform Battery #18: Sovereign Edge SQLite / Turso Vector Synchronization & Offline-First Edge Agent**.

The platform needed:
- A self-contained, in-process edge storage engine requiring **zero external daemons**.
- Embedded hybrid retrieval uniting SQLite 3 native **FTS5 full-text BM25** with binary **IEEE 754 float32 vector BLOBs** and in-process NumPy cosine similarity scoring.
- Cryptographic differential delta synchronization (`sequence_num` watermarking, SHA-256 state hashing) to transfer only newly inserted or modified chunks over constrained edge links.
- 1-Click standalone `.sqlite` bundle exports for instant air-gapped device deployment.
- Bi-directional offline mutation reconciliation with **Lamport logical timestamps** and Last-Write-Wins (LWW) conflict resolution.

---

## 2. Decision Drivers

- **Zero-Dependency In-Process Runtime:** The edge engine must run wherever standard SQLite 3 and Python/Node/Rust run, requiring zero background service managers or daemon containers.
- **Microsecond Query Latency:** Local vector dot-products on $d=768$ embeddings and FTS5 BM25 queries must execute in $<2\text{ms}$ on commodity hardware.
- **Strict Multi-Tenant Isolation:** Edge nodes belong strictly to a single `tenant_id`. Sequence tracking and checkpoints are strictly partitioned in PostgreSQL (`edge_nodes`, `edge_sync_checkpoints`).
- **Cryptographic State Integrity:** Every differential delta and bundle includes a deterministic SHA-256 hash verified by the edge node before committing to local SQLite.
- **Bi-Directional Eventual Consistency:** Edge mutations (feedback, user queries, local document annotations) queued during network isolation must seamlessly reconcile upon cloud reconnection using Lamport clocks.

---

## 3. Considered Options

### Option 1: Embedded DuckDB with `duckdb-vss`
- *Pros:* High columnar analytical throughput.
- *Cons:* Dynamic shared library compilation (`.duckdb_extension`) fails frequently across embedded ARM/iOS platforms; large disk footprint; overkill for pointwise hybrid chunk retrieval.

### Option 2: Local Dockerized Vector Daemons (Qdrant / Milvus Local)
- *Pros:* Native HNSW indexing out of the box.
- *Cons:* Heavy RAM footprint (400MB–1GB idle); requires Docker daemon on edge devices; cannot run inside iOS, Android, or browser WASM environments; high operational failure rate.

### Option 3: Sovereign SQLite 3 + FTS5 + Binary float32 BLOB Vector In-Process Engine (Chosen)
- *Pros:* 
  - Standard SQLite 3 is pre-installed on virtually every operating system on Earth (macOS, Linux, Windows, Android, iOS).
  - Single portable file (`.sqlite`) containing schema, documents, chunks, BM25 indices, and vector embeddings.
  - Zero background daemon requirement.
  - Sub-2ms cosine similarity via memory-aligned binary float32 BLOBs and vectorized NumPy dot products.
  - Reciprocal Rank Fusion ($k=60$) seamlessly executed in-process.

---

## 4. Architectural Decision

We architected and implemented the **Sovereign Edge Synchronization Engine** following strict Hexagonal Architecture boundaries across 4 distinct layers:

```mermaid
graph TD
    subgraph Cloud Control Plane ["Cloud Infrastructure (FastAPI + PostgreSQL + pgvector)"]
        PG[(PostgreSQL pgvector)]
        Adapter[EdgeSyncAdapter]
        DeltaCalc[DeltaCalculator]
        Reconciler[EdgeMutationReconciler]
        Router[FastAPI Edge Router /v1/tenants/{id}/edge/*]
    end

    subgraph Edge Distribution ["Over-The-Air or Air-Gapped Transfer"]
        Delta[EdgeSyncDelta JSON / Diff]
        Bundle[Standalone .sqlite Bundle File]
        Mutations[Queued EdgeMutations with Lamport Clocks]
    end

    subgraph Sovereign Edge Runtime ["Sovereign Edge Client (Laptop, Field Unit, Mobile)"]
        SQLite[(Local SQLite 3 Database)]
        FTS5[SQLite FTS5 BM25 Virtual Table]
        BlobVec[Binary float32 Vector BLOBs]
        NumPyVec[NumPy / BLAS Cosine Dot Product]
        Fusion[Reciprocal Rank Fusion k=60]
        LocalEngine[SQLiteEdgeEngine]
    end

    PG -->|Fetch chunks & pgvectors| Adapter
    Adapter -->|Compute sequence diff & SHA-256| DeltaCalc
    DeltaCalc -->|Deliver updates| Router
    Router -->|OTA Delta Sync| Delta
    Router -->|1-Click Download| Bundle
    Delta -->|Apply delta transactionally| LocalEngine
    Bundle -->|Mount zero-copy| SQLite

    LocalEngine -->|FTS5 match| FTS5
    LocalEngine -->|Binary cosine| NumPyVec
    NumPyVec -->|Scores| Fusion
    FTS5 -->|Scores| Fusion
    Fusion -->|Merged Top-K < 2ms| SovereignEdgeAgent[Offline Sovereign Agent]

    SovereignEdgeAgent -->|Record offline mutations| LocalEngine
    LocalEngine -->|Queued offline mutations| Mutations
    Mutations -->|Reconnection sync| Router
    Router -->|Reconcile| Reconciler
    Reconciler -->|LWW commit| PG
```

### 4.1 Schema Topology inside the Standalone SQLite Bundle

The generated `.sqlite` database embeds full schema, full-text virtual tables, and vector metadata:

```sql
-- Chunks storage with document metadata
CREATE TABLE IF NOT EXISTS edge_chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    metadata_json TEXT,
    sequence_num INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

-- Native SQLite FTS5 BM25 search table
CREATE VIRTUAL TABLE IF NOT EXISTS edge_chunks_fts USING fts5(
    chunk_id UNINDEXED,
    content,
    tokenize = 'porter unicode61'
);

-- Binary float32 vector BLOB storage
CREATE TABLE IF NOT EXISTS edge_vectors (
    chunk_id TEXT PRIMARY KEY,
    dimension INTEGER NOT NULL,
    vector_blob BLOB NOT NULL,
    FOREIGN KEY(chunk_id) REFERENCES edge_chunks(chunk_id) ON DELETE CASCADE
);

-- Local mutation log for offline auditing and cloud reconciliation
CREATE TABLE IF NOT EXISTS edge_mutation_log (
    mutation_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    action TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    lamport_timestamp INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    synced_to_cloud INTEGER DEFAULT 0
);
```

### 4.2 Vector BLOB Storage and In-Process Cosine Search

Embeddings are serialized as raw IEEE 754 32-bit floating point buffers (`struct.pack(f'{dim}f', *embedding)`). At query time:
1. `SQLiteEdgeEngine` queries all candidate binary BLOBs into memory.
2. Vectors are converted to a contiguous 2D float32 NumPy array without memory copying (`np.frombuffer(raw_blob, dtype=np.float32)`).
3. The normalized query embedding performs matrix dot product multiplication:
   $$\text{similarity} = \frac{\mathbf{Q} \cdot \mathbf{V}_i}{\|\mathbf{Q}\| \|\mathbf{V}_i\|}$$
4. RRF (Reciprocal Rank Fusion) computes the blended rank:
   $$\text{RRF}(d) = \alpha \cdot \frac{1}{k + \text{rank}_{\text{vector}}(d)} + (1 - \alpha) \cdot \frac{1}{k + \text{rank}_{\text{BM25}}(d)}$$

Benchmark tests demonstrate sub-2ms hybrid retrieval on 10,000 local chunks on standard Apple Silicon and Linux x86_64 machines.

### 4.3 Sequence Watermarking & Differential Delta Sync

1. Every document chunk in cloud PostgreSQL is assigned a monotonic sequence number (`sequence_num = 1, 2, ...`).
2. Cloud checkpoints store the global high-watermark sequence (`EdgeSyncCheckpointDb`).
3. When an edge node requests a sync delta:
   - It transmits its current watermark: `GET /v1/tenants/{id}/edge/delta?since_sequence=42`.
   - The backend queries only chunks where `sequence_num > 42`.
   - The delta computes an overall SHA-256 state hash over sorted chunk IDs and sequences.
   - The edge node validates the SHA-256 checksum and executes an atomic SQLite transaction:
     ```python
     with conn:
         for chunk in delta.added_chunks:
             conn.execute("INSERT OR REPLACE INTO edge_chunks ...")
             conn.execute("INSERT OR REPLACE INTO edge_chunks_fts ...")
         for vec in delta.added_vectors:
             conn.execute("INSERT OR REPLACE INTO edge_vectors ...")
     ```

### 4.4 Bi-Directional Mutation Reconciliation

When an edge node creates entities offline (such as user message feedback or field annotations):
1. A local **Lamport logical clock** is incremented: $L_{\text{local}} = L_{\text{local}} + 1$.
2. The mutation is saved to `edge_mutation_log`.
3. When network connectivity restores, the client POSTs mutations to `/v1/tenants/{id}/edge/mutations`.
4. `EdgeMutationReconciler` inspects the cloud entity:
   - If the server has a conflicting mutation with a higher sequence, Last-Write-Wins (LWW) is resolved based on Lamport timestamps and UTC timestamps.
   - Accepted mutations are committed to cloud PostgreSQL (`ChatMessageFeedbackDb`), and an `EdgeSyncConflictResolution` receipt is returned to the edge node.

---

## 5. Consequences

### 5.1 Positive Consequences
- **True Offline Autonomy:** Agents continue executing hybrid search, contextual grounding, and feedback logging during prolonged network partitions.
- **Air-Gapped Deployment:** Operations teams can download a single `.sqlite` file from the Admin Dashboard and transfer it via secure USB to air-gapped environments.
- **Zero Cloud Egress:** Client data never leaves the sovereign boundary in air-gapped mode.
- **Extremely Lightweight:** Zero background daemon processes, zero Docker containers on client machines.
- **Platform Battery #18 Registered:** Standardized discovery via `/v1/admin/batteries` under category `EDGE_DISTRIBUTION`.

### 5.2 Negative Consequences & Mitigations
- *Vector Scale Ceiling:* In-process NumPy cosine matrix multiplication is optimal up to $\approx 50,000$ chunks ($<10\text{ms}$). For edge devices indexing millions of chunks, approximate nearest neighbors (such as `sqlite-vss` or hierarchical k-means quantization) will be introduced in future sub-milestones.
- *Binary Blob Portability:* Float32 IEEE 754 is universally supported across standard CPU architectures (ARM64, x86_64), but endianness must remain Little Endian (standard on all modern consumer and server processors).

---

## 6. Verification and Test Results

- **Backend Pytest Suite:** `tests/test_edge_sync.py` passed **13/13 tests** in 3.78 seconds.
- **Web Admin Dashboard Build:** `retriever/apps/web` compiled with **0 errors**, hosting `/edge` route.
- **Client Web Studio Vitest Suite:** `Prateek_website` passed **7/7 tests** in 505ms.
- **Full Production Next.js 16 Build:** Clean compilation with **0 TypeScript errors** across 50 static/dynamic routes.
