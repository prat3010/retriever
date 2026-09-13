# ADR-025: Autonomous Multi-Turn ReAct Tool Loop & Self-Healing Execution Engine

**Status:** Accepted  
**Date:** 2026-09-14  
**Deciders:** Principal Cognitive Systems Architects, AI Agents Lead, Platform Reliability Engineers  
**Consulted:** SaaS Studio Team, Security & Sandboxing Officers  
**Informed:** Enterprise Clients, Developer Ecosystem  

---

## 1. Context and Problem Statement

Prior to Milestone 104, Retriever supported single-step tool calling and DAG-based workflow executions (Milestone 91), as well as edge swarm gossip coordination (Milestone 102). However, interactive cognitive reasoning was constrained:
1. **Single-Shot Tool Execution:** Users prompting the model for tasks requiring multi-step retrieval, parameter deduction, or exploratory synthesis were restricted to a single model inference with speculative tool execution.
2. **Fragility to Transient Tool Failures:** When an invoked tool returned a transient runtime error (e.g. database connection timeout, malformed payload arguments, or key lookup mismatch), the system immediately errored out to the user rather than allowing the model to inspect the exception, adjust arguments, and self-heal.
3. **Infinite Invocation Loops:** Without cryptographic signature fingerprinting, generative models frequently entered infinite repetitive loops calling the identical tool with identical parameters, exhausting token budgets and hanging user sessions.
4. **Lack of Transparent Streaming Observability:** Existing endpoints either returned monolithic results or raw token streams without intermediate thought-action-observation lifecycle tracing.

To resolve these limitations, Retriever introduced **Platform Battery #23: Autonomous Multi-Turn ReAct Tool Loop & Self-Healing Execution Engine** (`v0.89.0`, Milestone 104), opening **Phase N: Autonomous Cognitive Agents & Self-Healing Swarms**.

---

## 2. Decision Drivers

- **Pure Hexagonal Domain Abstractions:** The cyclic agent state machine and events must reside purely in `src/domain/abstractions/react.py` with zero framework or database imports.
- **Strict Cyclic State Transitions:** Enforce predictable transitions: $\text{REASONING} \to \text{SELECTING\_TOOL} \to \text{EXECUTING\_BATTERY} \to \text{OBSERVING} \to \text{EVALUATING\_COMPLETION}$.
- **Cryptographic Anti-Loop Circuit Breaker:** Track tool call signatures via SHA-256 hashes of `(tool_name, sorted_json_arguments)`. If repetition count $C \ge 2$, immediately trip the circuit breaker and inject advisory instructions to the model.
- **Self-Healing Exception Interception:** Catch all tool execution exceptions, format them as structured observations with actionable self-healing guidance, and allow the model to autonomously adapt and retry.
- **Deterministic Hard Safety Guards:** Enforce maximum turn cap ($\le 8$) and execution timeout ($\le 30.0\text{s}$) to prevent unbounded latency.
- **Real-Time SSE Streaming:** Expose an async generator emitting typed Server-Sent Events (`thought`, `tool_start`, `tool_done`, `self_healing`, `circuit_breaker`, `final_answer`, `[DONE]`) consumed seamlessly by the web studio.

---

## 3. Considered Options

### Option 1: External Framework Integration (LangChain / CrewAI / AutoGen)
- *Pros:* Off-the-shelf abstractions for agentic loops.
- *Cons:* Heavy external dependencies, bloated runtime footprint, breaks Hexagonal architecture boundaries, untrusted licensing/telemetry hooks, non-deterministic error recovery.

### Option 2: Stateless Client-Side Prompt Chaining
- *Pros:* No backend state machine modifications required.
- *Cons:* Exposes tool execution keys and execution secrets to frontend clients; excessive network roundtrips over WAN; zero centralized loop safety or anti-loop tripwires.

### Option 3: Hexagonal Pure ReAct Engine with Signature Hash Circuit Breaker & SSE Streaming (Chosen)
- *Pros:*
  - Zero external agent framework bloat: 100% pure Python domain abstractions.
  - Sub-millisecond state transitions and deterministic signature hashing.
  - Transparent error recovery with autonomous parameter adjustment.
  - Stream-first design emitting structured SSE event frames for live UX observability.
  - Complete multi-tenant isolation adhering to `verify_tenant_or_admin` security rules.

---

## 4. Decision Outcome

We selected **Option 3**. The architecture was implemented across four decoupled layers:

1. **Domain Abstractions (`src/domain/abstractions/react.py`):**
   - `ReActState`: Enum tracking execution phases (`REASONING`, `SELECTING_TOOL`, `EXECUTING_BATTERY`, `OBSERVING`, `EVALUATING_COMPLETION`, `COMPLETED`, `CIRCUIT_BREAKER_TRIPPED`, `ERROR`).
   - `ReActEventType`: Stream event tags (`thought`, `tool_start`, `tool_done`, `self_healing`, `circuit_breaker`, `final_answer`, `error`, `done`).
   - `ReActEvent`: Pure event model with monotonic turn counter and ISO timestamps.
   - `ReActLoopProtocol`: Abstract protocol for cyclic execution.

2. **Execution Engine (`src/domain/agentic/react_engine.py`):**
   - Implements `execute_react_loop` asynchronous generator yielding `ReActEvent` instances.
   - Manages SHA-256 signature frequency tracking for repeated tool calls.
   - Intercepts tool execution errors and marks `self_healing_applied = True`.
   - Halts on turn exhaustion or timeout, yielding informative synthesis.

3. **API & Routing (`src/routers/agentic.py`):**
   - Exposes `POST /v1/tenants/{tenantId}/agentic/stream` returning `text/event-stream`.
   - Enforces `verify_tenant_or_admin` dependency ensuring authorized multi-tenant access.

4. **Frontend Studio (`Prateek_website`):**
   - Mode toggle ("💬 Direct RAG" vs "⚡ ReAct Agent") in `ChatPanel.tsx`.
   - Collapsible live trace accordion rendering thoughts, tool invocations, results, and self-healing/circuit-breaker badges.

---

## 5. Consequences

### Positive
- Autonomous multi-step problem solving without human micro-management.
- High resilience: transient tool and parameter errors are autonomously resolved.
- Hard safety invariants prevent runaway API costs and infinite loops.
- 100% test coverage with automated Hexagonal AST purity assertions.

### Negative / Trade-offs
- Multi-turn loops consume more model inference tokens than single-turn RAG queries.
- Requires robust timeout and cancellation signal handling on client disconnects.
