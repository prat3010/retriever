---
id: DeepDive_Caching_Performance_Redis
title: "Infrastructure Deep-Dive: Multi-Tier Caching, Redis L2 Semantic Cache & Rate Limiting"
tier: 7_async_infrastructure
platform: retriever
tags:
  - infra/caching
  - redis
  - semantic-cache
  - rate-limiting
  - platform/retriever
blast_radius: HIGH
invariants:
  - "L1 Config Cache TTL MUST not exceed 300 seconds."
  - "L2 Semantic Similarity Cache hit threshold MUST be cosine similarity >= 0.94."
---

# Infrastructure Deep-Dive: Multi-Tier Caching, Redis L2 Semantic Cache & Rate Limiting

#infra #caching #redis #semanticcache #ratelimiting #latency #retriever

> **Technical architecture, cache hierarchies, and sliding-window rate limiters in Retriever.**

---

## 1. Multi-Tier Cache Hierarchy

Retriever minimizes generative model invocation costs and eliminates repetitive database queries via a 3-tier caching stack:

```mermaid
flowchart TD
    Req[Incoming User Request] --> L1{L1 In-Memory / Local Cache}
    L1 -->|Hit (<1ms)| RetL1[Tenant Config & Route Metadata]
    L1 -->|Miss| L2{L2 Redis Semantic Cache}
    
    L2 -->|Vector Sim >= 0.94 (<10ms)| RetL2[⚡ Return Cached Stream]
    L2 -->|Miss| DB[PostgreSQL Query / LLM Generation]
    
    DB --> StoreL2[Save to L2 with 24h TTL]
    StoreL2 --> RetFinal[Stream Response to Client]
```

---

## 2. Sliding-Window Token Bucket Rate Limiter

Enforces granular rate limits per API key / tenant via Redis Lua scripts:

| Plan Tier | Max Requests / min | Max Burst | Max Concurrent SSE Streams |
|:---|:---:|:---:|:---:|
| **Starter** | 30 | 10 | 2 |
| **Pro** | 120 | 30 | 10 |
| **Enterprise** | 600 | 150 | 50 |

---

## 🔗 Related Architecture & Cross-References
- [Database Schemas & Persistence](database_and_schemas.md)
- [Async Workers & Celery Queues](async_workers_and_queues.md)
