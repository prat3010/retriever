---
id: DeepDive_Consensus_Reflection
title: "Cognitive Deep-Dive: Multi-Agent Consensus, Adversarial Debate & Reflection Loops"
tier: 6_retriever_cognitive
platform: retriever
tags:
  - cognitive/consensus
  - cognitive/reflection
  - cognitive/adversarial
  - platform/retriever
blast_radius: HIGH
invariants:
  - "Generator and Critic agents MUST use distinct prompt personas to prevent collusive false confidence."
  - "Consensus score MUST evaluate faithfulness, completeness, and citation validity."
---

# Cognitive Deep-Dive: Multi-Agent Consensus, Adversarial Debate & Reflection Loops

#cognitive #consensus #reflection #critic #generator #faithfulness #retriever

> **Technical architecture, debate protocols, and reflection loops for zero-hallucination factual synthesis.**

---

## 1. Adversarial Reflection Architecture

For mission-critical queries (legal, medical, financial), single-pass generation risks hallucination. Retriever deploys an adversarial multi-agent debate loop:

```mermaid
sequenceDiagram
    autonumber
    participant Context as Grounded Knowledge Chunks
    participant Gen as Generator Agent (Proposer)
    participant Critic as Critic Agent (Auditor)
    participant Arbiter as Consensus Arbiter

    Context->>Gen: Provide Retrieved Passages
    Gen->>Gen: Draft Candidate Synthesis
    Gen->>Critic: Submit Initial Draft
    
    loop Reflection Debate
        Critic->>Critic: Cross-examine draft against Ground-Truth Context
        Critic->>Critic: Score Faithfulness & Identify Ungrounded Claims
        alt Faithfulness >= 0.85 & Citations Valid
            Critic->>Arbiter: Approve Draft
        else Claims Hallucinated / Missing Context
            Critic->>Gen: Feedback: "Claim X ungrounded; Section Y contradicts"
            Gen->>Gen: Revise Draft addressing Feedback
        end
    end
    
    Arbiter->>Arbiter: Finalize Verified Consensus Response
```

---

## 2. Multi-Metric Scoring Formula

The Critic computes the composite consensus score \(S_{\text{consensus}}\):

\[
S_{\text{consensus}} = 0.40 \cdot \text{Faithfulness} + 0.30 \cdot \text{ContextRelevance} + 0.30 \cdot \text{CitationAccuracy}
\]

If \(S_{\text{consensus}} \ge 0.85\), the draft is declared validated and emitted immediately.

---

## 🔗 Related Architecture & Cross-References
- [Consensus API Specification](../api/consensus.md)
- [Evaluation & Hallucinations Deep-Dive](evaluation_and_hallucinations.md)
