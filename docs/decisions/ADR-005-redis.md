# ADR-005: Use Redis for Multi-Tier Caching & Rate-Limiting

## Status
Accepted

## Context
Retriever requires sub-150ms search query responses. Fetching API credentials, tenant configurations, and active prompts from the primary database on every request adds database load. In addition, duplicate vector generation for identical queries increases LLM costs.

## Problem
We need an in-memory, low-latency database to:
1. Cache hot metadata (tenant configurations, API key hashes) with sub-millisecond read access (L1 Cache).
2. Cache search results based on semantic query vector similarity (L2 Cache).
3. Track rate-limiting counters (sliding windows) for tenant API calls.
4. Support thread-safe transactional updates and TTL expirations.

## Decision
Utilize **Redis** as the unified platform L1/L2 cache and rate-limiting database.

## Alternatives Considered
* **In-Memory Application Cache (e.g. dict cache in Python process):** While extremely fast, process-level caching makes it difficult to scale stateless API nodes horizontally, as caches become out-of-sync.
* **Memcached:** A high-performance in-memory cache, but lacks advanced data structures (hashes, sorted sets) and key eviction hooks, which are required for rate-limiting counters and semantic search caching.

## Consequences
* **Stateless API Scaling:** All serving nodes query a shared Redis cluster, maintaining configuration consistency across replicas.
* **Database Offloading:** Cache hits resolve config lookups in sub-milliseconds, protecting PostgreSQL from query spikes.
* **Semantic Query Savings:** Query matches that exceed the **0.99** similarity threshold resolve from the L2 Redis cache, bypassing vector generation and database search costs.
* **TTL Expirations:** Caches auto-evict expired keys based on TTL configuration policies.
* **Operational Constraint:** Requires configuring eviction policies (e.g., `allkeys-lru`) to prevent Redis Out-Of-Memory (OOM) crashes when cache capacity is exceeded.

## Future Review Criteria
* Monitor Redis hit rates. If the L1 config cache hit rate drops below **90%**, re-evaluate TTL policies.
* Audit L2 semantic cache accuracy to ensure returning cached results does not introduce data drift.
