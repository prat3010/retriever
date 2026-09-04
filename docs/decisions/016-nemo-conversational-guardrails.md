# ADR-016: NVIDIA NeMo Conversational Guardrails & Colang State Runtime

**Status:** Accepted  
**Date:** 2026-09-04  
**Deciders:** Core Engineering Team  
**Consulted:** Solutions Architects, Security Operations  
**Informed:** Platform Users  

---

## 1. Context and Problem Statement

Retriever previously relied on Llama Guard 3 (`Milestone 40 / 85.1`) for content moderation and simple regex pattern matching for PII redaction. While effective for one-shot safety classification, this approach suffered from fundamental enterprise limitations:
- **No Conversational Flow Steering:** The platform could not guide dialogue down predefined business paths (e.g., politely redirecting users away from off-topic subjects back to technical documentation).
- **Prompt Sensitivity & Non-Determinism:** Attempting to control conversational scope via system prompts alone frequently failed under adversarial pressure or resulted in unpredictable model drift.
- **Heavy Computational Overhead:** Running full Llama Guard 3 inference on every single streaming query adds 80ms–200ms latency, degrading real-time user experience.

The platform required a programmable, deterministic, low-latency conversational control layer with sub-20ms fast-path screening and human-readable policy syntax.

---

## 2. Decision Drivers

- **Deterministic Business Policy:** Enterprise clients must be able to specify strict dialogue constraints in human-readable Colang (`.co`) without retraining or fine-tuning models.
- **Latency Efficiency:** Fast-path input safety screening must execute in $<20\text{ms}$ concurrently with vector embedding generation to prevent TTFT degradation.
- **Zero-Dependency Resilience:** The runtime must operate reliably across cloud VPS and developer environments without failing on missing heavy C++ or CUDA wheels.
- **Multi-Tenancy Isolation:** Every tenant must be capable of editing custom Colang definitions, competitor registries, and grounding thresholds independently.
- **Platform Battery Registration:** NeMo Guardrails must be formalized as Battery #13 in `BatteryService` and integrated into SaaS Studio.

---

## 3. Considered Options

1. **Option 1: Rely solely on System Prompts:** Handcraft detailed negative constraints in system prompt templates.
2. **Option 2: Native Heavy NeMo Guardrails Wheel (`nemoguardrails` with full C++ extensions):** Bind directly to the official NVIDIA package.
3. **Option 3: Dual-Stage Architecture with Pure Python Colang Interpreter:** Implement an authentic, zero-dependency Colang state machine and fast-path regex heuristic scanner conforming strictly to NVIDIA NeMo syntax, with optional binding to native wheels if present.

---

## 4. Decision Outcome

**Chosen Option:** **Option 3 (Dual-Stage Architecture with Pure Python Colang Interpreter)**.

### Rationale:
- **Zero Deployment Friction:** Eliminates brittle binary compilation requirements on lightweight VPS instances (such as Oracle Ampere AArch64) while providing identical Colang flow parsing and dialogue steering.
- **Sub-20ms Latency:** Fast-path input regex scanning executes in $\sim 3.5\text{ms}$, allowing immediate rejection of blatant jailbreaks before allocating embedding or LLM compute.
- **Hexagonal Boundary Conformance:** Domain abstractions (`src/domain/abstractions/guardrails.py`) remain completely pure with zero framework imports, perfectly satisfying architectural conformance tests.

---

## 5. Consequences

### Positive:
- Blatant prompt injections and system extraction attacks are rejected in $<20\text{ms}$ with zero LLM token consumption.
- Tenants can define custom business boundaries using simple `.co` files (e.g. competitor shielding, off-topic steering, discount protection).
- SaaS Studio gains an interactive safety simulator and real-time violation audit stream.
- Formally cataloged as Platform Battery #13 in `BatteryService`.

### Negative / Trade-offs:
- Advanced semantic entailment in `strict_factual` mode requires token containment analysis, adding $\sim 5\text{ms} - 8\text{ms}$ post-generation overhead.
- Very complex nested Colang branching flows require valid syntax; syntax errors in user-entered `.co` files must be handled gracefully with fallbacks.
