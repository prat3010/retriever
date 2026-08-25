---
id: Retriever_API_v1_consensus
title: "API Specification: Multi-Agent Consensus & Adversarial Reflection (/v1/consensus)"
tier: 4_api_gateway
platform: retriever
tags:
  - api/consensus
  - cognitive/generator-critic
  - cognitive/reflection
  - platform/retriever
blast_radius: HIGH
security_auth: BEARER_JWT
invariants:
  - "Adversarial reflection loop MUST terminate when consensus_score >= 0.85 or max_rounds reached."
---

# API Specification: Multi-Agent Consensus & Adversarial Reflection (`/v1/consensus`)

#api #consensus #reflection #critic #adversarial #retriever

> **Authoritative specification for Generator-Critic multi-agent debate loops, hallucination detection, and grounded consensus scoring.**

---

## 1. Adversarial Debate Loop Flow

```mermaid
sequenceDiagram
    autonumber
    actor Client as User / System
    participant Router as Consensus Router (/v1/consensus)
    participant Gen as Generator Agent (Proposer)
    participant Critic as Critic Agent (Auditor)
    participant Context as Grounded Context Chunks

    Client->>Router: POST /v1/tenants/{id}/consensus/debate
    Router->>Gen: Draft initial synthesis from context
    Gen-->>Router: Initial Draft Proposal
    loop Adversarial Reflection (Rounds 1 to N)
        Router->>Critic: Critique draft against ground-truth context
        Critic-->>Router: Critique (Issues, Missing Citations, Consensus Score)
        alt Consensus Score >= 0.85 or No Errors
            Note over Router: Consensus Reached!
        else Consensus Score < 0.85
            Router->>Gen: Revise draft addressing Critic points
            Gen-->>Router: Refined Synthesis
        end
    end
    Router-->>Client: Final Consensus Answer + Debate Trace
```

---

## 2. API Endpoints

### 2.1 Run Multi-Agent Consensus Debate

- **HTTP Method:** `POST`
- **Path:** `/v1/tenants/{tenantId}/consensus/debate`
- **Authentication:** `Bearer <TOKEN>`
- **Request Body:**
```json
{
  "query": "Is the middleman commission payment refundable after 14 days?",
  "maxRounds": 3,
  "minConsensusScore": 0.85
}
```

#### Response Schema (`200 OK`)
```json
{
  "status": "consensus_achieved",
  "roundsExecuted": 2,
  "finalConsensusScore": 0.94,
  "finalAnswer": "No, middleman commission disbursements become fully non-refundable after the 14-calendar-day escrow review period expires [Source: agreement_sec_4].",
  "debateRounds": [
    {
      "round": 1,
      "generatorDraft": "Commission disbursements cannot be refunded after 14 days.",
      "criticScore": 0.70,
      "critique": "Draft lacks reference to Section 4 escrow review conditions."
    },
    {
      "round": 2,
      "generatorDraft": "No, middleman commission disbursements become fully non-refundable after the 14-calendar-day escrow review period expires [Source: agreement_sec_4].",
      "criticScore": 0.94,
      "critique": "Fully grounded and cites authoritative section."
    }
  ]
}
```

---

## 🔗 Related Architecture & Cross-References
- [Consensus & Reflection Deep-Dive](../cognitive/consensus_and_reflection.md)
- [Evaluation & Hallucinations](../cognitive/evaluation_and_hallucinations.md)
