# Operational Runbook: Multi-Cloud LibSQL Replication & Disaster Recovery Failover

**Runbook ID:** RB-OPS-099  
**Audience:** Principal Site Reliability Engineers, Cloud Operations Directors  
**Applies to:** Retriever AI Engine (v0.84.0+, Milestone 99)  
**Platform Battery:** Battery #19 (`multicloud_failover`)  

---

## 1. Architecture & Multi-Cloud Topology

Retriever's zero-downtime database high availability spans three distinct cloud providers using distributed LibSQL / sqld replication:
- **Primary Region (Active Write):** Oracle Cloud VPS (`eu-frankfurt-1` / `130.210.35.134`)
- **Secondary Replica (Hot Standby):** Fly.io Managed Edge Cluster (`ams` / Amsterdam)
- **Disaster Recovery Replica (Cold Standby):** AWS EC2 (`us-east-1` / N. Virginia)

```text
               ┌────────────────────────────────────────────────────────┐
               │         Anycast Edge Ingress (DNS Traffic Router)      │
               └───────────┬────────────────┬───────────────────────────┘
                           │                │ (Upon Failover)
              Primary Path │                │
                           ▼                ▼
     ┌───────────────────────────┐    ┌───────────────────────────┐
     │ Oracle Cloud VPS (Primary)│    │ Fly.io Hot Standby Replica│
     │ • LibSQL Leader Node      │    │ • Embedded Replica Stream │
     │ • FastAPI Cognitive Core  │    │ • Read-Only Query Traffic │
     └─────────────┬─────────────┘    └─────────────▲─────────────┘
                   │                                │
                   │ Raft Replication Log Stream    │
                   └────────────────────────────────┘
```

---

## 2. Health Monitoring & Observability Commands

### 2.1 Check Cluster Status & Active Leader
Query the cluster state, active primary node, and cross-region replication lag:

```bash
curl -s -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
  https://rag.prateeq.in/v1/admin/multicloud/status | jq .
```

**Expected Output (Normal Operations):**
```json
{
  "active_primary_region": "oracle-fra-1",
  "raft_leader_node": "node_oracle_01",
  "replication_lag_ms": 14.8,
  "nodes": [
    { "node_id": "node_oracle_01", "region": "oracle-fra-1", "role": "LEADER", "status": "HEALTHY", "ping_ms": 0.0 },
    { "node_id": "node_fly_01", "region": "fly-ams-1", "role": "FOLLOWER", "status": "HEALTHY", "ping_ms": 18.2 },
    { "node_id": "node_aws_01", "region": "aws-useast-1", "role": "FOLLOWER", "status": "HEALTHY", "ping_ms": 84.1 }
  ],
  "auto_failover_enabled": true
}
```

### 2.2 Probe Inter-Region Latency
Trigger a synthetic latency and read-after-write consistency probe:

```bash
curl -X POST "https://rag.prateeq.in/v1/admin/multicloud/probe" \
  -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" | jq .
```

---

## 3. Standard Operational Procedures (SOPs)

### SOP-CLOUD-01: Executing Planned Maintenance Failover

When performing OS kernel upgrades or routine maintenance on the primary Oracle Cloud VPS:

1. Initiate controlled promotion of the Fly.io replica:
   ```bash
   curl -X POST "https://rag.prateeq.in/v1/admin/multicloud/failover" \
     -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "target_region": "fly-ams-1",
       "reason": "Planned Oracle Cloud kernel reboot",
       "drain_timeout_seconds": 15
     }' | jq .
   ```
2. Verify that `active_primary_region` transitions to `fly-ams-1` with 0 replication transaction loss.
3. Perform maintenance on the Oracle VPS.
4. Once maintenance is complete, re-attach Oracle as a follower, wait for replication lag to reach `< 20ms`, and fail back:
   ```bash
   curl -X POST "https://rag.prateeq.in/v1/admin/multicloud/failover" \
     -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
     -H "Content-Type: application/json" \
     -d '{ "target_region": "oracle-fra-1", "reason": "Restoring primary after maintenance" }' | jq .
   ```

### SOP-CLOUD-02: Handling Emergency Unplanned Leader Outage

If the primary VPS becomes unreachable (hardware failure, datacenter network cut):

1. Confirm health probe failures:
   ```bash
   curl -I --connect-timeout 3 https://130.210.35.134:8000/v1/health
   ```
2. If unreachable, issue forceful leader promotion on the standby node:
   ```bash
   curl -X POST "https://api.fly.rag.prateeq.in/v1/admin/multicloud/failover" \
     -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "target_region": "fly-ams-1",
       "force_unclean_promotion": true,
       "reason": "Unplanned Oracle VPS power outage"
     }' | jq .
   ```
3. Update DNS CNAME record for `rag.prateeq.in` to point to `api.fly.rag.prateeq.in`.

---

## 4. Incident Triage & Troubleshooting Matrix

| Incident Symptom | Root Cause | Immediate Remediation |
| :--- | :--- | :--- |
| **Replication Lag > 5000ms** | Transatlantic network congestion or heavy batch ingestion. | Inspect write queue; throttle non-critical document ingestion jobs until lag drops under 500ms. |
| **Raft Quorum Split (No Leader)** | Network partition isolating 2 out of 3 nodes. | SSH into surviving majority nodes and manually designate leader via `sqld consensus force-leader`. |
| **`409 Stale Replica Read`** | Client querying read replica before recent write transaction replicated. | Configure `wal_read_consistency=strong` in tenant client connection options. |

---

## 5. Automated Verification

Verify multi-cloud failover logic via automated Pytest suites:

```bash
pytest apps/api/tests/test_multicloud_failover.py -v
```
