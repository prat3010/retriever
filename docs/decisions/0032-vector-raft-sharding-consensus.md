# 0032. Decentralized Multi-Tenant Vector Sharding & Distributed Raft Consensus

Date: 2026-09-15
Status: Accepted

## Context
As multi-tenant vector repositories scale to hundreds of thousands of document embeddings, single-node pgvector / HNSW index instances encounter physical RAM capacity boundaries and CPU contention during concurrent nearest-neighbor queries.

To enable horizontal elasticity while preserving strict multi-tenant isolation and index consistency, the platform required:
1. Horizontal partitioning across a deterministic consistent hash ring.
2. An in-process Raft consensus state machine to replicate vector index mutations (insert, update, delete, index snapshot) across replica groups without split-brain risk.
3. Scatter-gather parallel query execution with global reciprocal rank fusion and tunable read quorums.
4. Zero-downtime shard migration and rebalancing when node storage or query load becomes skewed.

## Decision
We implemented **Platform Battery #32: `vector_raft_sharding`**:
1. **Virtual-Node Consistent Hashing**: 64 virtual nodes per shard mapped across a 32-bit integer ring $[0, 2^{32}-1]$ via deterministic FNV-1a hashing. Supports dedicated tenant-isolated shards or shared multi-tenant partitions.
2. **Raft State Machine**: Implements terms, candidate elections with majority quorum ($\lfloor N/2 \rfloor + 1$), heartbeat leases (50ms interval), and replicated AppendEntries logs for vector mutations.
3. **Scatter-Gather Parallel Search**: Concurrent async fan-out across shard partition replicas with score normalization, duplicate suppression by `chunk_id`, and configurable read quorums (`LOCAL`, `ONE`, `QUORUM`, `ALL`).
4. **Online Shard Rebalancing**: Evaluates vector distribution skew standard deviation and executes a 2-phase migration (snapshot streaming followed by delta log replay and atomic lease cutover) with zero query downtime.
5. **Decoupled Client SDKs**: Exported full sharding and Raft consensus API parity to `@prat3010/retriever-client` (TypeScript) and `retriever-python` (PyPI).
6. **SaaS Studio Control Plane**: Added dedicated "Vector Shards & Raft" tab in `/rag/app` with hash ring topology visualizers, live Raft consensus monitors, scatter-gather latency waterfalls, and rebalancing controls under Design System 2.0.

## Consequences
- Single nodes no longer bottleneck large vector vaults; partitions can scale horizontally.
- Raft consensus guarantees deterministic replicated state and failover without external coordination dependencies like Zookeeper or etcd.
- Strict read quorums ensure callers can select between ultra-low-latency local reads (`LOCAL`) and strict consensus (`ALL`).
