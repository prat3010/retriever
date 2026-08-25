---
id: DeepDive_Guardrails_Safety_LlamaGuard
title: "Cognitive Deep-Dive: Enterprise Guardrails, Llama Guard 3 & Zero-Footprint PII Redaction"
tier: 6_retriever_cognitive
platform: retriever
tags:
  - cognitive/guardrails
  - cognitive/llamaguard
  - security/pii
  - platform/retriever
blast_radius: CRITICAL
invariants:
  - "Prompt injection attacks MUST trigger an instant 400 Bad Request before LLM execution."
  - "PII scrubbing MUST sanitize emails, phone numbers, SSNs, and credit cards via regex & NER."
---

# Cognitive Deep-Dive: Enterprise Guardrails, Llama Guard 3 & Zero-Footprint PII Redaction

#cognitive #guardrails #llamaguard #pii #security #safety #retriever

> **Technical architecture, prompt injection defenses, content moderation classifiers, and zero-footprint PII redaction.**

---

## 1. Zero-Trust Guardrails Architecture

Retriever wraps every inbound user prompt and outbound LLM generation with a dual-stage safety perimeter:

```mermaid
flowchart TD
    UserPrompt([User Prompt]) --> G1{Llama Guard 3 Pre-Flight}
    G1 -->|Violates Policy / Injection| Block1[Reject: 400 SAFETY_VIOLATION]
    G1 -->|Safe| PII1[Regex & Presidio PII Masking]
    
    PII1 --> Search[Hybrid Knowledge Retrieval]
    Search --> LLM[Frontier LLM Completion]
    
    LLM --> G2{Llama Guard 3 Post-Flight}
    G2 -->|Unsafe Output| Block2[Substitute: Neutral Fallback Response]
    G2 -->|Safe| PII2[PII De-anonymization / Final Scrub]
    PII2 --> Response([Client SSE Stream])
```

---

## 2. Protected Hazard Categories

| Hazard Code | Category Description | Detection Engine |
|:---|:---|:---|
| `S1` | Violent Crimes & Physical Harm | Llama Guard 3 |
| `S2` | Non-Violent Illegal Acts | Llama Guard 3 |
| `S3` | Sexually Explicit Content | Llama Guard 3 |
| `S4` | Child Sexual Exploitation | Llama Guard 3 |
| `S5` | Defamation & Hate Speech | Llama Guard 3 |
| `S6` | Specialized Advice (Financial / Medical) | Domain Boundary Classifier |
| `S7` | System Prompt Extraction & Jailbreaks | Regex + Heuristic AST Filter |
| `PII` | Email, Phone, Credit Card, SSN, API Keys | Microsoft Presidio / Regex Engine |

---

## 🔗 Related Architecture & Cross-References
- [Chat API Specification](../api/chat.md)
- [Zero-Trust Storage & Encryption](../infrastructure/storage_and_encryption.md)
