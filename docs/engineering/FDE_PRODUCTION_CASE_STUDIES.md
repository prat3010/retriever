# Forward Deployed Engineering (FDE) — Production Case Studies

This document provides technical deep-dives into mission-critical architecture decisions, trade-offs, and failure modes engineered across the **Retriever** cognitive platform.

---

## Case Study 1: Zero-Trust Multi-Tenancy & Defense-in-Depth RLS Isolation

### 1. The Challenge
Multi-tenant AI and retrieval platforms frequently suffer from data leakage between tenants due to application-level query bugs (e.g., forgetting a `WHERE tenant_id = :id` clause in a complex JOIN). In enterprise environments handling proprietary documentation, legal briefs, and client code, software-level filtering alone is unacceptable.

### 2. Architectural Solution
We implemented a **two-tier defense-in-depth security boundary**:

1. **Database-Level Row-Level Security (RLS):**
   Every tenant-scoped table in PostgreSQL 16 has RLS enabled with a strict policy:
   ```sql
   ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
   CREATE POLICY tenant_isolation_policy ON document_chunks
       FOR ALL
       TO authenticated_role
       USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
   ```

2. **AsyncPG / SQLAlchemy Session Context Manager:**
   Instead of relying on developers to manually inject tenant IDs into queries, every database operation is wrapped in a transactional context manager `tenant_session(tenant_id)`:
   ```python
   @asynccontextmanager
   async def tenant_session(tenant_id: str, bypass_rls: bool = False):
       async with async_session_factory() as session:
           if not bypass_rls:
               await session.execute(
                   text("SET LOCAL app.current_tenant_id = :tenant_id"),
                   {"tenant_id": tenant_id}
               )
           try:
               yield session
               await session.commit()
           except Exception:
               await session.rollback()
               raise
   ```
   Even if an application query omits `WHERE tenant_id = ...`, PostgreSQL's query planner automatically appends the RLS predicate.

3. **Hexagonal Boundary Enforcement:**
   An automated architectural AST test (`tests/test_architecture.py`) continuously scans the domain layer (`src/domain/`) to ensure no direct SQL execution or raw ORM imports bypass the repository abstraction.

---

## Case Study 2: HMAC Webhook Idempotency & Resilient Ledger Reconciliation

### 1. The Challenge
External payment providers (Stripe, Razorpay, PhonePe) send asynchronous webhook events for payment completions, refunds, and subscription renewals. Network retries, out-of-order deliveries, and concurrent webhook bursts can trigger duplicate entitlements or corrupt financial ledgers.

### 2. Architectural Solution
1. **Cryptographic Signature Verification:**
   Before parsing JSON bodies, raw bytes are validated using SHA-256 HMAC against provider secret keys (`X-Razorpay-Signature`, `Stripe-Signature`), aborting immediately on signature mismatch with constant-time comparison (`hmac.compare_digest`).

2. **Two-Phase Idempotency Lock:**
   Events are registered in an immutable `payment_events` table before domain processing:
   ```python
   async with tenant_session(tenant_id) as session:
       stmt = insert(PaymentEvent).values(
           event_id=raw_event_id,
           provider=provider_name,
           status="processing"
       ).on_conflict_do_nothing(index_elements=["event_id"])
       
       result = await session.execute(stmt)
       if result.rowcount == 0:
           return WebhookResponse(status="duplicate_acknowledged")
   ```

3. **Atomic Ledger State Machine:**
   Upon successful validation, tenant quotas, subscription status, and invoice line items are updated within the same database transaction. If any downstream step fails, the event status is marked as `failed` with the error trace, enabling automated retries via Celery without duplicate credit issuance.

---

## Case Study 3: Hybrid Retrieval with Reciprocal Rank Fusion & ColBERT Late Interaction

### 1. The Challenge
Dense vector search (bi-encoders) excels at conceptual matching but struggles with exact keyword queries (SKUs, error codes, domain-specific acronyms). Sparse search (BM25 / SPLADE) excels at exact matches but fails on semantic nuance. Furthermore, standard cosine similarity scores cannot be naively summed because their score distributions differ fundamentally.

### 2. Architectural Solution
1. **Parallel Multi-Engine Execution:**
   Queries are simultaneously dispatched across two retrieval paths:
   - **Dense Path:** 768-dimensional `nomic-embed-text` embeddings queried against a pgvector HNSW index (cosine distance).
   - **Sparse Path:** PostgreSQL full-text search with customized English/code dictionaries (or SPLADE lexical vectors).

2. **Reciprocal Rank Fusion (RRF):**
   Rather than normalizing raw scores, ranks are combined using constant $k=60$:
   $$RRF(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$
   This rank-based aggregation is mathematically invariant to score scaling differences between dense and sparse models.

3. **ColBERT / Cross-Encoder Reranking:**
   The top-$K$ candidates (default 25) are passed to a lightweight cross-encoder or ColBERT late-interaction reranker that computes token-level token-to-query interaction matrices. This recovers contextual relevance while keeping latency under 120ms.

4. **In-Memory Semantic Caching:**
   High-frequency queries are evaluated against an in-memory L2 semantic cache using cosine similarity (>0.96 threshold). Cache hits bypass vector index traversal entirely, delivering responses in under 15ms.

---

## Case Study 4: Production Dogfooding — Scoping as an Authentic Multi-Tenant Consumer

### 1. The Challenge
Many developer platforms suffer from "demo rot" where sample apps and client integrations break because internal developers use private APIs or hardcoded backdoors rather than the public SDK and HTTP endpoints.

### 2. Architectural Solution
1. **Zero-Backdoor Principle:**
   The commercial Project Scoping wizard on `prateeq.in/scoping` does not have private database access to Retriever. It interacts strictly as an external tenant:
   - Authenticates via `RETRIEVER_SCOPING_TENANT_ID` and `RETRIEVER_SCOPING_API_KEY`.
   - Uses the official `@/lib/rag-client` TypeScript client.
   - Leverages public endpoints: `POST /v1/tenants/{tenantId}/intent/classify` and `POST /v1/tenants/{tenantId}/search`.

2. **Deterministic Fallback Contract:**
   If the VPS or LLM provider experiences upstream latency spikes or network partitions, the client transparently falls back to an offline rule-based catalog matcher, explicitly flagging `fallbackMode: true` in the telemetry contract.

3. **Automated Client Onboarding:**
   When a prospective commercial client signs into `/dashboard`, a dedicated tenant (`tn_client_<uuid>`) is provisioned on Retriever with an immutable baseline document indexing the agreed Statement of Work (`is_system: true`), pre-grounding their client AI copilot from day one.
