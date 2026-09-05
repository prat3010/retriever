# Operational Runbook: Sovereign Edge Vector Sync & CRDT SQLite Swarms

**Runbook ID:** RB-OPS-098  
**Audience:** Platform SREs, Edge Infrastructure Engineers, Field Deployment Teams  
**Applies to:** Retriever AI Engine (v0.83.0+, Milestone 98)  
**Platform Battery:** Battery #18 (`edge_vector_sync`)  

---

## 1. System Overview & Architecture

The Sovereign Edge Sync architecture enables remote, air-gapped, or intermittent edge devices (mobile kiosks, local branch servers, embedded gateways) to maintain a complete, queryable vector index locally via SQLite with vector extensions, synchronizing bidirectional changes with the central Oracle VPS pgvector cluster when connectivity is established.

```text
  [ Remote Edge Device ]                                    [ Central Retriever VPS ]
   (Local SQLite + CRDT)                                     (PostgreSQL + pgvector)
             │                                                         │
             │ 1. POST /v1/edge/peers/register                         │
             ├────────────────────────────────────────────────────────►│
             │◄────────────────────────────────────────────────────────┤ (Returns peer_id & token)
             │                                                         │
             │ 2. GET /v1/edge/tenants/{id}/snapshot                   │
             ├────────────────────────────────────────────────────────►│ (Compresses baseline SQLite)
             │◄────────────────────────────────────────────────────────┤
             │ (Loads snapshot into memory / local NVMe)               │
             │                                                         │
             │ 3. (Offline Inference & Local Vector Mutations)         │
             │                                                         │
             │ 4. POST /v1/edge/tenants/{id}/delta (Vector Clock Sync) │
             ├────────────────────────────────────────────────────────►│ (Merge CRDT state)
             │◄────────────────────────────────────────────────────────┤ (Returns central deltas)
```

---

## 2. Health Checks & Verification Commands

### 2.1 Verify Edge Subsystem Battery Health
Confirm that Battery #18 (`edge_vector_sync`) is active and healthy:

```bash
curl -s -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
  https://rag.prateeq.in/v1/admin/edge/health | jq .
```

**Expected Output:**
```json
{
  "status": "healthy",
  "battery_id": "edge_vector_sync",
  "active_peers": 14,
  "pending_snapshot_jobs": 0,
  "avg_delta_latency_ms": 38.2,
  "crdt_clock_skew_max_seconds": 1.4
}
```

### 2.2 Inspect Tenant Edge Sync Status
Query active peer devices and vector clock synchronization metrics for a tenant:

```bash
curl -s -H "Authorization: Bearer $TENANT_API_KEY" \
  https://rag.prateeq.in/v1/edge/tenants/$TENANT_ID/status | jq .
```

---

## 3. Standard Operational Procedures (SOPs)

### SOP-EDGE-01: Provisioning a New Edge Peer Device

1. Register the device via administrative or tenant key:
   ```bash
   curl -X POST "https://rag.prateeq.in/v1/edge/peers/register" \
     -H "Authorization: Bearer $TENANT_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "device_name": "kiosk-berlin-04",
       "hardware_arch": "aarch64",
       "os_platform": "linux",
       "storage_capacity_mb": 64000
     }' | jq .
   ```
2. Store the returned `peer_id` and `peer_auth_token` securely on the edge device in `/etc/retriever/edge_credentials.json` (chmod 600).

### SOP-EDGE-02: Generating & Bootstrapping Baseline SQLite Snapshot

When deploying a new edge node, download the current consolidated SQLite replica snapshot:

```bash
curl -s -H "Authorization: Bearer $PEER_AUTH_TOKEN" \
  "https://rag.prateeq.in/v1/edge/tenants/$TENANT_ID/snapshot?format=zstd" \
  -o /var/lib/retriever/snapshot_baseline.sqlite.zst

# Uncompress snapshot
zstd -d /var/lib/retriever/snapshot_baseline.sqlite.zst -o /var/lib/retriever/edge_replica.sqlite
```

Verify SQLite integrity and table row counts:
```bash
sqlite3 /var/lib/retriever/edge_replica.sqlite "PRAGMA integrity_check;"
sqlite3 /var/lib/retriever/edge_replica.sqlite "SELECT count(*) FROM local_embeddings;"
```

### SOP-EDGE-03: Triggering Bidirectional Delta Sync

Edge devices execute periodic cron jobs (e.g. every 60 seconds) to push local vector changes and receive remote insertions:

```bash
curl -X POST "https://rag.prateeq.in/v1/edge/tenants/$TENANT_ID/delta" \
  -H "Authorization: Bearer $PEER_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "peer_id": "peer_kiosk_berlin_04",
    "vector_clock": { "peer_kiosk_berlin_04": 142, "central_vps": 981 },
    "local_deltas": []
  }' | jq .
```

---

## 4. Incident Triage & Troubleshooting Matrix

| Symptom | Probable Root Cause | Resolution Action |
| :--- | :--- | :--- |
| **`409 Vector Clock Desync Conflict`** | Clock skew exceeds maximum allowed window (>300 seconds) or diverging branches. | Run `SOP-EDGE-02` to re-baseline from a fresh central snapshot; discard local diverged sequence. |
| **`500 SQLite Disk I/O Error on Edge`** | Filesystem full or WAL log locking contention. | Run `sqlite3 /var/lib/retriever/edge_replica.sqlite "PRAGMA wal_checkpoint(TRUNCATE);"` and clean temporary caches. |
| **`403 Peer Revoked`** | Peer device flagged as compromised or inactive >30 days. | Verify device physical integrity, then generate new credentials via `SOP-EDGE-01`. |
| **High Delta Latency (>5000ms)** | Massive batch insertions (>10,000 documents) synced over high-latency 4G link. | Enforce chunked pagination (`limit=500`) in the edge sync daemon configuration. |

---

## 5. Automated Verification & Disaster Recovery

Run the automated edge replication test suite in `apps/api`:

```bash
pytest apps/api/tests/test_edge_sync.py -v
```
