# Multi-Agent Swarm Quorum & Dialectic Debate Consensus Engine

**Milestone:** M109 (v0.93.0)  
**System Layer:** Multi-Agent Systems & Machine Learning Intelligence (Platform Battery #26)  
**Architecture:** Dialectic Debate DAG + Role-Calibrated Weighted Quorum Voting + Automated Hallucination Pruning  

---

## 1. Executive Summary

Milestone 109 registers **Platform Battery #26 (`multi_agent_swarm_quorum`)** under the `ML_INTELLIGENCE` category.

Single-agent systems—even those equipped with multi-turn ReAct loops—suffer from confirmation bias and blind-spot hallucinations. When an LLM generates an ungrounded assumption in step 1, downstream steps compound the hallucination.

Milestone 109 introduces a structured multi-agent dialectic debate engine:
- **Specialized Multi-Agent Roles:**
  - **Strategic Planner ($w=1.1$):** Formulates step-by-step resolution proposals.
  - **Adversarial Skeptic ($w=1.3$):** Identifies logical inconsistencies and edge cases.
  - **Forensic Auditor ($w=1.4$):** Cross-examines every candidate claim against retrieved document chunks.
  - **Code Synthesizer ($w=1.2$):** Formulates verified executable artifacts.
- **Role-Calibrated Weighted Quorum Voting:** Resolves competing answers via mathematical consensus threshold ($\tau_{\text{quorum}} \ge 0.67$).
- **Automated Hallucination Elimination:** Any claim failing factual verification during forensic audit is quarantined from the final ballot.

---

## 2. Mathematical Formulation

### Weighted Consensus Score
For candidate resolution $A_k$:
$$V(A_k) = \frac{\sum_{i \in \text{Agents}} w_i \cdot c_{i,k} \cdot \mathbf{1}(\text{vote}_i = A_k)}{\sum_{i \in \text{Agents}} w_i}$$
Where:
- $w_i \in \{1.1, 1.2, 1.3, 1.4\}$ represents the calibrated authority weight of agent $i$.
- $c_{i,k} \in [0, 1]$ represents the subjective confidence score assigned by agent $i$.
- A candidate $A_k$ reaches consensus if and only if $V(A_k) \ge \tau_{\text{quorum}}$ (default: $0.67$).

---

## 3. Battery Specifications & Parameters

- **Identifier:** `multi_agent_swarm_quorum`
- **Category:** `ML_INTELLIGENCE`
- **Latency Profile:** `<45ms` multi-agent debate synthesis overhead
- **Algorithm Foundation:** Dialectic DAG Debate + Weighted Quorum Voting & Hallucination Elimination
- **Health Check Endpoint:** `/v1/consensus/swarm`
- **Dynamic LLM Debate Synthesis (M124):** In addition to heuristic arbitration, `MultiAgentSwarmQuorumEngine` now binds an optional `LLMInferenceProvider` (`src/domain/abstractions/inference.py`). When configured, agent arguments, dialectic counter-arguments, and consensus synthesis are generated dynamically through structured LLM calls with persona-grounded system prompts, eliminating static template heuristics while strictly preserving quorum voting math.

### Active Parameters
| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| `quorum_threshold` | `float` | `0.67` | Minimum weighted vote ratio required for consensus |
| `agents_count` | `int` | `3` | Number of active debating agents |
| `dialectic_rounds` | `int` | `2` | Number of critique and rebuttal rounds |
| `prune_unverified` | `bool` | `true` | Quarantines claims without document citation grounding |
| `llm_provider` | `Optional[LLMInferenceProvider]` | `None` | Pluggable LLM inference engine for dynamic multi-turn dialectic generation |

