# ADR-013: LangGraph Cyclic Agentic Orchestration & Human-in-the-Loop State Engine

## Status
Accepted

## Context
Complex cognitive workflows (document synthesis, deep research, contract audits, and autonomous lead prospecting) require multi-step reasoning, dynamic tool usage, and cyclic reflection. Standard DAG execution engines (e.g. basic chains) cannot handle loops, conditional self-correction, or human intervention pauses.

## Problem
We need an agentic execution platform that:
1. Supports cyclic execution graphs with conditional branching and multi-turn reflection.
2. Persists full state checkpoints at every step in PostgreSQL to allow time-travel debugging and workflow resumption.
3. Provides first-class Human-in-the-Loop (HITL) approval gates for high-risk actions (e.g., executing Python code, financial payouts, external emails).

## Decision
Adopt **LangGraph Cyclic State Orchestration** backed by PostgreSQL persistence:
1. Implement `LangGraphOrchestratorAdapter` conforming to Hexagonal domain boundaries.
2. Persist state snapshots in `agent_checkpoints` with RLS tenant isolation.
3. Support `interrupt_before` gates where workflows halt, emit pending approval payloads to the Admin Dashboard / Client Studio, and resume seamlessly once approved.
4. Expose REST endpoints under `/v1/agentic/*` (`/invoke`, `/stream`, `/state/{threadId}`, `/approve/{threadId}`).

## Consequences
* **Stateful Resilience:** Workflows survive server restarts and can be inspected or resumed from any previous checkpoint.
* **Safety:** Destructive or high-impact actions require explicit cryptographic administrator authorization before execution.
* **Storage Footprint:** Checkpointing multi-step conversations generates JSON state snapshots in PostgreSQL, managed by automated data retention schedules.

## Future Review Criteria
* Review checkpoint table size and apply vacuuming/archival policies when thread count exceeds 100,000.
