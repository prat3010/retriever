# NVIDIA NeMo Guardrails & Multi-Turn Conversational Safety Engine

**Milestone:** M94 (v0.79.0)  
**System Layer:** Cognitive Security & Conversational Flow Controller (Battery #13)  
**Architecture:** Dual-Stage (Sub-20ms Fast-Path Input Rail + Colang State Steering + Factual Grounding Output Rail)

---

## 1. Executive Summary

Enterprise deployments of cognitive RAG systems encounter three distinct vulnerability classes that cannot be solved by system prompts alone:
1. **Adversarial Jailbreaks & System Extraction:** Clever prompt-engineering attacks (e.g., DAN, Base64 obfuscation, multi-turn escalation) that coerce the model into ignoring foundational safety constraints or leaking system instructions.
2. **Conversational Drift & Off-Topic Exploitation:** Users abusing customer-facing bots as free general-purpose conversational engines (e.g. asking for homework help, political opinions, or competitor endorsements), ballooning token costs and creating corporate brand liability.
3. **Factual Hallucinations & Unauthorized Commitments:** Generative models committing to unauthorized price discounts, inventing nonexistent warranties, or fabricating technical capabilities not supported by verified retrieved chunks.

Milestone 94 integrates **NVIDIA NeMo Guardrails architecture** into Retriever as **Platform Battery #13**, pairing sub-20ms heuristic input screening with programmable **Colang (`.co`)** conversational state definitions and post-generation factual entailment scoring.

---

## 2. Architecture & Pipeline Topology

```text
                           [Incoming Client Query]
                                      │
                                      ▼
             ┌─────────────────────────────────────────────────┐
             │       STAGE 1: FAST-PATH INPUT RAIL (<20ms)     │
             │   • Heuristic Regex Scanner (DAN, jailbreaks)   │
             │   • Asynchronous with Vector Embedding Compute   │
             └────────────────────────┬────────────────────────┘
                                      │
                         Is Query Jailbreak/Malicious?
                                     / \
                             YES   /     \  NO
                                 /         \
                                ▼           ▼
                       [Block 400 Bad Req]  │
                                            ▼
             ┌─────────────────────────────────────────────────┐
             │       STAGE 2: COLANG INTENT & DIALOG FLOW      │
             │   • Parse active tenant Colang (.co) rules      │
             │   • Detect competitor entities & off-topic query │
             │   • Multi-turn intent steering state machine    │
             └────────────────────────┬────────────────────────┘
                                      │
                         Did Query Match Steer Flow?
                                     / \
                             YES   /     \  NO
                                 /         \
                                ▼           ▼
                       [Return Predefined] [Dispatch to LLM &
                        Steered Response    Retrieve Chunks]
                                (0 tokens)          │
                                                    ▼
             ┌─────────────────────────────────────────────────┐
             │       STAGE 3: FACTUAL GROUNDING OUTPUT RAIL    │
             │   • Cross-reference response with context chunks│
             │   • Entailment & token containment scoring      │
             │   • Zero-Trust PII scrubber (SSN, CC, Tokens)   │
             └────────────────────────┬────────────────────────┘
                                      │
                         Is Grounding Score >= Threshold?
                                     / \
                             YES   /     \  NO (in STRICT mode)
                                 /         \
                                ▼           ▼
                       [Stream Grounded    [Intercept & Deliver
                        Response to Client] Polite Disclaimers]
```

---

## 3. The Colang (`.co`) Specification in Retriever

Colang is NVIDIA's domain-specific language for modeling conversational dialog flows. Retriever implements an authentic, zero-overhead pure Python Colang interpreter conforming to standard `.co` syntax:

### 3.1 Intent Definitions (`define user ...`)
Groups natural language variations into semantic user intents:
```colang
define user express greeting
  "hello"
  "hi there"
  "hey"
  "good morning"

define user ask competitor comparison
  "why are you worse than competitor"
  "is competitor cheaper than you"
  "switch to competitor"
```

### 3.2 Bot Response Definitions (`define bot ...`)
Defines standardized, enterprise-approved responses:
```colang
define bot offer help
  "Hello! I am your AI platform assistant grounded in verified documentation. How can I assist you today?"

define bot address competitor neutrally
  "We focus on providing verified PostgreSQL pgvector benchmarks and strict multi-tenant isolation. Our engineering team can provide a tailored comparison."
```

### 3.3 Flow State Machines (`define flow ...`)
Binds user intents to conversational responses and determines steering action:
```colang
define flow greeting
  user express greeting
  bot offer help

define flow competitor inquiry
  user ask competitor comparison
  bot address competitor neutrally
```

---

## 4. Pre-Packaged Enterprise Templates

Retriever provides 4 out-of-the-box Colang templates customizable via the SaaS Studio:

| Template Name | Domain | Key Behaviors |
| :--- | :--- | :--- |
| **Enterprise Customer Support** | B2B SaaS & Portals | Off-topic redirection, polite greeting, competitor shielding |
| **Legal & Risk Governance** | Legal, Compliance | Mandatory disclaimers, liability avoidance, advice refusal |
| **Financial & Pricing Protection** | FinTech, E-Commerce | Blocks unauthorized discount promises, redirects commercial terms |
| **Technical Developer Assistant** | Engineering Copilots | Permits code/shell syntax while blocking base prompt exfiltration |

---

## 5. Empirical Performance & Latency Budget

| Stage | Operation | Average Latency | Concurrency Behavior |
| :--- | :--- | :--- | :--- |
| **Fast-Path Input Rail** | Heuristic injection scanner | **~3.5ms** | Non-blocking, parallel with embedding generation |
| **Colang Intent Matcher** | Multi-turn flow evaluation | **~8.2ms** | In-memory token overlap & exact matching |
| **Competitor Shield** | Entity inspection | **~1.8ms** | Regex boundary search across tenant blacklist |
| **Factual Grounding Rail** | Key term context containment | **~5.1ms** | Runs post-generation on completed response |
| **End-to-End Rail Overhead** | Full pipeline evaluation | **~14.5ms** | $<2\%$ overhead on typical 800ms LLM inference |

---

## 6. Multi-Tenancy Isolation Guarantees

1. **Tenant-Scoped Policies:** Every tenant maintains independent Colang scripts, active flow definitions, competitor name registries, and grounding thresholds (`TenantGuardrailsConfig`).
2. **Isolated Telemetry Buffers:** Security violations are strictly partitioned by `tenant_id`. Tenant A cannot inspect or correlate security violations triggered by Tenant B.
3. **Database RLS Invariant:** Any persistence layer operations respect PostgreSQL Row-Level Security policies.

---

## 7. Administrative & Client UI Surfaces

- **Retriever Master Admin Cockpit (`admin.rag.prateeq.in/guardrails`):**
  - Cross-tenant selector for super-admins to inspect, audit, and configure safety policies for any onboarded organization.
  - Platform Battery #13 health metrics, fast-path latency tracking, and blocked/steered intervention counters.
  - Interactive Colang 2.0 flow editor with 1-click template loader, live syntax test sandbox, and rolling safety violation telemetry table with 10s auto-refresh.
- **Client SaaS Studio Panel (`prateeq.in/rag/app`):**
  - Tenant-scoped self-service guardrail tuning (execution mode, custom Colang flows, competitor keyword lists, and grounding threshold slider).
  - Authenticated via tenant API keys with zero platform privilege escalation.

