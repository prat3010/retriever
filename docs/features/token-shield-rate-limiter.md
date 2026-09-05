# Edge AI Token Shield & Redis Sliding-Window Rate Limiter

**Milestone:** M86 (v0.71.0)  
**System Layer:** Traffic Defense & Denial-of-Service Shielding (Platform Battery #11)  
**Architecture:** Upstash Redis Sorted Sets (ZADD/ZREMRANGEBYSCORE) + Local In-Memory LRU Fallback + Tiered Token Quota Costing + RFC 429 Headers  

---

## 1. Executive Summary

Milestone 86 establishes **Platform Battery #11: `token_shield_rate_limiter`**, protecting high-cost LLM and embedding endpoints from automated token drainage, distributed denial-of-service (DDoS) bursts, and infinite client loop cascades.

In an AI cognitive architecture, traditional naive request rate limiting (e.g. "10 requests/min") is fundamentally insufficient:
- A single request to an RFP document ingestion endpoint might burn 80,000 tokens through recursive OCR and embedding, whereas a simple ping burns zero.
- Fixed-window rate limiters permit 2x traffic bursts across window boundaries (e.g. 10 requests at 11:59:59 and 10 requests at 12:00:01).
- External Redis outages can completely blind rate limiters or take down the API.

Platform Battery #11 solves these challenges with a dual-mode sliding-window rate limiter:
1. **True Sliding-Window Arithmetic:** Uses Redis Sorted Sets (`ZSET`) where scores represent millisecond timestamps, eliminating boundary burst anomalies.
2. **Endpoint Weight-Tiered Token Shielding:** Heavy AI endpoints (RFP extraction, Docling OCR, multi-agent consensus) carry proportionally higher token weights than lightweight status lookups.
3. **Local In-Memory LRU Failover:** If Upstash Redis is unreachable or experiences network latency $>250\text{ms}$, the limiter seamlessly falls back to an in-memory thread-safe LRU cache with zero downtime.

---

## 2. Mathematical Algorithm & Redis Sorted Set Mechanics

For each arriving request from key $K$ (derived from client IP or authenticated `tenant_id`):

```text
       Window Start: T - WindowSize (60s)                    Current Time: T
              │                                                     │
              ▼                                                     ▼
     ─────────[─────•──────•──────────•─────────•──────•────────────]───────► Time (ms)
                    t1     t2         t3        t4     t5 (Current Request)
     
     1. ZREMRANGEBYSCORE(K, 0, T - WindowSize)  --> Prunes expired entries
     2. ZCARD(K)                                --> Counts active requests in window
     3. If ZCARD + Weight <= Limit:
            ZADD(K, T, UUID)                    --> Records current timestamp
            Return ALLOWED (200)
        Else:
            Return RATE_LIMITED (429)
```

### RFC 429 Standardized Response Headers
Every response emitted through the limiter includes compliance headers:
- `X-RateLimit-Limit`: Maximum tokens/requests allowed in the rolling window.
- `X-RateLimit-Remaining`: Remaining capacity in the current window.
- `X-RateLimit-Reset`: Milliseconds until the oldest request falls out of the sliding window.
- `Retry-After`: Seconds the client must wait before retrying (on 429 responses).

---

## 3. Tiered Endpoint Configuration

| Endpoint Tier | Window Size | Capacity Limit | Cost Weight | Description |
|:---|:---|:---|:---|:---|
| **RFP & Document OCR** | 60 seconds | 5 requests | 5x | Heavy multimodal Docling parsing & layout extraction |
| **Scoping AI Intent** | 60 seconds | 10 requests | 2x | Multimodal CPQ prompt intent expansion |
| **Copilot Chat & RAG** | 60 seconds | 20 requests | 1x | Streaming vector search & RLM REPL generation |
| **Status & Ping** | 60 seconds | 120 requests | 0.1x | System metrics, health checks, and public analytics |

---

## 4. Implementation Details

- **Adapter:** `apps/api/src/adapters/api/rate_limiter.py`
- **Frontend / Edge Mirror:** `Prateek_website/src/lib/rateLimit.ts`
- **Supported Storage:** Upstash Redis REST / Redis TCP with local in-process `collections.OrderedDict` LRU fallback.
- **Latency Profile:** $\sim 2\text{ms}$ evaluation overhead.
- **Health Check Endpoint:** `GET /v1/telemetry/rate-limit/status`

---

## 5. Non-Negotiable Invariants

1. **Zero Downtime on Redis Outages:** If Redis drops or times out, the local LRU engine takes over within $5\text{ms}$ with an `ALERT` log; requests are never dropped due to infrastructure unavailability.
2. **Sub-2ms Evaluation:** The rate-limiting middleware must evaluate before any database transaction or LLM API call begins.
3. **Atomic Multi-Tenancy:** Keys are prepended with `rl:{tenant_id}:{endpoint_tier}` to prevent cross-tenant quota collisions.
