---
id: Retriever_API_v1_mesh
title: "API Specification: Distributed Model Context Protocol (MCP) Mesh & Agent Federation (/v1/mesh)"
tier: 4_api_gateway
platform: retriever
tags:
  - api/mesh
  - mcp/mesh
  - federation/react
  - platform/retriever
blast_radius: HIGH
security_auth: BEARER_JWT_OR_TENANT_HEADER
invariants:
  - "Inter-cluster tool execution and delegation MUST verify signed HMAC-SHA256 TrustEnvelopes."
  - "Cross-cluster agent delegation MUST abort on circular paths with FederationLoopError."
  - "Stale nodes inactive for >120s MUST be evicted from routing candidate pools."
---

# API Specification: Distributed Model Context Protocol (MCP) Mesh & Agent Federation (`/v1/mesh`)

#api #mesh #mcp #federation #react #zero_trust #retriever

> **Authoritative REST and JSON-RPC API specification for the Distributed Model Context Protocol (MCP) Mesh, peer node registration, latency-weighted tool routing, and cross-cluster agent federation (Platform Battery #30).**

---

## 1. Overview & Architecture

The Distributed MCP Mesh exposes standard REST endpoints mounted at `/v1/mesh/*` that allow multiple Retriever instances, regional cloud deployments, and edge micro-enclaves to federate their tool registries and cognitive sub-agent reasoning loops.

```text
  [ Client / Parent Agent ]                 [ Local Retriever Node ]               [ Remote Peer Cluster ]
              │                                        │                                      │
              │ 1. POST /v1/mesh/tools/execute         │                                      │
              ├───────────────────────────────────────►│ 2. Resolve Route (Lowest Latency)    │
              │                                        ├─────────────────────────────────────►│
              │                                        │    (Signed HMAC-SHA256 Envelope)     │
              │                                        │◄─────────────────────────────────────┤
              │◄───────────────────────────────────────┤    McpToolExecutionResult            │
              │    McpToolExecutionResult              │                                      │
```

---

## 2. Endpoints Reference

### 2.1 Get Mesh Topology & Status
* **Endpoint:** `GET /v1/mesh/status`
* **Auth:** Optional / Public Health
* **Description:** Retrieves real-time mesh health, count of active and total nodes, registered tools across clusters, and current default routing policy.
* **Response (200 OK):**
```json
{
  "battery_id": "distributed_mcp_mesh",
  "status": "active",
  "total_nodes": 3,
  "active_nodes": 3,
  "total_mesh_tools": 14,
  "routing_policy": "local_first",
  "nodes": [
    {
      "node_id": "node_seed_primary",
      "cluster_id": "cluster_alpha",
      "hostname": "127.0.0.1",
      "port": 8000,
      "role": "seed_gateway",
      "status": "online",
      "latency_ms": 0.0,
      "advertised_tools": ["hybrid_search", "document_reader", "web_search"],
      "last_heartbeat": 1773539400.0,
      "metadata": {}
    }
  ]
}
```

---

### 2.2 List Mesh Peer Nodes
* **Endpoint:** `GET /v1/mesh/nodes`
* **Query Parameters:**
  * `online_only` (bool, default `true`): Filter to only active, reachable nodes with non-expired leases (< 120s).
* **Response (200 OK):**
```json
[
  {
    "node_id": "node_beta_gpu",
    "cluster_id": "cluster_beta",
    "hostname": "10.0.1.15",
    "port": 8000,
    "role": "sovereign_node",
    "status": "online",
    "latency_ms": 12.4,
    "advertised_tools": ["vllm_generate", "lora_adapter_swap"],
    "last_heartbeat": 1773539410.5,
    "metadata": {"gpu": "A100-80GB"}
  }
]
```

---

### 2.3 Register Peer Node Lease
* **Endpoint:** `POST /v1/mesh/nodes/register`
* **Description:** Registers a new or existing node in the cluster directory and activates its 120-second lease.
* **Request Body:**
```json
{
  "node_id": "node_gamma_voice",
  "cluster_id": "cluster_gamma",
  "hostname": "10.0.2.20",
  "port": 8000,
  "role": "remote_peer",
  "status": "online",
  "latency_ms": 8.1,
  "advertised_tools": ["voice_stream_synthesizer"],
  "metadata": {"webrtc": true}
}
```
* **Response (200 OK):** Returns the registered `MeshPeerNode` representation.

---

### 2.4 Send Node Heartbeat Ping
* **Endpoint:** `POST /v1/mesh/nodes/heartbeat?node_id=node_gamma_voice&latency_ms=7.9`
* **Description:** Renews the 120-second lease for the node and updates its observed roundtrip latency.
* **Response (200 OK):**
```json
{
  "status": "renewed",
  "node_id": "node_gamma_voice",
  "last_heartbeat": 1773539430.0
}
```

---

### 2.5 Aggregate Discoverable Tools
* **Endpoint:** `GET /v1/mesh/tools`
* **Description:** Aggregates all unique MCP tool definitions advertised across all currently reachable peer nodes in the mesh.
* **Response (200 OK):** Array of standard `McpToolDefinition` objects.

---

### 2.6 Execute Distributed Tool Call
* **Endpoint:** `POST /v1/mesh/tools/execute?policy=lowest_latency`
* **Query Parameters:**
  * `policy` (string, default `local_first`): Routing policy (`local_first`, `lowest_latency`, `failover`).
* **Request Body:**
```json
{
  "tool_name": "hybrid_search",
  "arguments": {
    "query": "cryptographic memory sealing",
    "top_k": 3
  },
  "tenant_id": "tn_client_acme",
  "call_id": "call_12345"
}
```
* **Response (200 OK):**
```json
{
  "content": [
    {
      "type": "text",
      "text": "Sealed memory enclaves utilize AES-256-GCM with hardware-rooted keys..."
    }
  ],
  "is_error": false,
  "meta": {
    "routed_node": "node_seed_primary",
    "cluster_id": "cluster_alpha",
    "execution_mode": "local_mesh"
  }
}
```

---

### 2.7 Delegate Federated Agent Task
* **Endpoint:** `POST /v1/mesh/federation/delegate`
* **Description:** Delegates an autonomous sub-goal from a parent ReAct agent to a specialist role on a remote cluster. Enforces circular loop breaking and depth limits.
* **Request Body:**
```json
{
  "delegation_id": "del_001",
  "source_cluster_id": "cluster_alpha",
  "target_cluster_id": "cluster_delta",
  "tenant_id": "tn_client_acme",
  "target_agent_role": "compliance_auditor",
  "intent": "Verify GDPR erasure certificate for user identity USR-9812",
  "context_scope": {
    "domain": "compliance",
    "regulation": "GDPR_ARTICLE_17"
  },
  "max_depth": 3,
  "visited_clusters": ["cluster_alpha"]
}
```
* **Response (200 OK):**
```json
{
  "delegation_id": "del_001",
  "status": "completed",
  "source_cluster_id": "cluster_alpha",
  "target_cluster_id": "cluster_delta",
  "tenant_id": "tn_client_acme",
  "synthesis": "Federated COMPLIANCE_AUDITOR on cluster 'cluster_delta' successfully resolved sub-intent...",
  "tool_trace_summary": [
    {
      "tool": "enclave_policy_evaluator",
      "status": "success"
    }
  ],
  "execution_latency_ms": 14.8,
  "signature": "8fbc91...",
  "error_message": null
}
```
* **Error Response (409 Conflict):**
```json
{
  "detail": "Circular delegation loop detected: cluster 'cluster_alpha' already in visited chain ['cluster_alpha']."
}
```

---

## 3. SDK Code Usage Examples

### TypeScript (`@prat3010/retriever-client`)
```typescript
import { RetrieverClient } from '@prat3010/retriever-client';

const client = new RetrieverClient({
  baseUrl: 'https://rag.prateeq.in',
  apiKey: process.env.RETRIEVER_API_KEY!,
});

// 1. Inspect active mesh nodes
const status = await client.getMeshStatus();
console.log(`Active mesh nodes: ${status.active_nodes}`);

// 2. Delegate a federated sub-goal with anti-loop protection
const response = await client.delegateFederatedTask({
  delegation_id: `del_${Date.now()}`,
  source_cluster_id: 'cluster_alpha',
  target_cluster_id: 'cluster_beta',
  tenant_id: 'tn_demo',
  target_agent_role: 'vllm_synthesizer',
  intent: 'Synthesize low-latency summary of technical whitepaper',
  context_scope: { domain: 'engineering' },
  max_depth: 3,
  visited_clusters: ['cluster_alpha'],
});
console.log(`Federation synthesis: ${response.synthesis}`);
```

### Python (`retriever-python`)
```python
import asyncio
from retriever import AsyncRetrieverClient

async def main():
    async with AsyncRetrieverClient(
        base_url="https://rag.prateeq.in",
        api_key="YOUR_API_KEY",
    ) as client:
        # Route a tool invocation across the lowest-latency online node
        result = await client.execute_mesh_tool(
            tool_name="hybrid_search",
            arguments={"query": "Hardware micro-enclave memory sealing", "top_k": 3},
            tenant_id="tn_demo",
            policy="lowest_latency",
        )
        print(f"Result from node: {result.meta.get('routed_node')}")

asyncio.run(main())
```
