# Autonomous Mesh Dynamic Load-Balancing & Ephemeral Enclave Auto-Scaling

**Milestone:** M116 (`v1.6.0-alpha1`)  
**System Layer:** Distributed Mesh & Elastic Sovereign Compute  
**Platform Battery:** #31 (`mesh_load_balancer`)  
**Architecture:** Power-of-Two-Choices (P2C) + EWMA Latency Decay ($\alpha = 0.2$) + Concurrency Slot Reservation + Scale-to-Zero Sovereign Enclave Provisioning + Hard 95% Circuit-Breaker Load-Shedding

---

## 1. Overview

Milestone 116 delivers **Platform Battery #31 (`mesh_load_balancer`)**, introducing intelligent load balancing, dynamic concurrency reservation, and autonomous scale-to-zero enclave provisioning to the Distributed MCP Mesh.

Prior to M116, MCP tool calls were routed using static policies (`local_first`, `lowest_latency`), which resulted in traffic stampedes on low-latency nodes and static cloud resource consumption. M116 eliminates these bottlenecks with:
- **Power-of-Two-Choices (P2C):** Evaluates two random candidate nodes and selects the one with the minimal composite load score.
- **EWMA Latency Decay ($\alpha = 0.2$):** Replaces static ping intervals with real execution latency decay.
- **Dynamic Slot Reservation:** Atomic reservation and release of execution slots with queue depth tracking.
- **Autonomous Autoscaling & Scale-to-Zero Reaping:** Automatically scales out ephemeral enclaves under burst load and reaps idle enclaves after 300s of inactivity.
- **Circuit-Breaker Load-Shedding:** Emits HTTP 429 Too Many Requests when all candidate nodes exceed 95% slot saturation.

---

## 2. API Endpoints Reference

| Endpoint | Method | Purpose |
|:---|:---:|:---|
| `/v1/mesh/load/metrics` | `GET` | Battery #31 health check, cluster-wide slot saturation, EWMA latency, and node breakdown |
| `/v1/mesh/load/autoscaling/events` | `GET` | Retrieve audit ledger of recent autoscaling, rebalancing, and load-shedding events |
| `/v1/mesh/load/autoscaling/policy` | `POST` | Update autoscaling thresholds (utilization, queue depth, scale-down timeout) |
| `/v1/mesh/load/heartbeat-telemetry` | `POST` | Ingest node capacity metrics (CPU %, memory %, active slots, EWMA latency) |
| `/v1/mesh/load/scale-down/reap` | `POST` | Trigger autonomous evaluation of cluster pressure and reap idle ephemeral enclaves |
| `/v1/mesh/tools/execute?policy=load_balanced_ewma` | `POST` | Execute tool invocation routed via P2C EWMA load balancing |

---

## 3. Mathematical Foundations

### 3.1 Composite Load Score

For candidate node $i$, the composite load score combines EWMA latency, queue depth, slot saturation, and node health status:

$$\text{LoadScore}_i = \text{EWMA}_i \times (1 + \text{QueueDepth}_i) \times \left(1 + \frac{\text{ActiveSlots}_i}{\max(1, \text{MaxSlots}_i)}\right) \times \text{StatusPenalty}_i$$

where:
- $\text{StatusPenalty} = 1.0$ if $\text{ONLINE}$, else $10.0$.

### 3.2 Power-of-Two-Choices (P2C)

Given a set of candidate nodes $C$ advertising tool $T$ ($|C| \ge 2$):
1. Sample two distinct nodes uniformly at random: $A, B \sim C$.
2. Compute $\text{LoadScore}_A$ and $\text{LoadScore}_B$.
3. Route to $\arg\min(\text{LoadScore}_A, \text{LoadScore}_B)$.

### 3.3 Exponentially Weighted Moving Average (EWMA) Decay

Upon completion of tool execution with observed latency $L_{\text{sample}}$:

$$\text{EWMA}_t = \alpha \cdot L_{\text{sample}} + (1 - \alpha) \cdot \text{EWMA}_{t-1}$$

with default smoothing factor $\alpha = 0.2$.

---

## 4. Autoscaling & Scale-to-Zero State Machine

```
      [Burst Traffic / High Latency]
                 │
                 ▼
     ┌────────────────────────┐
     │  Utilization ≥ 80%     │
     │  Queue Depth ≥ 10      │ ─── Trigger SCALE_UP ───► Provision Ephemeral Enclave
     │  EWMA Latency ≥ 250ms  │
     └────────────────────────┘
                 │
                 │ Normal Traffic (Slots Available)
                 ▼
     ┌────────────────────────┐
     │   Active Slots == 0    │
     │   Idle Time ≥ 300s     │ ─── Trigger SCALE_DOWN ──► Reap Enclave to Zero
     └────────────────────────┘
                 │
                 │ Saturated Cluster (All Nodes ≥ 95%)
                 ▼
     ┌────────────────────────┐
     │   SHED_LOAD Event      │ ─── HTTP 429 Too Many Requests
     └────────────────────────┘
```

---

## 5. Client SDK Integration

### TypeScript (`@prat3010/retriever-client`)

```typescript
import { RetrieverClient } from "@prat3010/retriever-client";

const client = new RetrieverClient({ apiKey: "rt_live_xxx", tenantId: "tn_prod_01" });

// 1. Inspect cluster capacity metrics
const load = await client.getMeshLoadMetrics();
console.log(`Cluster Saturation: ${load.clusters["cluster-primary"].utilization_pct}%`);

// 2. Dispatch tool via Load-Balanced EWMA
const result = await client.executeMeshTool(
  "hybrid_search",
  { query: "Q3 financial compliance audit" },
  "cluster_primary",
  "load_balanced_ewma"
);

// 3. Inspect autoscaling event ledger
const events = await client.getAutoscalingEvents(20);
```

### Python (`retriever-python`)

```python
from retriever import RetrieverClient

client = RetrieverClient(api_key="rt_live_xxx", tenant_id="tn_prod_01")

# 1. Update cluster autoscaling policy
client.update_autoscaling_policy({
    "scale_up_utilization_pct": 75.0,
    "scale_down_idle_seconds": 180.0,
    "max_ephemeral_enclaves": 6,
})

# 2. Trigger idle enclave reaping
reaped_events = client.reap_idle_enclaves("cluster-primary")
print(f"Reaped {len(reaped_events)} idle enclaves.")
```
