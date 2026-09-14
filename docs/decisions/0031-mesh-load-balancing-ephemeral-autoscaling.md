# 0031. Autonomous Mesh Dynamic Load-Balancing & Ephemeral Enclave Auto-Scaling

Date: 2026-09-15  
Status: Accepted  
Deciders: Prateek Sharma, Platform Architecture Team  
Milestone: Milestone 116 (`v1.6.0-alpha1`)  
Platform Battery: #31 (`mesh_load_balancer`)

---

## Context & Problem Statement

With the introduction of the Distributed Model Context Protocol (MCP) Mesh in Milestone 115 (Battery #30), Retriever clusters and sovereign peer nodes can discover tools and route calls across regional boundaries. However, in production multi-tenant environments under dynamic AI workloads:
1. **Traffic Hotspotting & Stampedes:** Naive routing policies (e.g. static `local_first` or naive `lowest_latency`) direct bursts of traffic to the single fastest node, causing tail latency degradation, queue congestion, and cluster cascading failures.
2. **Static Resource Provisioning:** Running edge enclave nodes continuously wastes compute and cloud resources during off-peak hours, while traffic spikes require rapid horizontal scaling.
3. **Cluster Overload & Cascade Failure:** Without adaptive load-shedding, surges in heavy tool executions (e.g., intensive RLM code execution or vector search) saturate worker thread pools, starving core retrieval operations.
4. **Latency Measurement Noise:** Static ping latency fails to reflect active concurrency bottlenecks or CPU starvation on target nodes.

---

## Decision Drivers

- **Zero-Hotspot Balancing:** Avoid thundering herd problems on low-latency nodes through randomized sampling.
- **Adaptive Moving Decay:** Latency metrics must dynamically incorporate real execution latency rather than static probe intervals.
- **Autonomous Scale-to-Zero Lifecycle:** Spawning ephemeral enclaves under burst load and autonomously reaping them when idle, without manual DevOps intervention.
- **Circuit-Breaker Load-Shedding:** Reject excess tool invocations with clear HTTP 429 semantics when global node capacity exceeds 95% saturation.
- **Pure Hexagonal Architecture:** The load-balancer service must reside in `src/domain/` with zero framework or infrastructure dependencies.

---

## Considered Options

1. **Option 1: Kubernetes Horizontal Pod Autoscaler (HPA) & NGINX Ingress:** Relies on external container orchestration metrics (CPU/RAM). Does not have application-level context of active MCP execution slots, tool queue depth, or per-tenant trust parameters.
2. **Option 2: Centralized Round-Robin Gateway:** Distributes requests evenly across nodes, but ignores heterogeneous node capacities, varying tool execution costs, and real-time latency variations.
3. **Option 3: Power-of-Two-Choices (P2C) with EWMA Latency Decay & Sovereign Ephemeral Enclave Provisioning (Chosen):**
   - Applies the Power-of-Two-Choices (P2C) load balancing algorithm to sample two random candidate nodes and pick the one with lower composite load score.
   - Computes composite load scores combining Exponentially Weighted Moving Average (EWMA) latency ($\alpha = 0.2$), queue depth, and active slot utilization.
   - Embeds autonomous scale-up and scale-to-zero reaping policies through pure domain ports.

---

## Decision Outcome

Chosen Option: **Option 3**.

### Architectural Foundation

1. **Platform Battery #31 Registration:**
   - Cataloged `mesh_load_balancer` under `SYSTEM_EXTENSIBILITY` in `BatteryService`.
   - Health check endpoint: `/v1/mesh/load/metrics`.
   - Default parameters: `scale_up_utilization_pct: 80.0`, `scale_down_idle_seconds: 300.0`, `max_ephemeral_enclaves: 4`, `load_shedding_threshold_pct: 95.0`.

2. **Power-of-Two-Choices (P2C) Algorithm:**
   - For $N \ge 2$ candidate nodes advertising the requested MCP tool, randomly sample 2 nodes ($A, B$).
   - Compute the composite load score:
     $$\text{LoadScore} = \text{EWMA} \times (1 + \text{QueueDepth}) \times \left(1 + \frac{\text{ActiveSlots}}{\text{MaxSlots}}\right) \times \text{StatusPenalty}$$
   - Route to $\arg\min(\text{LoadScore}_A, \text{LoadScore}_B)$. This drastically suppresses stampedes and guarantees balanced distribution without $O(N)$ sorting overhead.

3. **Exponentially Weighted Moving Average (EWMA) Decay:**
   - Execution slots are reserved via `acquire_slot(node_id)` prior to dispatch.
   - In a `finally` block upon completion, `release_slot(node_id, elapsed_ms)` updates EWMA with decay factor $\alpha = 0.2$:
     $$\text{EWMA}_t = \alpha \cdot \text{SampleLatency} + (1 - \alpha) \cdot \text{EWMA}_{t-1}$$

4. **Autonomous Autoscaling & Scale-to-Zero Reaping:**
   - `evaluate_autoscaling(cluster_id)` inspects cluster utilization.
   - **Scale-Up:** Triggered when cluster utilization $\ge 80\%$, queue depth $\ge 10$, or average EWMA $\ge 250$ms (up to `max_ephemeral_enclaves`).
   - **Scale-to-Zero Reaping:** Ephemeral enclaves with 0 active execution slots idle for $\ge 300$ seconds are autonomously terminated and unregistered from the mesh catalog.
   - **Load Shedding:** If all candidate nodes exceed `load_shedding_threshold_pct` (95%), `MeshLoadSheddingError` is raised with HTTP 429 Too Many Requests.

---

## Consequences

### Positive
- **Zero Herd Cascades:** P2C prevents traffic stampedes during sudden traffic bursts.
- **Resource Elasticity:** Edge enclaves scale out on demand and scale down to zero when idle.
- **Fail-Fast Protection:** Saturated nodes shed load gracefully rather than entering memory starvation.
- **Observability:** Complete audit ledger of all scale-up, scale-down, and shed-load events.

### Negative / Trade-offs
- Ephemeral enclaves require warm-up time upon initial spawn.
- Cluster nodes must accurately report heartbeat telemetry or participate in slot tracking.
