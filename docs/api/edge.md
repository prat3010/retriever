---
id: Retriever_API_v1_edge
title: "API Specification: Sovereign Edge SQLite & Vector Sync (/v1/admin/edge, /v1/tenants/{tenantId}/edge)"
tier: 4_api_gateway
platform: retriever
tags:
  - api/edge
  - edge/sync
  - edge/sqlite
  - platform/retriever
blast_radius: HIGH
security_auth: ADMIN_KEY_OR_BEARER_JWT
invariants:
  - "Edge node registration and sync checkpoints MUST be strictly scoped by tenant_id."
  - "Differential pull requests MUST only return chunks with sequence_num strictly greater than since_sequence."
  - "Offline mutation reconciliation MUST preserve Lamport logical timestamps for Last-Write-Wins conflict resolution."
---

# API Specification: Sovereign Edge SQLite & Vector Synchronization (`/v1/edge`)

#api #edge #sync #sqlite #vector #offline #retriever

> **Authoritative REST API specification for Sovereign Edge Node registration, cryptographic sequence delta synchronization, offline mutation reconciliation, and standalone SQLite bundle exports (Platform Battery #18).**

---

## 1. Overview & Sync Topology

The Edge API facilitates bi-directional synchronization between the centralized PostgreSQL pgvector cluster and distributed edge SQLite instances running on air-gapped laptops, field devices, and embedded micro-servers.

```text
  [ Sovereign Edge Node ]                                [ Retriever Cloud API ]
            │                                                      │
            │ 1. POST /v1/tenants/{id}/edge/nodes/register         │
            ├─────────────────────────────────────────────────────►│ (Record Node & Watermark)
            │                                                      │
            │ 2. POST /v1/tenants/{id}/edge/sync/pull              │
            │    { "since_sequence": 1420 }                        │
            ├─────────────────────────────────────────────────────►│
            │◄─────────────────────────────────────────────────────┤
            │    { "chunks": [...], "latest_sequence": 1580,       │
            │      "sha256_hash": "..." }                          │
            │                                                      │
            │ 3. (Offline Operation - Local Mutations Queued)      │
            │                                                      │
            │ 4. POST /v1/tenants/{id}/edge/sync/push              │
            │    { "mutations": [ { "lamport_ts": 105, ... } ] }   │
            ├─────────────────────────────────────────────────────►│ (Reconcile via LWW)
```

---

## 2. Admin Endpoints

### 2.1 Get Edge System Overview
* **Endpoint:** `GET /v1/admin/edge/overview`
* **Auth:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
* **Description:** Retrieves system-wide telemetry across all registered edge nodes, online/offline status counts, hardware platforms, and execution tiers.
* **Response (200 OK):**
```json
{
  "total_nodes": 12,
  "online_nodes": 9,
  "offline_nodes": 3,
  "total_checkpoints": 450,
  "platforms": {
    "darwin_arm64": 5,
    "linux_x86_64": 7
  },
  "tiers": {
    "hybrid_cache": 8,
    "sovereign_full": 4
  },
  "nodes": [
    {
      "node_id": "field-laptop-alpha",
      "tenant_id": "00000000-0000-0000-0000-000000000001",
      "device_name": "Field Engineering Unit A",
      "platform": "darwin_arm64",
      "last_synced_seq": 1580,
      "last_heartbeat_at": "2026-09-05T18:00:00Z",
      "status": "online",
      "meta_data": {}
    }
  ]
}
```

---

## 3. Tenant Endpoints

### 3.1 List Tenant Edge Nodes
* **Endpoint:** `GET /v1/tenants/{tenantId}/edge/nodes`
* **Auth:** `Authorization: Bearer <JWT_OR_TENANT_KEY>`
* **Response (200 OK):** Array of `EdgeNodeMetadata` objects.

### 3.2 Register Edge Node / Heartbeat
* **Endpoint:** `POST /v1/tenants/{tenantId}/edge/nodes/register`
* **Auth:** `Authorization: Bearer <JWT_OR_TENANT_KEY>`
* **Request Body:**
```json
{
  "node_id": "node_field_unit_01",
  "device_name": "Offshore Diagnostic Terminal",
  "platform": "linux_x86_64",
  "tier": "hybrid_cache",
  "client_version": "0.83.0",
  "hardware_specs": {
    "cpu_cores": 4,
    "ram_mb": 8192,
    "storage_available_mb": 25600
  }
}
```
* **Response (200 OK):** Returns confirmed `EdgeNodeMetadata`.

### 3.3 Pull Differential Delta
* **Endpoint:** `POST /v1/tenants/{tenantId}/edge/sync/pull`
* **Auth:** `Authorization: Bearer <JWT_OR_TENANT_KEY>`
* **Request Body:**
```json
{
  "node_id": "node_field_unit_01",
  "since_sequence": 1420,
  "batch_size": 100
}
```
* **Response (200 OK):**
```json
{
  "tenant_id": "c7a8b9c0-1234-5678-90ab-cdef12345678",
  "since_sequence": 1420,
  "to_sequence": 1580,
  "delta_chunks": [
    {
      "chunk_id": "d1e2f3a4-b5c6-7890-1234-567890abcdef",
      "sequence_num": 1421,
      "content": "Zero-trust micro-enclave cryptographic parameters...",
      "embedding_blob": "base64_encoded_float32_bytes...",
      "meta_data": { "category": "security" },
      "is_deleted": false
    }
  ],
  "sha256_checksum": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
}
```

### 3.4 Push Offline Mutations
* **Endpoint:** `POST /v1/tenants/{tenantId}/edge/sync/push`
* **Auth:** `Authorization: Bearer <JWT_OR_TENANT_KEY>`
* **Request Body:**
```json
{
  "node_id": "node_field_unit_01",
  "mutations": [
    {
      "mutation_id": "mut_001",
      "entity_type": "chunk_feedback",
      "entity_id": "d1e2f3a4-b5c6-7890-1234-567890abcdef",
      "operation": "update",
      "lamport_timestamp": 105,
      "payload": { "rating": 1, "comment": "Verified in field inspection" }
    }
  ]
}
```
* **Response (200 OK):** Returns `EdgeSyncConflictResolution` detailing accepted vs. superseded mutations.

### 3.5 Download Standalone SQLite Bundle
* **Endpoint:** `GET /v1/tenants/{tenantId}/edge/bundle`
* **Auth:** `Authorization: Bearer <JWT_OR_TENANT_KEY>`
* **Response (200 OK):** Returns binary stream with header `Content-Disposition: attachment; filename="tenant_{id}_edge.sqlite"`.
