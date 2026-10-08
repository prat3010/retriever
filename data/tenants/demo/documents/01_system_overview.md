# Acme Systems — Architecture & System Overview

## 1. Platform Mission
Acme Systems builds modern, resilient distributed infrastructure designed for high throughput, zero-downtime deployments, and real-time event streaming.

## 2. Core Architectural Pillars
- **Hexagonal Architecture (Ports and Adapters)**: The domain layer remains completely decoupled from external protocols, databases, and third-party frameworks.
- **Strict Multi-Tenancy**: Data isolation is enforced at the database level using PostgreSQL Row-Level Security (RLS). Cross-tenant queries are prevented by session variable enforcement (`SET LOCAL app.current_tenant = ...`).
- **Hybrid Retrieval**: Combines HNSW vector search (using cosine distance) with BM25 full-text keyword indexing and Reciprocal Rank Fusion (RRF) for sub-50ms context retrieval.
- **Asynchronous Task Processing**: Heavy compute tasks such as document OCR, embedding synthesis, and batch migrations are executed via background worker pools backed by Redis and Celery.

## 3. SLA & Performance Targets
- **P95 Retrieval Latency**: < 45ms across collections of up to 10M embeddings.
- **Availability Target**: 99.95% uptime with multi-region database replicas.
- **Failover Recovery**: Automated active-passive failover within 30 seconds.
