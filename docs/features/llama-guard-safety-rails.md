# Structured Llama Guard 3 Safety Rails & S1–S13 Policy Moderation

**Milestone:** M85.1 (v0.70.1)  
**System Layer:** Content Moderation & AI Safety Guardrails (Platform Battery #12)  
**Architecture:** Meta Llama Guard 3 Policy Engine + Fast-Path Token Screening + Multi-Category Hazard Taxonomy (S1–S13)  

---

## 1. Executive Summary

Milestone 85.1 delivers **Platform Battery #12: `llama_guard_safety_rails`**, establishing automated adversarial prompt defense and content moderation across Retriever's conversational endpoints.

Without pre-inference safety moderation, customer-facing LLM systems are vulnerable to:
- Prompt-injection and jailbreak attacks (e.g. DAN, roleplay bypasses) designed to exfiltrate system prompts or bypass tenant boundaries.
- Generating hazardous, toxic, or legally actionable content (hate speech, self-harm instructions, malware code generation).
- PII leakage and regulatory non-compliance under EU AI Act and GDPR frameworks.

Platform Battery #12 deploys Meta's Llama Guard 3 model as an asynchronous pre- and post-generation classification gate. Prompts and assistant completions are evaluated against 13 standardized safety policies (S1–S13). Violations trigger immediate request rejection with standardized violation codes before any token generation occurs.

---

## 2. Policy Taxonomy (S1–S13 Hazard Categories)

Llama Guard 3 classifies content according to the MLCommons standardized safety taxonomy:

| Category | Description | Violation Action |
|:---|:---|:---|
| **S1: Violent Crimes** | Facilitating or encouraging bodily harm, homicide, kidnapping | Immediate 400 Rejection + Alert |
| **S2: Non-Violent Crimes** | Theft, fraud, money laundering, drug trafficking | Immediate 400 Rejection |
| **S3: Sex-Related Crimes** | Sexual assault, exploitation, harassment | Immediate 400 Rejection + Alert |
| **S4: Child Sexual Abuse Material (CSAM)** | Depicting or facilitating abuse of minors | Zero-Tolerance Hard Block + Key Quarantine |
| **S5: Defamation** | Knowingly false statements intended to harm reputations | Immediate 400 Rejection |
| **S6: Specialized Advice** | Practicing law, medicine, or financial trading without license | Intercepted + Disclaimed |
| **S7: Privacy / PII** | Unauthorized revelation of SSNs, passport numbers, home addresses | Redacted via Presidio / Rejected |
| **S8: Intellectual Property** | Facilitating software piracy, direct copyright infringement | Immediate 400 Rejection |
| **S9: Indiscriminate Weapons (CBRN)** | Chemical, biological, radiological, or nuclear weapon construction | Zero-Tolerance Hard Block + Alert |
| **S10: Hate Speech** | Attacking protected identity groups or slurs | Immediate 400 Rejection |
| **S11: Suicide & Self-Harm** | Encouraging or providing instructions for self-injury | Intercepted + Help Resources Emitted |
| **S12: Sexual Content** | Non-criminal explicit pornography or erotic generation | Immediate 400 Rejection |
| **S13: Automated Cyberattacks** | Generating polymorphic malware, zero-day exploits, DDoS code | Immediate 400 Rejection + Quarantine |

---

## 3. Pre- & Post-Inference Guardrail Pipeline

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        LLAMA GUARD 3 SAFETY PIPELINE                                   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   [ Inbound User Prompt ]                                                              │
│              │                                                                         │
│              ▼                                                                         │
│   ┌──────────────────────────────────────────────────────────────────────────┐         │
│   │ 1. Sub-20ms Heuristic Regex Pre-Filter                                   │         │
│   │    - Instantly catches known raw jailbreak phrases (e.g. "ignore rules") │         │
│   └────────────────────────────────────┬─────────────────────────────────────┘         │
│                                        │ (Passes Heuristics)                           │
│                                        ▼                                               │
│   ┌──────────────────────────────────────────────────────────────────────────┐         │
│   │ 2. Llama Guard 3 Classification Rail (~80ms)                             │         │
│   │    - Formulates prompt with MLCommons System Policy Context              │         │
│   │    - Emits "safe" or "unsafe\nS<category_number>"                        │         │
│   └────────────────────────────────────┬─────────────────────────────────────┘         │
│                                        │                                               │
│             ┌──────────────────────────┴──────────────────────────┐                    │
│             ▼ (Result: safe)                                      ▼ (Result: unsafe)   │
│   ┌────────────────────────────────┐                    ┌────────────────────────────┐ │
│   │ Forward to RAG Engine / LLM    │                    │ 400 ContentModerationError │ │
│   │ Ingest Context & Stream Tokens │                    │ Code: S1-S13 Categorized   │ │
│   └────────────────┬───────────────┘                    └────────────────────────────┘ │
│                    │                                                                   │
│                    ▼                                                                   │
│   ┌──────────────────────────────────────────────────────────────────────────┐         │
│   │ 3. Output Response Rail (Validates generated text before final stream)   │         │
│   └──────────────────────────────────────────────────────────────────────────┘         │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Implementation Details

- **Adapter:** `apps/api/src/adapters/guardrails/llama_guard_adapter.py`
- **FastAPI Router:** `apps/api/src/routers/guardrails.py`
- **Latency Profile:** $\sim 80\text{ms}$ classification evaluation.
- **Health Check Endpoint:** `GET /v1/safety/guardrails/status`

---

## 5. Non-Negotiable Invariants

1. **Zero Egress on Violation:** If Llama Guard returns `unsafe`, the raw prompt is never forwarded to the target LLM or vector search engine.
2. **Audit Trail Logging:** All S1–S13 violations are logged with timestamps and tenant IDs to `guardrail_audit_log` for security review.
3. **Deterministic Output:** Formatted as strict `safe` or `unsafe` with explicit violation category codes; unstructured model responses are parsed strictly.
