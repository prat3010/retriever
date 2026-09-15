# Decentralized Multi-Tenant Vector Sharding & Distributed Raft Consensus

> **Platform Battery:** #32 (`vector_raft_sharding`)  
> **Category:** `EDGE_DISTRIBUTION`  
> **Milestone:** M117 (`v1.7.0-alpha1`)  
> **Health Check Endpoint:** `GET /v1/shards/topology`  

---

## 1. Architectural Overview

The **Vector Sharding & Distributed Raft Consensus** engine horizontally partitions multi-tenant vector embedding collections across cluster nodes while maintaining index consistency and fault tolerance:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        CONSISTENT HASH RING                            │
│                 [0 ----------------- 4,294,967,295]                   │
│                                                                        │
│       Shard 000          Shard 001         Shard 002    ... Shard 007  │
│      (64 vnodes)        (64 vnodes)       (64 vnodes)                  │
├────────────────────────────────────────────────────────────────────────┤
│                     RAFT CONSENSUS REPLICA GROUPS                      │
│                                                                        │
│      [Node 01: Leader]  [Node 02: Leader]  [Node 03: Leader]           │
│      Replicas: 02, 03   Replicas: 01, 03   Replicas: 01, 02            │
├────────────────────────────────────────────────────────────────────────┤
│                       SCATTER-GATHER FAN-OUT                           │
│                                                                        │
│   Query Vector ──► Broadcast to Partitions ──► Local Top-K Search      │
│                ◄── Collect & RRF Rank Merge ◄── Score Normalization    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Concepts

### 1. Consistent Virtual-Node Hashing
- **Hash Ring:** 32-bit integer range $[0, 2^{32}-1]$ utilizing deterministic FNV-1a hashing.
- **Virtual Nodes:** 64 virtual points per shard partition distributed around the ring to guarantee uniform key distribution and prevent hotspotting.
- **Tenant Isolation:** Tenants with high security or high-volume requirements can be assigned dedicated partitions, while standard tenants share uniform hash slices.

### 2. Distributed Raft Consensus
- **Terms & Roles:** Nodes transition between `LEADER`, `FOLLOWER`, and `CANDIDATE` states.
- **Elections:** Leader election requires a strict majority quorum ($\lfloor N/2 \rfloor + 1$).
- **Replicated Log:** Vector insertions, deletions, and shard reconfigurations are appended as immutable `RaftLogEntry` records and committed only after majority replica acknowledgment.

### 3. Scatter-Gather Parallel Vector Search
- **Fan-Out:** Parallel asynchronous search tasks dispatched across target partition replicas.
- **Tunable Read Quorum:**
  - `LOCAL`: Lowest latency (<2ms); query served by local replica.
  - `ONE`: First replica to respond.
  - `QUORUM`: Majority of partition replicas must respond.
  - `ALL`: Strict consistency across 100% of replicas.
- **Rank Score Fusion:** Candidate vectors normalized and deduplicated by `chunk_id` keeping highest cosine similarity.

### 4. Zero-Downtime Shard Migration
- **Skew Detection:** Evaluates standard deviation of vector counts across nodes.
- **2-Phase Migration:**
  1. *Snapshot Transfer:* Background snapshot streamed to target node while source continues serving reads.
  2. *Delta Replay & Cutover:* Catchup logs replayed and atomic lease handoff completed without dropping queries.

---

## 3. REST API Reference

| Endpoint | Method | Description |
|:---|:---:|:---|
| `/v1/shards/topology` | `GET` | Returns shard partitions, hash boundaries, leaders, and replicas |
| `/v1/shards/query` | `POST` | Executes parallel scatter-gather vector query with latency breakdown |
| `/v1/shards/mutate` | `POST` | Replicates vector mutations via Raft consensus log |
| `/v1/shards/raft/status` | `GET` | Cluster Raft consensus telemetry, current term, and log health |
| `/v1/shards/election` | `POST` | Simulates Raft leader election for a candidate node |
| `/v1/shards/rebalance` | `POST` | Triggers online shard migration to eliminate cluster skew |
| `/v1/shards/{shard_id}/snapshot` | `POST` | Captures immutable shard state snapshot |
