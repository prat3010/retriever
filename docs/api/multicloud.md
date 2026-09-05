---
id: Retriever_API_v1_multicloud
title: "API Specification: Distributed Multi-Cloud Failover & LibSQL Replication (/v1/admin/multicloud, /v1/tenants/{tenantId}/multicloud)"
tier: 4_api_gateway
platform: retriever
tags:
  - api/multicloud
  - failover/quorum
  - database/libsql
  - platform/retriever
blast_radius: CRITICAL
security_auth: ADMIN_KEY_OR_BEARER_JWT
invariants:
  - "Leader failover MUST enforce strict majority quorum consensus (Q = floor(N/2) + 1)."
  - "Stale leaders MUST step down immediately upon detection of higher monotonic generation terms."
  - "LibSQL embedded replicas MUST proxy write operations to the active primary node."
---

# API Specification: Multi-Cloud Failover & Edge LibSQL Replication (`/v1/multicloud`)

#api #multicloud #failover #libsql #quorum #retriever

> **Authoritative REST API specification for active-active multi-cloud cluster topology inspection, mathematical quorum failover simulation, and Turso LibSQL embedded WAL replication (Platform Battery #19).**

---

## 1. Overview & Consensus Architecture

The Multi-Cloud API coordinates high-availability cluster topology across heterogeneous cloud providers:
- **Oracle Cloud Infrastructure (Primary Leader - Mumbai)**
- **AWS us-east-1 (Secondary Standby)**
- **Fly.io Frankfurt (EU Edge Replica)**
- **Cloudflare Edge Workers (Global Query Routing)**

Leader elections require a strict majority quorum consensus ($Q = \lfloor N/2 \rfloor + 1$) to eliminate split-brain states during regional network partitions.

---

## 2. Admin Endpoints

### 2.1 Get Multi-Cloud Topology & Quorum Health
* **Endpoint:** `GET /v1/admin/multicloud/clusters`
* **Auth:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
* **Description:** Retrieves the current cluster topology, active write primary, generation term, and node status list.
* **Response (200 OK):**
```json
{
  "topology": {
    "cluster_name": "retriever-global-mesh",
    "generation_term": 4,
    "primary_region": "oracle_mumbai",
    "quorum_threshold": 3,
    "nodes": [
      {
        "region_id": "oracle_mumbai",
        "provider": "oracle_cloud",
        "is_primary": true,
        "status": "HEALTHY",
        "latency_ms": 12.4,
        "last_probe_at": "2026-09-05T18:00:00Z"
      },
      {
        "region_id": "aws_us_east_1",
        "provider": "aws",
        "is_primary": false,
        "status": "HEALTHY",
        "latency_ms": 142.1,
        "last_probe_at": "2026-09-05T18:00:00Z"
      }
    ]
  },
  "active_battery": {
    "id": "multicloud_failover_libsql",
    "name": "Distributed Multi-Cloud Failover & Edge Turso LibSQL Replication",
    "status": "ACTIVE"
  },
  "probes_summary": {
    "healthy_nodes": 4,
    "total_nodes": 4,
    "quorum_achieved": true
  }
}
```

### 2.2 Trigger Cluster Health Probe
* **Endpoint:** `POST /v1/admin/multicloud/probe`
* **Auth:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
* **Description:** Dispatches asynchronous health and EWMA latency probes to all registered cloud nodes.
* **Response (200 OK):** Array of `RegionHealthProbe` records.

### 2.3 Simulate / Execute Failover
* **Endpoint:** `POST /v1/admin/multicloud/failover/simulate`
* **Auth:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
* **Request Body:**
```json
{
  "target_region": "aws_us_east_1",
  "reason": "Simulated primary outage drill",
  "force_override": false
}
```
* **Response (200 OK):**
```json
{
  "success": true,
  "previous_primary": "oracle_mumbai",
  "new_primary": "aws_us_east_1",
  "new_generation_term": 5,
  "quorum_votes": 3,
  "execution_time_ms": 782,
  "message": "Quorum election successful; primary leadership transferred to aws_us_east_1."
}
```

---

## 3. Tenant Endpoints

### 3.1 Get LibSQL Replica Configuration
* **Endpoint:** `GET /v1/tenants/{tenantId}/multicloud/replica-config`
* **Auth:** `Authorization: Bearer <JWT_OR_TENANT_KEY>`
* **Response (200 OK):** Returns `LibsqlReplicaConfig` with database URL and auth tokens for connecting embedded LibSQL clients.

### 3.2 Get Replication Telemetry & WAL Stats
* **Endpoint:** `GET /v1/tenants/{tenantId}/multicloud/stats`
* **Auth:** `Authorization: Bearer <JWT_OR_TENANT_KEY>`
* **Response (200 OK):**
```json
{
  "tenant_id": "c7a8b9c0-1234-5678-90ab-cdef12345678",
  "current_wal_frame": 18420,
  "synced_wal_frame": 18418,
  "replication_lag_ms": 42.5,
  "read_latency_local_ms": 0.82,
  "write_proxy_latency_ms": 138.4
}
```
