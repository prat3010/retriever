# Operational Runbook: Geo-Distributed Edge Routing & Multi-Region Read-Replicas (Milestone 89)

**Document Status:** Production-Ready  
**Milestone:** 89 (v0.74.0)  
**Target Audience:** SREs, DevOps Engineers, Enterprise Architects & Platform Administrators  

---

## 1. Executive Overview & Physical Latency Math

In a centralized global architecture, having a single database cluster forces international users to pay a steep network round-trip tax governed by the speed of light in fiber optic cables:

```text
Trans-Atlantic / Trans-Pacific Route        Physical Distance        Round-Trip Time (RTT)
────────────────────────────────────        ─────────────────        ─────────────────────
New York / California  ──>  Mumbai / Singapore   ~13,000 km                ~210 ms - 250 ms
London / Frankfurt     ──>  Mumbai / Singapore    ~7,000 km                ~140 ms - 170 ms
Singapore / Tokyo      ──>  Mumbai               ~4,000 km                 ~40 ms - 60 ms
Local (Same Region)    ──>  Local Data Center        <50 km                 ~12 ms - 25 ms
```

For AI search applications, waiting **200ms+ just for network transport** before vector embedding and LLM token generation begins severely degrades real-time streaming responsiveness.

**Milestone 89** solves this by deploying a **CQRS (Command Query Responsibility Segregation) Geo-Distributed Edge Routing architecture** that routes read queries to localized database replicas while strictly preserving transactional writes on the Primary Master.

---

## 2. Architectural Blueprint & CQRS Guarantees

```text
                     [Global Client Traffic]
                                │
                                ▼
                   ┌───────────────────────────┐
                   │   Geo-IP Edge Router      │
                   │  (Vercel / Cloudflare IP) │
                   └─────────────┬─────────────┘
                                 │
             ┌───────────────────┼───────────────────┐
             │                   │                   │
    Americas (US/CA/BR)   Europe/ME (GB/DE/AE)   APAC (IN/SG/JP)
             │                   │                   │
             ▼                   ▼                   ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │  us-east Edge   │ │ eu-central Edge │ │  ap-south Hub   │
    │  Read-Replica   │ │  Read-Replica   │ │ (Primary Master)│
    │   (~18ms RTT)   │ │   (~22ms RTT)   │ │   (~15ms RTT)   │
    └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
             │ Reads             │ Reads             │ Reads & All WRITES
             └───────────────────┼───────────────────┘
                                 │
                     (WAL Replication Stream)
                                 ▼
                     ┌───────────────────────┐
                     │ PostgreSQL / pgvector │
                     │ Primary Master Engine │
                     └───────────────────────┘
```

### Strict Invariants:
1. **Mutations (Writes) are Single-Leader:** Document ingestion, chunk deletions, API key issuances, user auth, and SOW escrow freezes **ALWAYS** execute against the Primary Master (`PRIMARY_REGION="ap-south"`). Replicas are never subject to write split-brain.
2. **Lookups (Reads) are Multi-Region:** Vector similarity searches (`pgvector` cosine similarity), hybrid BM25 searches, semantic cache reads, and SLA metrics are routed to the caller's nearest regional read-replica.
3. **Zero-Config Resilient Fallback ($0 Budget Friendly):** If a regional replica URL is omitted, offline, or experiencing network degradation, traffic instantly and automatically falls back to the Primary Master without dropping queries or throwing HTTP 500 errors.

---

## 3. Geo-IP Continental Mapping

Retriever detects caller geography via standard proxy edge headers:
- `x-vercel-ip-country` (Populated automatically by Vercel edge proxy)
- `cf-ipcountry` (Populated automatically by Cloudflare Workers/CDN)
- `x-country-code` (Manual caller override header)

### Routing Matrix:

| Continent | ISO-3166-1 Country Codes | Target Node | Primary RTT | Edge Replica RTT | Latency Improvement |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Americas** | `US`, `CA`, `MX`, `BR`, `AR`, `CL`, `CO`, `PE`, `VE`... | `us-east` | ~215 ms | **~18 ms** | **⚡ -91.6% Faster** |
| **Europe & ME** | `GB`, `DE`, `FR`, `IT`, `ES`, `NL`, `SE`, `CH`, `AE`, `IL`... | `eu-central` | ~158 ms | **~22 ms** | **⚡ -86.1% Faster** |
| **Asia-Pacific** | `IN`, `SG`, `JP`, `AU`, `NZ`, `KR`, `ID`, `MY`, `TH`, `VN`... | `ap-south` | ~15 ms | **~15 ms** | Local Master |
| **Unknown / Other** | Unresolved / default traffic | `ap-south` | ~15 ms | ~15 ms | Primary Fallback |

---

## 4. Configuration & Environment Setup

Configure regional endpoints in your environment file (`.env` or deployment secret store):

```bash
# ==============================================================================
# MULTI-REGION READ-REPLICAS & EDGE ROUTING (M89)
# ==============================================================================

# Primary Master region (default: "ap-south" for Mumbai/Singapore Hub)
PRIMARY_REGION="ap-south"

# Primary Master Database URL (Handles all Writes and APAC reads)
DATABASE_URL="postgresql+asyncpg://postgres:password@primary-db.internal:5432/retriever_db"

# Optional Regional Read-Replicas (Leave commented or empty for single-node mode)
# REPLICA_US_EAST_DATABASE_URL="postgresql+asyncpg://postgres:password@us-east-replica.internal:5432/retriever_db"
# REPLICA_EU_CENTRAL_DATABASE_URL="postgresql+asyncpg://postgres:password@eu-central-replica.internal:5432/retriever_db"
# REPLICA_AP_SOUTH_DATABASE_URL=""
```

> [!TIP]
> **Single-Node / Development Mode ($0 Cost):**  
> If you leave `REPLICA_US_EAST_DATABASE_URL` and `REPLICA_EU_CENTRAL_DATABASE_URL` commented out, Retriever operates in **Zero-Config Primary Fallback Mode**. All operations run against `DATABASE_URL` without any error warnings or cloud infrastructure costs.

---

## 5. How to Provision Regional Read-Replicas

### A. Managed Cloud Providers (Supabase / Neon)
1. In the cloud dashboard, navigate to **Settings** $\rightarrow$ **Database** $\rightarrow$ **Read Replicas**.
2. Click **Add Read Replica** and select:
   - Region 1: `US East (N. Virginia)`
   - Region 2: `Europe Central (Frankfurt)`
3. Copy the pooled connection string (port `5432` or transaction pooler port `6543`) and assign to `REPLICA_US_EAST_DATABASE_URL` and `REPLICA_EU_CENTRAL_DATABASE_URL`.

### B. Self-Hosted PostgreSQL (Physical Streaming Replication)
1. On the replica server, set `hot_standby = on` in `postgresql.conf`.
2. Configure `pg_basebackup` pointing to the primary master.
3. Configure `standby.signal` and `primary_conninfo` pointing to `ap-south` master.

---

## 6. SRE & Administrator Observability REST APIs

### 1. Inspect Cluster Topology & Health
```bash
curl -X GET "https://rag.prateeq.in/v1/admin/platform/regions" \
  -H "X-Admin-Key: <ADMIN_MASTER_KEY>"
```
**Sample Response:**
```json
{
  "primary_region": "ap-south",
  "total_regions": 3,
  "configured_replicas": 2,
  "active_routing_mode": "Geo-IP Adaptive Dynamic Routing",
  "regions": [
    {
      "region_code": "ap-south",
      "region_name": "Asia-Pacific Hub",
      "city": "Mumbai / Singapore",
      "is_primary": true,
      "is_configured": true,
      "endpoint_display": "rag.prateeq.in (Primary Master)",
      "status": "healthy",
      "latency_ms": 14.5
    },
    {
      "region_code": "us-east",
      "region_name": "Americas Edge",
      "city": "N. Virginia / New York",
      "is_primary": false,
      "is_configured": true,
      "endpoint_display": "us-east.rag.prateeq.in",
      "status": "healthy",
      "latency_ms": 18.2
    },
    {
      "region_code": "eu-central",
      "region_name": "Europe & ME Edge",
      "city": "Frankfurt / London",
      "is_primary": false,
      "is_configured": false,
      "endpoint_display": "Fallback to Primary Master",
      "status": "fallback_primary",
      "latency_ms": 158.0
    }
  ]
}
```

### 2. Trigger Active RTT Latency Probe
```bash
curl -X POST "https://rag.prateeq.in/v1/admin/platform/regions/probe" \
  -H "X-Admin-Key: <ADMIN_MASTER_KEY>"
```

### 3. Simulate Geo-IP Routing for Any Country
```bash
curl -X GET "https://rag.prateeq.in/v1/admin/platform/regions/preview?country=US" \
  -H "X-Admin-Key: <ADMIN_MASTER_KEY>"
```
**Sample Response:**
```json
{
  "client_country": "US",
  "detected_continent": "Americas",
  "selected_region": "us-east",
  "target_endpoint": "https://us-east.rag.prateeq.in",
  "is_fallback": false,
  "estimated_primary_latency_ms": 215.0,
  "estimated_replica_latency_ms": 18.0,
  "estimated_reduction_pct": 91.6,
  "routing_reason": "Optimally routed to local Americas edge replica (us-east)."
}
```

---

## 7. Web Admin Console UI

Administrators can inspect and test multi-region edge routing directly in the web dashboard at **`/system-data`**:
- **3-Region Status Cards:** Shows live RTT latency, regional role, and endpoint status.
- **Geo-IP Routing Simulator:** Click country buttons (`US`, `GB`, `DE`, `IN`, `JP`, `AU`, `BR`) to see instant simulated routing decisions, roundtrip times, and latency reduction badges.
- **Probe Regional Latency Button:** Executes an on-demand ping across all nodes in 1 click.
