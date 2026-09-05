# Distributed Multi-Cloud Failover & Edge Turso LibSQL Replication Engine

**Milestone:** M99 (v0.84.0)  
**System Layer:** Distributed Sovereign Edge & Multi-Cloud Resiliency (Platform Battery #19)  
**Architecture:** Hexagonal Domain Protocols + Quorum Consensus Failover + Circuit Breaker EWMA + Embedded Turso LibSQL WAL Streaming  

---

## 1. Executive Summary

Milestone 99 delivers **Platform Battery #19: `multicloud_failover_libsql`**, completing the enterprise high-availability and distributed resilience foundations of the Retriever cognitive platform.

Prior to Milestone 99, Retriever operated as a single-region deployment anchored on an Oracle Cloud Infrastructure VPS in Mumbai (`oracle-bom`, `130.210.35.134`). While high-performance, single-cloud deployments present unacceptable enterprise risks:
- Datacenter-wide power/fiber cuts take down the entire RAG pipeline.
- Cross-continental API requests from North America and Europe suffer 150–250ms roundtrip latencies for read-heavy operations.
- Naive failovers risk catastrophic **split-brain data corruption** where multiple nodes write contradictory data concurrently.

Milestone 99 solves this by introducing:
1. **Heterogeneous Multi-Cloud Cluster Topology:** Nodes spanning Oracle Cloud (`oracle-bom`), Amazon Web Services (`aws-iad`), Fly.io (`fly-fra`), and Cloudflare Global Anycast Edge (`cf-global`).
2. **Mathematical Quorum Consensus ($>50\%$ Majority):** An election engine requiring at least $\lfloor N/2 \rfloor + 1 = 3$ votes out of 4 nodes before promoting any standby node to active leader.
3. **Monotonic Generation Terms:** Epoch counter preventing stale, partitioned nodes from accepting writes upon rejoining the cluster.
4. **Dynamic Circuit Breaker & EWMA Latency Tracking:** Auto-failover triggered when a leader fails 3 consecutive heartbeats or its exponentially weighted moving average latency exceeds $1500\text{ms}$.
5. **Turso LibSQL Embedded Replicas:** Local SQLite-compatible database replicas delivering sub-1ms read latency on edge nodes with asynchronous WAL frame streaming and write-through proxying to the primary.
6. **Unified Dual-Surface Dashboards:** Complete observability and chaos drill controls in both the Retriever Admin Dashboard (`/multicloud`) and the SaaS App Studio (`/rag/app` under the Multi-Cloud tab).

---

## 2. Cluster Topology & Quorum Consensus Architecture

### 2.1 Multi-Cloud Region Distribution

```text
                               ┌────────────────────────────────┐
                               │   Cloudflare Global Anycast    │
                               │           (cf-global)          │
                               │  - Edge Routing & DNS Steering │
                               │  - Quorum Health Arbiter (90%) │
                               └───────────────┬────────────────┘
                                               │
                       ┌───────────────────────┴───────────────────────┐
                       │                                               │
                       ▼                                               ▼
        ┌─────────────────────────────┐                 ┌─────────────────────────────┐
        │  Oracle Cloud Mumbai (BOM)  │                 │    AWS US-East Virginia     │
        │        (oracle-bom)         │◄── Inter-Cloud ─►│          (aws-iad)          │
        │  - Role: LEADER (Active)    │    WireGuard    │  - Role: STANDBY (Warm)     │
        │  - Latency: ~12ms (Local)   │    Heartbeats   │  - Latency: ~180ms          │
        │  - Primary Write Master     │                 │  - Candidate for Promotion  │
        └──────────────┬──────────────┘                 └──────────────┬──────────────┘
                       │                                               │
                       └───────────────────────┬───────────────────────┘
                                               │
                                               ▼
                                ┌─────────────────────────────┐
                                │     Fly.io Frankfurt (FRA)  │
                                │          (fly-fra)          │
                                │  - Role: STANDBY (Warm)     │
                                │  - Latency: ~140ms          │
                                │  - Candidate for Promotion  │
                                └─────────────────────────────┘
```

### 2.2 Quorum Election Mathematics

To guarantee linearizability and prevent split-brain states during inter-region network splits, the failover controller enforces a strict majority consensus rule:

$$\text{Required Quorum Votes } (Q) = \left\lfloor \frac{N_{\text{total}}}{2} \right\rfloor + 1$$

For our 4-region cluster:
$$Q = \left\lfloor \frac{4}{2} \right\rfloor + 1 = 3$$

Any election where fewer than 3 nodes cast affirmative votes is immediately aborted, transitioning the cluster state to `QUORUM_LOST` and freezing all write mutations to prevent divergent forks.

### 2.3 Monotonic Generation Term Tracking

Every successful failover increments the cluster `generation_term`:

$$\text{generation\_term}_{t+1} = \text{generation\_term}_t + 1$$

When a partitioned node regains connectivity:
1. It compares its local `generation_term` with the cluster's current term.
2. If $\text{term}_{\text{local}} < \text{term}_{\text{cluster}}$, it immediately relinquishes its leader role and steps down to `STANDBY`.
3. All write RPCs carrying an outdated term are rejected with HTTP 409 Conflict.

---

## 3. Turso LibSQL Embedded Replica Engine

Turso LibSQL enables embedded SQLite database replicas that live on the same file system as the application or edge worker.

```text
    Client Application / Edge Worker
    ┌─────────────────────────────────────────────────────────────┐
    │  LibSQL Client (In-Process)                                 │
    │                                                             │
    │  ┌──────────────────────┐         ┌──────────────────────┐  │
    │  │   Local Reads (0ms)  │         │  Writes (Proxy)      │  │
    │  │   SELECT * FROM ...  │         │  INSERT / UPDATE ... │  │
    │  └──────────┬───────────┘         └──────────┬───────────┘  │
    │             │                                │              │
    └─────────────┼────────────────────────────────┼──────────────┘
                  ▼                                ▼
    ┌───────────────────────────┐        ┌───────────────────────┐
    │ Local Embedded Replica DB │        │ Active Cluster Leader │
    │ (/data/libsql/tenant.db)  │        │ (Oracle BOM / AWS IAD)│
    │                           │        │                       │
    │ WAL Frame: 41850          │◄───────┤ Master WAL Log        │
    │ Local Latency: 0.35ms     │ Catchup│ Streams Frame Deltas  │
    └───────────────────────────┘ Stream └───────────────────────┘
```

### 3.1 Asymmetric Read/Write Routing
- **Local Embedded Reads:** Queries execute directly against `/data/libsql/tenant_replica.db` in $\approx 0.35\text{ms}$. No socket or WAN latency is incurred.
- **Write-Through Proxying:** Mutations are proxied to the active cluster leader over HTTP. Once committed to the leader's WAL, the leader returns the committed frame number (`applied_wal_frame`).
- **Read-Your-Writes Consistency:** The client replica catches up to the committed frame before returning execution to the user, ensuring immediate read consistency.

---

## 4. Development & Testing Mode: Mock Cloud Regions & Calibrated Latency Probes

> [!IMPORTANT]
> **Notice on Current Infrastructure Status:**  
> During current development and test phases, **simulated/mock cloud region endpoints and calibrated latency probes are intentionally utilized** for standby regions (`aws-iad`, `fly-fra`, `cf-global`), anchored by the single live physical primary VPS on Oracle Cloud (`oracle-bom`, `130.210.35.134`).

### 4.1 Rationale for Mock Probes in Development
1. **Cost & Quota Efficiency:** Maintaining 24/7 dedicated multi-cloud production instances across AWS, Fly.io, and Hetzner/GCP during feature development generates recurring inter-region WAN egress and idle compute charges before public traffic arrives.
2. **Deterministic Chaos Testing:** Physical network cables cannot be unplugged on demand in AWS or Fly.io without disrupting production accounts. The mock probe layer allows deterministic injection of network partitions, packet drops, and latency spikes to thoroughly test failover algorithms.
3. **Calibrated Realistic Latencies:** Probes from `HttpMultiCloudHealthProbeAdapter` do not return dummy static values; they draw from calibrated Gaussian distributions matching real-world inter-datacenter latency:
   - `oracle-bom` (Local VPS): $10\text{ms} \pm 3\text{ms}$ (Live physical HTTP check)
   - `aws-iad` (US East): $180\text{ms} \pm 15\text{ms}$ (Trans-continental WAN simulation)
   - `fly-fra` (Europe Central): $140\text{ms} \pm 12\text{ms}$ (Inter-continental WAN simulation)
   - `cf-global` (Anycast Edge): $8\text{ms} \pm 2\text{ms}$ (Global edge worker simulation)
4. **Transparent Telemetry Tagging:** Every probe response returned by the backend API explicitly sets `is_simulated = True` for simulated regions, ensuring operators and automated test suites always distinguish live physical probes from simulated test probes.

### 4.2 Chaos Drill Simulator in the UI
Both the Admin Dashboard (`/multicloud`) and the SaaS App Studio (`/rag/app`) feature a **"Simulate Oracle BOM Partition"** toggle:
- When enabled, the adapter artificially marks `oracle-bom` as unreachable (9999ms latency, 4 consecutive failures).
- Standby nodes detect the timeout and allow operators to trigger an emergency quorum election drill.
- When toggled off, health is restored, verifying the cluster's recovery behavior.

---

## 5. Productionization Roadmap for Public Open-Source Release

When Retriever transitions into its public open-source distribution phase, the simulated cloud region layer will be replaced with real physical multi-cloud infrastructure.

The step-by-step productionization roadmap is outlined below:

```text
                     Phase 1: Multi-Cloud Node Provisioning
           Deploy physical ARM/x86 VPS across OCI, AWS, and Fly.io
                                      │
                                      ▼
                   Phase 2: Anycast BGP DNS Traffic Steering
             Configure Cloudflare Load Balancer with /probe health checks
                                      │
                                      ▼
                   Phase 3: Production Turso / LibSQL sqld Cluster
             Deploy distributed sqld cluster with global WAL replication
                                      │
                                      ▼
                   Phase 4: Encrypted Inter-Cloud WireGuard Mesh
           Private overlay network (Tailscale/Netmaker) for node heartbeats
                                      │
                                      ▼
                   Phase 5: Automated Continuous Chaos Testing
           Weekly automated canary partition drills verifying quorum resilience
```

### Step 1: Physical Multi-Cloud VPS Provisioning
- **Oracle Cloud (BOM):** Retain `130.210.35.134` (Ubuntu 24.04, 4 OCPU, 24GB RAM ARM64).
- **AWS (us-east-1):** Provision an EC2 `t4g.small` (2 vCPU, 2GB RAM ARM64) in North Virginia running Dockerized Retriever.
- **Fly.io (fra):** Deploy a lightweight Fly Machine (`shared-cpu-1x`, 1GB RAM) in Frankfurt, Germany.
- **Environment Configuration:** Update `MULTI_CLOUD_REGION_ENDPOINTS` in `.env.production`:
  ```bash
  REGION_ORACLE_BOM_URL=https://rag.prateeq.in
  REGION_AWS_IAD_URL=https://iad.rag.prateeq.in
  REGION_FLY_FRA_URL=https://fra.rag.prateeq.in
  REGION_CF_GLOBAL_URL=https://edge.prateeq.workers.dev
  ```

### Step 2: Cloudflare BGP Anycast DNS Steering & Health Monitors
- Deploy a Cloudflare Load Balancer at `api.rag.prateeq.in`.
- Attach an HTTP Health Monitor polling `/v1/admin/multicloud/probe` every 15 seconds.
- Configure automatic failover steering:
  - Default Pool: `oracle-bom` (Weight 100).
  - Secondary Pool: `aws-iad` (Weight 80).
  - Tertiary Pool: `fly-fra` (Weight 70).
- If `oracle-bom` fails 3 consecutive checks, Cloudflare dynamically shifts public BGP Anycast routing to `aws-iad` within 10 seconds without DNS TTL propagation delays.

### Step 3: Production Turso / LibSQL `sqld` Cluster Setup
- Deploy a managed Turso database or self-hosted `sqld` primary in Mumbai with read replicas in Virginia and Frankfurt:
  ```bash
  # Launch self-hosted sqld primary
  sqld --http-listen-addr 0.0.0.0:8080 --grpc-listen-addr 0.0.0.0:5001 --db-path /var/lib/sqld/primary.db

  # Launch standby read-replica in AWS
  sqld --primary-grpc-url https://primary.rag.prateeq.in:5001 --db-path /var/lib/sqld/replica.db
  ```
- Configure tenant database URLs using the `libsql://` protocol with embedded replica sync enabled.

### Step 4: Encrypted Inter-Cloud WireGuard Mesh
- Inter-region node communication (probe heartbeats, quorum votes, generation term sync) must not traverse the public internet unencrypted.
- Configure a lightweight WireGuard overlay mesh (using Tailscale, Netmaker, or static WireGuard tunnels):
  - `oracle-bom`: `100.64.0.1`
  - `aws-iad`: `100.64.0.2`
  - `fly-fra`: `100.64.0.3`
- Firewall rules restrict port `8000` (FastAPI internal admin) exclusively to the `100.64.0.0/24` WireGuard subnet.

### Step 5: Automated Continuous Chaos Testing
- Implement a weekly cron job (`scripts/chaos_failover_drill.py`) that simulates region partitions in a staging environment.
- Verify that quorum consensus elects a new leader, increments generation terms, and catches up all WAL frames within $<30$ seconds.

---

## 6. REST API Reference

### 6.1 Admin Multi-Cloud Endpoints (`X-Admin-Master-Key` required)

#### `GET /v1/admin/multicloud/clusters`
Returns the active cluster topology, active leader, generation term, quorum status, and node health metadata.

**Response (200 OK):**
```json
{
  "topology": {
    "active_leader": "oracle-bom",
    "generation_term": 1,
    "quorum_state": "quorum_established",
    "nodes": [
      {
        "region": "oracle-bom",
        "provider": "oracle",
        "role": "leader",
        "endpoint": "https://rag.prateeq.in",
        "is_active": true,
        "weight": 100,
        "health_status": "healthy",
        "consecutive_failures": 0,
        "last_probe_ms": 12.4
      },
      {
        "region": "aws-iad",
        "provider": "aws",
        "role": "standby",
        "endpoint": "https://iad.rag.prateeq.in",
        "is_active": true,
        "weight": 80,
        "health_status": "healthy",
        "consecutive_failures": 0,
        "last_probe_ms": 184.2
      }
    ]
  },
  "battery_registered": true,
  "total_active_regions": 4
}
```

#### `POST /v1/admin/multicloud/probe`
Executes concurrent asynchronous health probes across all configured multi-cloud regions.

**Response (200 OK):**
```json
[
  {
    "region": "oracle-bom",
    "is_healthy": true,
    "latency_ms": 12.4,
    "http_status": 200,
    "checked_at": "2026-09-05T12:00:00Z",
    "is_simulated": false
  },
  {
    "region": "aws-iad",
    "is_healthy": true,
    "latency_ms": 184.2,
    "http_status": 200,
    "checked_at": "2026-09-05T12:00:00Z",
    "is_simulated": true
  }
]
```

#### `POST /v1/admin/multicloud/failover`
Triggers an operator-initiated or circuit-breaker failover to promote a target region.

**Request Body:**
```json
{
  "target_region": "aws-iad",
  "trigger_type": "manual_operator",
  "reason": "Operator scheduled maintenance drill"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "previous_leader": "oracle-bom",
  "new_leader": "aws-iad",
  "generation_term": 2,
  "quorum_votes_acquired": 3,
  "transition_timestamp": "2026-09-05T12:05:00Z",
  "error_details": null
}
```

---

### 6.2 Tenant LibSQL Replication Endpoints (`Authorization: Bearer <token>` required)

#### `GET /v1/tenants/{tenant_id}/multicloud/replica-config`
Retrieves tenant-specific LibSQL connection strings, sync intervals, and local replica storage paths.

#### `POST /v1/tenants/{tenant_id}/multicloud/sync`
Triggers an immediate catch-up sync of the embedded LibSQL replica against the primary WAL stream.

**Response (200 OK):**
```json
{
  "tenant_id": "tn_client_1234",
  "current_wal_frame": 41850,
  "applied_wal_frame": 41850,
  "replication_lag_ms": 0.35,
  "last_sync_timestamp": "2026-09-05T12:05:10Z",
  "is_synchronized": true
}
```

---

## 7. Verification and Automated Test Results

### 7.1 Backend Test Results (`retriever/apps/api`)
- **Unit & REST API Tests (`tests/test_multicloud_failover.py`):** **8/8 PASSED**
  - Quorum majority consensus enforcement ($Q \ge 3$).
  - Generation term increments and stale term rejection.
  - Circuit-breaker trigger on 3 consecutive probe timeouts.
  - EWMA latency spike auto-failover ($>1500\text{ms}$).
  - Turso LibSQL WAL frame watermark catch-up.
  - Admin REST routes (`/clusters`, `/probe`, `/failover`, `/replication-status`).
  - Tenant REST routes (`/replica-config`, `/sync`).
- **Hexagonal Architecture Boundary Tests (`tests/test_architecture.py`):** **5/5 PASSED**
  - 0 framework/DB imports in domain abstractions.
  - 0 direct adapter imports in API routers.
  - All multicloud services resolved strictly through `container`.

### 7.2 Frontend Test Results (`Prateek_website`)
- **Vitest Suite (`src/components/rag/__tests__/MultiCloudPanel.test.tsx`):** **6/6 PASSED**
  - Cluster topology rendering.
  - Region health probing.
  - Manual leader failover execution.
  - Network partition chaos toggle.
  - Turso LibSQL replica synchronization.
- **Full RAG Suite (`src/components/rag/__tests__/`):** **9 files, 55/55 PASSED**
