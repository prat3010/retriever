# ADR-028: Multi-Agent Swarm Quorum & Dynamic Debate Consensus Engine

**Status:** Accepted  
**Date:** 2026-09-14  
**Deciders:** Principal Cognitive Systems Architects, AI Economists, Platform Reliability Engineers  
**Consulted:** SaaS Studio Team, Enterprise Client Operations  
**Informed:** Enterprise Clients, Developer Ecosystem  

---

## 1. Context and Problem Statement

Single-agent reasoning engines (even multi-turn ReAct loops) suffer from inherent confirmation bias: once an LLM proposes an unverified assumption or hallucinated citation in early steps, downstream reasoning frequently compounds the error. Simple two-agent generator-critic reflection loops provide baseline critique, but lack specialized cross-examination:
1. **Lack of Specialization:** A single critic cannot simultaneously audit low-level algorithmic correctness, compliance boundaries, and multi-hop operational plans.
2. **Ungrounded Hallucinations:** Claims made without verified evidentiary backing can slip through unstructured conversations.
3. **Absence of Weighted Quorum Consensus:** Competing candidate solutions lack formal mathematical consensus mechanics to resolve disputes with role-calibrated authority.

To resolve these limitations, Retriever introduced **Platform Battery #26: Multi-Agent Swarm Quorum & Dynamic Debate Consensus Engine** (`v0.93.0`, Milestone 109).

---

## 2. Decision Drivers

- **Hexagonal Architecture Decoupling:** Pure domain abstractions in `src/domain/abstractions/agent_swarm.py` (`SwarmAgentRole`, `DebateStance`, `CandidateClaim`, `DebateTurn`, `DebateRound`, `AgentBallot`, `CandidateResolution`, `QuorumConsensusResult`, `SwarmDebateProtocol`) with strictly zero framework, ORM, or database imports.
- **Dialectic Topology DAG (`networkx.DiGraph`):** Agents interact along directed communication edges (`PLANNER -> SKEPTIC`, `SKEPTIC -> SYNTHESIZER`, `SYNTHESIZER -> AUDITOR`, `AUDITOR -> PLANNER`), preventing unstructured broadcast noise and establishing clear review accountability.
- **Role-Calibrated Weighted Quorum Mathematics:**
  $$V(A_k) = \frac{\sum_{i \in \text{Agents}} w_i \cdot c_{i,k} \cdot \mathbf{1}(\text{agree})}{\sum_{i \in \text{Agents}} w_i}$$
  where role weights reflect specialized authority (Forensic Auditor $w=1.4$, Adversarial Skeptic $w=1.3$, Code Synthesizer $w=1.2$, Strategic Planner $w=1.1$).
- **Automated Hallucination Pruning:** Any claim failing factual verification during the Forensic Auditor's cross-examination is quarantined from the final ballot and archived into `hallucinations_pruned`.
- **Pre-Loop Memory Priming & Post-Loop Trace Consolidation:** Dialectic debates consult Battery #25's `CognitiveMemoryEngine` to ingest relevant episodic guidance in Round 1, and automatically consolidate winning consensus traces upon reaching quorum.

---

## 3. Decision Outcome

Implemented `MultiAgentSwarmQuorumEngine` in `apps/api/src/domain/agentic/swarm/engine.py` and exposed tenant-isolated endpoints via `apps/api/src/routers/agent_swarm.py`:
- `POST /v1/tenants/{tenantId}/agentic/swarm/debate`: Synchronous debate and quorum execution.
- `POST /v1/tenants/{tenantId}/agentic/swarm/debate/stream`: Real-time SSE streaming of turns, critiques, and ballots.
- `GET /v1/tenants/{tenantId}/agentic/swarm/roles`: Lists registered role profiles and voting weights.
- `GET /v1/tenants/{tenantId}/agentic/swarm/stats`: Operational telemetry.

### Positive Consequences
- **Eliminates Confirmation Bias:** High-stakes tasks are thoroughly cross-examined from structural, evidentiary, algorithmic, and adversarial angles.
- **Formal Quorum Verification:** Eliminates arbitrary tie-breaking; only candidate resolutions reaching the $\tau_{\text{quorum}}$ threshold are endorsed.
- **Full Observability:** Live turn-by-turn SSE streaming powers the SaaS Studio `SwarmPanel.tsx` cockpit in `Prateek_website`.
