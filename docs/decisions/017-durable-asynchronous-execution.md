# ADR-017: Durable Asynchronous Execution & Checkpoint State Machine Engine

**Status:** Accepted  
**Date:** 2026-09-04  
**Deciders:** Core Engineering Team  
**Consulted:** Distributed Systems Architects, Reliability Engineering  
**Informed:** Platform Tenants, API Consumers  

---

## 1. Context and Problem Statement

Retriever operations frequently involve multi-minute asynchronous workloads:
- Ingesting and embedding enterprise vaults containing hundreds of PDFs and markdown documents.
- Multi-document Knowledge Graph extraction and community clustering (GraphRAG).
- Synthetic evaluation triplet synthesis (Q&A ground-truth generation).
- Bulk re-embedding of semantic cache vector indexes.

Previously, these operations ran as fragile in-process tasks or synchronous HTTP calls. When process restarts, VPS deployments, network timeouts, or rate limit exceptions occurred:
- The entire workload failed with no state preserved.
- Resuming meant re-running from step 0, wasting expensive embedding tokens and LLM API quotas.
- Tenants had no visibility into intermediate step execution status, execution times, or checkpoint outputs.

The platform required an industrial durable execution engine supporting step-level memoization, idempotent checkpointing, exponential backoff retries, and crash recovery.

---

## 2. Decision Drivers

- **Zero-Waste Crash Recovery:** If step 3 of a 5-step workflow crashes or is killed, retrying must resume from step 3 without re-executing steps 1 and 2 (step memoization).
- **Hexagonal Purity:** Domain logic (`src/domain/abstractions/durable_workflow.py` and `src/domain/workflow/durable_engine.py`) must remain pure Python with zero database, framework, or cloud dependencies.
- **Strict Multi-Tenancy:** Workflow execution state and step checkpoints must enforce database-level tenant isolation (Postgres RLS) to prevent cross-tenant data leaks.
- **Idempotency & Concurrency Control:** Duplicate webhook or API triggers with the same `idempotency_key` must return the existing execution rather than launching parallel workers. Concurrency limits per workflow blueprint must be enforced.
- **Zero-Dependency Core:** The engine must work reliably in development and lightweight VPS environments using PostgreSQL 16 state tables, with optional Redis lock backends.
- **Platform Battery Registration:** Formalized as Battery #15 (`durable_workflow_engine`) under `BACKGROUND_WORKFLOWS`.

---

## 3. Considered Options

1. **Option 1: Temporal.io / Temporal Server:** Deploy a full Temporal cluster with dedicated worker processes.
   - *Downside:* Massive infrastructure footprint (Temporal server, Cassandra/Postgres, UI container), complex deployment topology, high operational overhead for single VPS setups.
2. **Option 2: Celery + Redis:** Traditional message queue worker pool.
   - *Downside:* Celery lacks native deterministic step-level memoization and state machine checkpoint persistence without extensive custom database plugins.
3. **Option 3: Embedded Durable Checkpoint State Machine (Chosen):** Pure Hexagonal domain model with step-level memoization, PostgreSQL state tables (`workflow_executions`, `workflow_step_checkpoints`), exponential backoff retry runner, and HMAC webhook dispatching.

---

## 4. Decision Outcome

**Chosen Option:** **Option 3 (Embedded Durable Checkpoint State Machine)**.

### Rationale:
- **Zero Additional Infrastructure Overhead:** Runs directly inside the existing FastAPI process and PostgreSQL 16 database without adding container dependencies or operational complexity.
- **Step-Level Memoization:** Each step checkpoint serializes its `memoized_output` to PostgreSQL. Upon restart, the adapter replays completed checkpoints in $<2\text{ms}$ with zero computation cost.
- **Pre-packaged Enterprise Blueprints:** Ships out of the box with 4 battle-tested pipelines:
  1. `vault_bulk_ingest`
  2. `batch_graph_extraction`
  3. `synthetic_eval_generator`
  4. `bulk_reembed_pipeline`
- **Outbound Event-Driven Notifications:** Workflows emit signed HMAC SHA-256 webhooks to client-specified URLs on completion or failure.

---

## 5. Consequences

### Positive:
- Uninterrupted long-running batch jobs that survive server restarts and deployment cycles.
- Token cost savings of up to $80\%$ on recovered workflows through step-level output caching.
- Native multi-tenant isolation guarded by PostgreSQL Row-Level Security.
- Full real-time observability in Retriever Studio with visual DAG timelines and step checkpoint inspection.
- Registered as Platform Battery #15 in `BatteryService`.

### Negative / Trade-offs:
- Intermediate step outputs must be JSON-serializable to store in the checkpoint database.
- Extreme high-throughput task queuing ($>10,000\text{ jobs/sec}$) would eventually require a distributed message broker like NATS or Kafka.
