# 0030. Distributed Model Context Protocol (MCP) Mesh & Agent Federation

Date: 2026-09-15  
Status: Accepted  
Deciders: Prateek Sharma, Platform Architecture Team  
Milestone: Milestone 115 (`v1.5.0-alpha1`)  
Platform Battery: #30 (`distributed_mcp_mesh`)

---

## Context & Problem Statement

Prior to Milestone 115, Retriever exposed its platform capabilities (hybrid search, ColBERT reranking, RLM REPL, guardrails) via a single-instance Model Context Protocol (MCP) server (Milestone 103, Battery #23) connecting directly to local IDEs (Claude Desktop, Cursor). 

However, in multi-cluster, multi-cloud, and edge enterprise deployments:
1. **Sovereign Boundaries:** Enterprise data cannot be centralized into a single cluster without violating data sovereignty laws (e.g., EU GDPR Chapter V or financial micro-enclaves).
2. **Specialized Regional Capabilities:** Certain specialist tools (e.g., local legal compliance auditors, hardware-rooted SGX micro-enclaves, or edge SQLite CRDT sync) only exist on specific sovereign nodes.
3. **Circular Delegation Hazards:** When autonomous multi-agent cognitive loops (ReAct / Swarm Quorum) delegate sub-goals across cluster boundaries, naive recursion can lead to infinite ping-pong delegation loops, consuming unbounded compute and tokens.
4. **Zero-Trust Cross-Cluster Transport:** Unauthenticated RPC calls across sovereign boundaries create critical security vulnerabilities.

---

## Decision Drivers

- **Standardization over Proprietary RPC:** Must use standard Model Context Protocol (JSON-RPC 2.0 / SSE) tool schemas.
- **Cryptographic Trust Proofs:** Inter-cluster communication must enforce mutual authentication without relying purely on network perimeter firewalls.
- **Strict Anti-Loop Recursion Termination:** A formal, deterministic circuit breaker must detect and reject circular delegations.
- **Tenant Isolation Invariant:** Inter-cluster delegations must strictly preserve `tenant_id` context and abort on any cross-tenant leakage.
- **Zero-Toy Invariant:** All routing, trust validation, and delegation logic must be authentic, production-grade domain logic with zero synthetic facades.

---

## Considered Options

1. **Option 1: Centralized Service Mesh (Istio / Envoy):** Heavy infrastructure dependency requiring complex sidecar proxies and Kubernetes clusters. Violates Retriever's lightweight single-binary & edge deployment philosophy.
2. **Option 2: Proprietary Multi-Agent Socket Protocol:** Bespoke message format that creates vendor lock-in and cannot be consumed by external tools or frontier IDEs.
3. **Option 3: Decentralized MCP Tool Mesh with Cryptographic Trust Envelopes (Chosen):** Pure domain `McpMeshService` and `AgentFederationService` leveraging standard MCP JSON-RPC contracts, HMAC-SHA256 request signing with sliding-window nonce deduplication, and recursion-bounded delegation chains.

---

## Decision Outcome

Chosen Option: **Option 3**.

### Architectural Foundation

1. **Platform Battery #30 Registration:**
   - Cataloged `distributed_mcp_mesh` under `SYSTEM_EXTENSIBILITY` in `BatteryService`.
   - Health check endpoint: `/v1/mesh/status`.

2. **Decentralized Node Catalog & Latency-Weighted Routing:**
   - Pure domain `McpMeshService` tracks registered peer nodes (`SEED_GATEWAY`, `SOVEREIGN_NODE`, `EDGE_ENCLAVE`, `REMOTE_PEER`).
   - Dynamic capability advertisement: aggregates tools from all online nodes.
   - Heartbeat leasing: nodes with last heartbeat $> 120$s are automatically marked `UNREACHABLE`.
   - Routing policies (`LOCAL_FIRST`, `LOWEST_LATENCY`, `ROUND_ROBIN`, `FAILOVER`).

3. **HMAC-SHA256 Cryptographic Trust Envelopes:**
   - Every inter-cluster tool invocation and delegation carries a canonicalized `TrustEnvelope`:
     $$\text{Signature} = \text{HMAC-SHA256}(K, \text{sender} \parallel \text{receiver} \parallel \text{tenant} \parallel \text{nonce} \parallel \text{timestamp} \parallel \text{payload\_hash})$$
   - Clock skew enforced $\le 60.0$s.
   - Nonce replay cache prevents replay attacks.

4. **Circular Delegation Termination:**
   - `FederatedDelegationRequest` tracks `visited_clusters: list[str]` and `max_depth: int` (default 2, cap 3).
   - If `target_cluster_id in visited_clusters`, execution raises `FederationLoopError` immediately.
   - If `len(visited_clusters) >= max_depth`, execution raises `FederationLoopError`.

5. **ReAct Tool Registry Integration:**
   - Exposes `delegate_to_federated_agent` tool into the local `ToolRegistry` so autonomous agents can naturally delegate sub-intents to sovereign clusters.

---

## Consequences

- **Positive:** Full-duplex sovereign agent delegation across multi-cloud and edge nodes without data residency breaches.
- **Positive:** Reaches 30 production batteries in Retriever.
- **Positive:** Decoupled SDKs (`@prat3010/retriever-client` and `retriever-python`) provide seamless cross-cluster control.
- **Negative / Operational:** Multi-cluster operators must share the cluster secret key or provision mutual TLS certificates across nodes.
