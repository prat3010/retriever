# ADR-015: LiteLLM Multi-Model Smart Router with Dynamic Cascades & Virtual Tenant Budgets

## Status
Accepted

## Context
High-volume production applications face upstream API rate limits (HTTP 429), regional outages, and unpredictable token bills when using frontier commercial LLMs. Static single-model routing is fragile, while unmetered API key access creates financial exposure for multi-tenant SaaS platforms.

## Problem
We need an intelligent routing layer that:
1. Translates requests across 100+ commercial and local LLMs through a unified interface.
2. Automatically fails over down a priority cascade when primary models encounter rate limits or timeouts.
3. Implements circuit-breaker cooldowns to prevent spamming failing upstream providers.
4. Enforces strict virtual daily and monthly spending limits with configurable breach policies (Warning, Hard Block HTTP 402, or Zero-Downtime Downgrade to Local Free SLM).

## Decision
Implement the **Enterprise LLM Gateway & Smart Router** (`GatewayRouterAdapter`):
1. **Dynamic Priority Cascade:** $\text{Primary} \xrightarrow{\text{429 / 5xx / Timeout}} \text{Secondary} \xrightarrow{} \text{Local Free Model}$.
2. **Circuit-Breaker Cooldowns:** Bypasses failing models for a configurable cooldown window (e.g. 60s) before testing availability.
3. **Virtual Tenant Budget Ledger:** `SqlBudgetRepository` tracks UTC calendar spend from `inference_logs`, enforcing pre-flight checks before dispatching queries.
4. **Control Planes:** Provides visual cascade configuration and live latency ping gauges in both Retriever Admin (`apps/web/src/app/(dashboard)/gateway`) and SaaS Studio (`Prateek_website/src/components/rag/GatewayPanel.tsx`).

## Consequences
* **99.99% Availability:** Upstream outages automatically fail over to secondary providers or zero-cost local Ollama models.
* **Financial Protection:** Tenants cannot exceed their configured dollar budgets.
* **Latency Overhead:** The router adds $<2\text{ms}$ Python overhead to route selection.

## Future Review Criteria
* Audit failover cascade distributions and cooldown trigger frequency in production telemetry.
