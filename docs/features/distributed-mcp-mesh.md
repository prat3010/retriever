# Distributed Model Context Protocol (MCP) Mesh & Agent Federation

**Milestone:** M115 (`v1.5.0-alpha1`)  
**System Layer:** Tool Protocols & Distributed Multi-Agent Systems  
**Platform Battery:** #30 (`distributed_mcp_mesh`)  
**Architecture:** JSON-RPC 2.0 / SSE + Decentralized Peer Topology + HMAC-SHA256 Mutual Trust + Recursive ReAct Delegation

---

## 1. Overview

Milestone 115 introduces **Platform Battery #30 (`distributed_mcp_mesh`)**, evolving Retriever from a single-instance MCP server into a **decentralized, multi-cluster MCP tool mesh and cross-cluster agent federation network**.

This enables sovereign AI agents to:
- Dynamically discover MCP tools advertised across remote clusters.
- Execute tools with lowest-latency peer routing policies.
- Securely communicate over zero-trust boundaries using HMAC-SHA256 cryptographic trust envelopes with sliding-window nonce deduplication.
- Delegate complex sub-goals to specialist sub-agents on remote sovereign enclaves while terminating circular delegation loops deterministically.

---

## 2. API Endpoints Reference

| Endpoint | Method | Purpose |
|:---|:---:|:---|
| `/v1/mesh/status` | `GET` | Battery #30 health check, node counts, and topology overview |
| `/v1/mesh/nodes` | `GET` | List active peer nodes and their advertised tool manifests |
| `/v1/mesh/nodes/register` | `POST` | Register or update an edge enclave or remote cluster peer node |
| `/v1/mesh/nodes/heartbeat` | `POST` | Process peer heartbeat and update latency metrics |
| `/v1/mesh/nodes/{node_id}` | `DELETE` | Remove a peer node from the mesh topology |
| `/v1/mesh/tools` | `GET` | Aggregated catalog of discoverable tools across all online nodes |
| `/v1/mesh/tools/execute` | `POST` | Route and execute a tool call locally or via remote authenticated RPC |
| `/v1/mesh/federation/delegate` | `POST` | Submit a cross-cluster agent delegation request with loop guards |
| `/v1/mesh/federation/tasks/{id}` | `GET` | Retrieve audit record and status for a delegated task |

---

## 3. Cryptographic Trust Envelope

Inter-cluster tool execution and agent delegation payloads are authenticated using canonicalized HMAC-SHA256 signatures:

```json
{
  "sender_cluster_id": "cluster_us_primary",
  "receiver_cluster_id": "cluster_eu_enclave",
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "timestamp": 1789456200.1245,
  "nonce": "a3f8c1b2d4e5f6a7b8c9d0e1f2a3b4c5",
  "signature": "3a7b9c1d5e2f4a6b8c0d2e4f6a8b0c2d4e6f8a0b2c4d6e8f0a2b4c6d8e0f2a4b",
  "payload_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

- **Replay Protection:** Nonces are cached for 60 seconds; repeated nonces trigger immediate `TrustVerificationError`.
- **Clock Skew:** Requests with $|t_{\text{now}} - t_{\text{msg}}| > 60\text{s}$ are rejected.

---

## 4. Circular Loop Breaker & Recursion Limit

Cross-cluster delegations maintain an immutable `visited_clusters` array:
- If a target cluster appears in `visited_clusters`, a `FederationLoopError` halts execution immediately.
- If `len(visited_clusters) >= max_depth` (default 2, maximum 3), delegation is terminated safely.

---

## 5. Client SDK Usage

### TypeScript (`@prat3010/retriever-client`)
```typescript
import { RetrieverClient } from "@prat3010/retriever-client";

const client = new RetrieverClient({
  apiKey: "ret_live_...",
  tenantId: "tn_enterprise_corp",
  baseUrl: "http://localhost:8000",
});

// 1. Inspect mesh status
const meshStatus = await client.getMeshStatus();
console.log(`Mesh online: ${meshStatus.active_nodes} clusters, ${meshStatus.total_mesh_tools} tools`);

// 2. Execute distributed tool with lowest latency routing
const toolResult = await client.executeMeshTool("gdpr_residency_audit", { scope: "storage" }, "cluster_eu_enclave", "lowest_latency");

// 3. Delegate reasoning to remote specialist agent
const delegation = await client.delegateFederatedTask({
  target_cluster_id: "cluster_eu_enclave",
  intent: "Verify sovereign data residency for European storage nodes",
  target_agent_role: "forensic_auditor",
  max_depth: 2,
});
console.log("Delegation synthesis:", delegation.synthesis);
```

### Python (`retriever-python`)
```python
from retriever import RetrieverClient

client = RetrieverClient(api_key="ret_live_...", tenant_id="tn_enterprise_corp")

# Inspect mesh
status = client.get_mesh_status()
print(f"Total tools across mesh: {status.total_mesh_tools}")

# Delegate task to remote cluster agent
delegation = client.delegate_federated_task(
    target_cluster_id="cluster_eu_enclave",
    intent="Audit compliance with sovereign data residency bounds",
    target_agent_role="forensic_auditor",
)
print("Synthesis:", delegation.synthesis)
```
