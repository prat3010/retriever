# ADR-027: Cognitive Agent Memory Consolidation & Long-Horizon Experience Distillation

**Status:** Accepted  
**Date:** 2026-09-14  
**Deciders:** Principal Cognitive Systems Architects, AI Economists, Platform Reliability Engineers  
**Consulted:** SaaS Studio Team, Enterprise Client Operations  
**Informed:** Enterprise Clients, Developer Ecosystem  

---

## 1. Context and Problem Statement

In autonomous multi-turn ReAct agent systems, exploratory trajectories across complex tool spaces (e.g. database schema discovery, Python REPL data pipelines, error diagnosis) generate rich problem-solving experiences. However, typical agentic platforms treat each session as an isolated blank slate:
1. **Amnestic Re-Exploration:** When faced with identical or analogous downstream tasks, agents repeat costly, trial-and-error exploratory steps, incurring redundant token spend and latency.
2. **Error Re-Occurrence:** Ephemeral tool failure recovery patterns (such as fixing a CSV delimiter mismatch or catching missing dict keys) are forgotten as soon as the session closes, forcing the agent to re-learn error recoveries repeatedly.
3. **Linear Context Bloat:** Naively dumping raw historical traces into prompts exhausts context windows, dilutes attention, and degrades reasoning precision.

To solve these challenges, Retriever introduced **Platform Battery #25: Cognitive Agent Memory Consolidation & Long-Horizon Experience Distillation** (`v0.92.0`, Milestone 108).

---

## 2. Decision Drivers

- **Hexagonal Architecture Decoupling:** Pure domain abstractions in `src/domain/abstractions/memory.py` (`MemoryType`, `EpisodicMemoryNode`, `MemoryQuery`, `DistilledGuidance`, `CognitiveMemoryProtocol`) with strictly zero framework, ORM, or database imports, verified by AST introspection tests.
- **Mathematical Ebbinghaus Retention Decay:**
  $$R(t) = \exp\left(-\frac{\Delta t}{S \times 86,400}\right)$$
  where $\Delta t$ is elapsed seconds since the last retrieval and $S$ represents memory stability in days.
- **Memory Stability Reinforcement:** Each time a memory node successfully primes a downstream agent session, its stability expands:
  $$S_{\text{new}} = 1.5 \times S_{\text{old}} + 0.5$$
  frequently utilized operational patterns resist decay, while transient exploratory noise decays exponentially toward pruning ($R < 0.15$).
- **Autonomous Procedural Heuristic Synthesis:** During ReAct trajectory post-loop consolidation, turn transitions exhibiting error-to-success transitions ($\text{turn}_k \to \text{error}, \text{turn}_{k+1} \to \text{success}$) are automatically synthesized into `PROCEDURAL` memory nodes with elevated importance ($0.85$), preserving critical self-healing procedures.
- **Tenant-Isolated Vector Guidance Injection:** Prior to entering the ReAct reasoning loop, the engine queries cognitive memory via term-vector cosine similarity and semantic filtering, injecting a compact, high-signal experience prompt (`DISTILLED EXPERIENCE FROM PRIOR SESSIONS`) without human intervention.

---

## 3. Considered Options

### Option 1: Monolithic Raw Chat Log Storage (Dumping Transcripts into Vector Store)
- *Pros:* Easy to implement by storing full conversation strings.
- *Cons:* Extremely noisy; contains irrelevant conversational chatter; high retrieval token cost; lacks mathematical forgetting curves or stability reinforcement; agent context quickly degrades.

### Option 2: External Memory Service (e.g. MemGPT/Letta API)
- *Pros:* Third-party managed service for long-term agent memory.
- *Cons:* Introduces external network latency and vendor lock-in; violates local-first sovereignty invariants; uncoupled from Retriever's internal ReAct self-healing mechanics and multi-model economic gateway.

### Option 3: Hexagonal Cognitive Memory Engine with Ebbinghaus Decay & ReAct Trajectory Distillation (Chosen)
- *Pros:*
  - Pure Python domain abstractions conforming strictly to hexagonal architecture.
  - Mathematical forgetting dynamics via empirical Ebbinghaus decay curve.
  - Zero-compute pruning of decayed noise ($R < 0.15$).
  - Seamless native ReAct integration (pre-loop guidance injection + post-loop trace consolidation).
  - Multi-tenant isolation enforced at domain, storage, and API layers.

---

## 4. Decision Outcome

Adopt Option 3. `CognitiveMemoryEngine` is implemented in `apps/api/src/domain/memory/engine.py` and mounted via `/api/v1/memory` in FastAPI, consumed by the SaaS Studio workspace via `MemoryPanel.tsx` in `Prateek_website`.

### Positive Consequences
- Agents learn from past sessions across the tenant workspace, eliminating redundant exploratory tool calls.
- Self-healing recovery techniques are systematically preserved as procedural memory nodes.
- High signal-to-noise ratio in prompt space, bounded token usage via Ebbinghaus decay.
- Full parity with Design System 2.0 and interactive Experience Distillation Simulator in SaaS Studio.

---

## 5. Architectural Verification & Compliance

- Pure domain boundary asserted by `apps/api/tests/test_architecture.py`.
- Zero-toy verification asserted by `apps/api/tests/test_zero_toy_invariants.py` and `scripts/audit_zero_toy.py`.
- Complete unit and integration test suite passing in `apps/api/tests/test_memory.py` (8/8 passed).
- Frontend Vitest suite passing in `src/components/rag/__tests__/MemoryPanel.test.tsx` (5/5 passed).
