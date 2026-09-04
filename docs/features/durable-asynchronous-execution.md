# Durable Asynchronous Execution & Background AI Workflow Engine

**Milestone:** M95 (v0.80.0)  
**System Layer:** Background Workflows & Checkpoint State Machine (Battery #15)  
**Architecture:** Pure Hexagonal Domain + PostgreSQL 16 Checkpoint Repository + Async Exponential Backoff Runner

---

## 1. Executive Summary

Enterprise AI batch workloads (such as indexing multi-gigabyte document vaults, extracting multi-document entity graphs, or generating thousands of synthetic test triplets) are inherently long-running. Traditional synchronous APIs or naive background fire-and-forget tasks fail when subjected to transient cloud network drops, rate limit exceptions, or container restarts.

Milestone 95 introduces the **Durable Asynchronous Execution Engine** as **Platform Battery #15**:
- **Step-Level Memoization:** Intermediate outputs of each pipeline step are checkpointed into PostgreSQL. Upon restart or retry, completed steps replay in $<2\text{ms}$ with zero computation or token cost.
- **Resilient Automatic Backoff:** Automatic exponential backoff retries on transient step failures.
- **Strict Multi-Tenancy:** State tables (`workflow_executions`, `workflow_step_checkpoints`) enforce PostgreSQL Row-Level Security (RLS) scoped by `tenant_id`.
- **Pre-Packaged Enterprise Blueprints:** Ready-to-run pipelines for vault bulk ingestion, batch GraphRAG extraction, synthetic evaluation generation, and semantic cache re-embedding.

---

## 2. Architecture Topology

```text
               [Client / Webhook Trigger / Studio UI]
                                │
                                ▼
               ┌─────────────────────────────────┐
               │    FastAPI Workflow Router      │
               │   (Check Concurrency & Idemp)   │
               └────────────────┬────────────────┘
                                │
                                ▼
               ┌─────────────────────────────────┐
               │     DurableWorkflowAdapter      │
               │   (Background asyncio Runner)   │
               └────────────────┬────────────────┘
                                │
                  For each Step in Blueprint:
                                │
                                ▼
                     Is Step Checkpoint Saved?
                                / \
                       YES    /     \   NO
                            /         \
                           ▼           ▼
                   [Replay Memoized] [Execute Step Handler]
                   (0 computation)             │
                                               ▼
                                      Step Successful?
                                            / \
                                   YES    /     \   NO
                                        /         \
                                       ▼           ▼
                             [Commit Checkpoint] [Retry with Backoff]
                             [in PostgreSQL RLS] [or Transition FAILED]
                                       │
                                       ▼
                       All Steps Completed?
                                       │
                                       ▼
                     [Send HMAC SHA-256 Webhook]
```

---

## 3. Pre-Packaged Blueprints

1. **`vault_bulk_ingest`:**
   - Steps: `scan_documents` $\rightarrow$ `chunk_and_embed` $\rightarrow$ `index_vectors`
   - Scans markdown/PDF files, calculates checksums, computes `nomic-embed-text` embeddings, and indexes into pgvector.
2. **`batch_graph_extraction`:**
   - Steps: `extract_entities` $\rightarrow$ `link_relations` $\rightarrow$ `build_graph_clusters`
   - Dispatches document chunks to LLM entity extractors, constructs graph edges, and computes Leiden community clusters.
3. **`synthetic_eval_generator`:**
   - Steps: `sample_chunks` $\rightarrow$ `synthesize_qa_pairs` $\rightarrow$ `filter_and_export`
   - Samples document distribution, generates challenging question-answer-context triplets, and produces a golden evaluation set.
4. **`bulk_reembed_pipeline`:**
   - Steps: `fetch_cache_keys` $\rightarrow$ `recompute_embeddings` $\rightarrow$ `update_cache_store`
   - Re-embeds query keys when switching models without service downtime.

---

## 4. Crash Recovery & Step Replay

When a workflow experiences an unexpected process termination:
1. The execution row remains in `running` or is marked `failed`.
2. A client or administrator triggers the `/retry` endpoint.
3. The runner reads all existing checkpoints for `execution_id`.
4. For every step with a status of `completed`, the cached `memoized_output` is injected directly into the step execution context without executing the step function.
5. Execution resumes at the exact step that failed or was interrupted.
