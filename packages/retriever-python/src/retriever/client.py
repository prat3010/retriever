"""Official Python Client for Retriever Enterprise Cognitive Engine."""

from collections.abc import AsyncIterator, Iterator
import json
from pathlib import Path
from typing import Any

import httpx

from retriever.exceptions import (
    ApiRequestError,
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitExceededError,
)
from retriever.models import (
    AutoscalingEventDTO,
    AutoscalingPolicyDTO,
    CognitiveMemoryNode,
    ConnectorConfigDTO,
    ConnectorManifestDTO,
    ConnectorSyncResponseDTO,
    DocumentResponse,
    EnclaveEvidence,
    FederatedDelegationResponseDTO,
    McpToolDefinition,
    MeshPeerNodeDTO,
    MeshStatusSummaryDTO,
    MultimodalGraphResponseDTO,
    RaftConsensusStatus,
    ReActEvent,
    ScatterGatherQuery,
    ScatterGatherResponse,
    SchematicDiagramDTO,
    SearchResponse,
    SearchResultItem,
    ShardMutationRequest,
    ShardMutationResponse,
    ShardRebalancePlan,
    ShardTopologyResponse,
    SwarmDebateResult,
)


def _handle_error(response: httpx.Response) -> None:
    if response.status_code == 401:
        raise AuthenticationError("Invalid or missing API key.")
    if response.status_code == 403:
        raise PermissionDeniedError("Tenant isolation boundary violation or forbidden access.")
    if response.status_code == 404:
        raise NotFoundError("Requested resource not found.")
    if response.status_code == 429:
        raise RateLimitExceededError("Rate limit or token quota exceeded.")
    if response.is_error:
        raise ApiRequestError(response.status_code, response.text, response.text)


class RetrieverClient:
    """Synchronous Client for Retriever Cognitive Engine."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000",
        tenant_id: str = "00000000-0000-0000-0000-000000000001",
        user_id: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.tenant_id = tenant_id
        self.user_id = user_id
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
        }
        if self.user_id:
            headers["X-User-ID"] = self.user_id

        self._client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
        )

    def __enter__(self) -> "RetrieverClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    # ── Search & Retrieval (Batteries #1, #2, #3) ────────────────────────────

    def search(
        self,
        query: str,
        limit: int = 10,
        enable_colbert_rerank: bool = True,
        hybrid_alpha: float = 0.7,
        filters: list[dict[str, Any]] | None = None,
        tags: list[str] | None = None,
    ) -> SearchResponse:
        payload = {
            "query": query,
            "limit": limit,
            "enable_hybrid": True,
            "hybrid_alpha": hybrid_alpha,
            "reranker_engine": "colbert" if enable_colbert_rerank else "cohere",
            "filters": filters or [],
            "tags": tags or [],
        }
        resp = self._client.post(
            f"/v1/tenants/{self.tenant_id}/search",
            json=payload,
        )
        _handle_error(resp)
        data = resp.json()
        items = [
            SearchResultItem(
                chunk_id=item.get("chunkId") or item.get("chunk_id", ""),
                document_id=item.get("documentId") or item.get("document_id", ""),
                content=item["content"],
                score=item["score"],
                metadata=item.get("metadata", {}),
            )
            for item in data.get("results", [])
        ]
        return SearchResponse(
            results=items,
            total=data.get("total", len(items)),
            latency_ms=data.get("latency_ms", 0.0),
            strategy_used=data.get("strategy_used", "hybrid"),
            cached=data.get("cached", False),
        )

    # ── Documents (Battery #4) ───────────────────────────────────────────────

    def upload_document(
        self,
        file_path_or_bytes: str | Path | bytes,
        filename: str,
        mime_type: str = "text/markdown",
    ) -> DocumentResponse:
        if isinstance(file_path_or_bytes, (str, Path)):
            with open(file_path_or_bytes, "rb") as f:
                content = f.read()
        else:
            content = file_path_or_bytes

        files = {"file": (filename, content, mime_type)}
        resp = self._client.post(f"/v1/tenants/{self.tenant_id}/documents", files=files)
        _handle_error(resp)
        return DocumentResponse.model_validate(resp.json())

    def list_documents(self, limit: int = 50) -> list[DocumentResponse]:
        resp = self._client.get(f"/v1/tenants/{self.tenant_id}/documents?limit={limit}")
        _handle_error(resp)
        data = resp.json()
        items = data if isinstance(data, list) else data.get("items", [])
        return [DocumentResponse.model_validate(d) for d in items]

    # ── ReAct Streaming Chat (Battery #24) ────────────────────────────────────

    def chat_stream(
        self,
        session_id: str,
        message: str,
    ) -> Iterator[ReActEvent]:
        payload = {
            "content": message,
            "stream": True,
            "agentic_mode": True,
        }
        with self._client.stream(
            "POST",
            f"/v1/tenants/{self.tenant_id}/chat/sessions/{session_id}/messages",
            json=payload,
            headers={"Accept": "text/event-stream"},
        ) as response:
            _handle_error(response)
            for line in response.iter_lines():
                line = line.strip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line.removeprefix("data:").strip()
                if data_str == "[DONE]":
                    break
                try:
                    parsed = json.loads(data_str)
                    yield ReActEvent.model_validate(parsed)
                except Exception:
                    yield ReActEvent(type="token", content=data_str)

    # ── Cognitive Memory (Battery #25) ───────────────────────────────────────

    def query_memory(self, query: str, limit: int = 5) -> list[CognitiveMemoryNode]:
        resp = self._client.post(
            f"/v1/tenants/{self.tenant_id}/memory/query",
            json={"query": query, "limit": limit},
        )
        _handle_error(resp)
        return [CognitiveMemoryNode.model_validate(m) for m in resp.json()]

    # ── Multi-Agent Swarm Quorum (Battery #26) ────────────────────────────────

    def swarm_debate(
        self,
        task: str,
        roles: list[str] | None = None,
        max_rounds: int = 2,
    ) -> SwarmDebateResult:
        payload = {
            "task": task,
            "roles": roles or ["planner", "auditor", "synthesizer", "skeptic"],
            "max_rounds": max_rounds,
        }
        resp = self._client.post(
            f"/v1/tenants/{self.tenant_id}/swarm/debate",
            json=payload,
        )
        _handle_error(resp)
        return SwarmDebateResult.model_validate(resp.json())

    # ── Universal MCP Protocol (Battery #23) ─────────────────────────────────

    def list_mcp_tools(self) -> list[McpToolDefinition]:
        resp = self._client.get("/v1/mcp/tools")
        _handle_error(resp)
        data = resp.json()
        tools = data.get("tools", [])
        return [McpToolDefinition.model_validate(t) for t in tools]

    # ── Micro-Enclave Attestation (Battery #21) ───────────────────────────────

    def get_enclave_attestation(self, nonce: str | None = None) -> EnclaveEvidence:
        resp = self._client.post(
            f"/v1/tenants/{self.tenant_id}/enclave/attestation",
            json={"challenge_nonce": nonce},
        )
        _handle_error(resp)
        return EnclaveEvidence.model_validate(resp.json())


    # ── Community Connectors & CDC Pipeline (Battery #27) ──────────────────────

    def list_connector_manifests(self) -> list[ConnectorManifestDTO]:
        resp = self._client.get("/v1/admin/connectors/manifests")
        _handle_error(resp)
        data = resp.json()
        return [ConnectorManifestDTO.model_validate(m) for m in data.get("manifests", [])]

    def list_connectors(self) -> list[ConnectorConfigDTO]:
        resp = self._client.get(f"/v1/admin/tenants/{self.tenant_id}/connectors")
        _handle_error(resp)
        return [ConnectorConfigDTO.model_validate(c) for c in resp.json()]

    def create_connector(
        self,
        name: str,
        connector_type: str,
        configuration: dict[str, Any] | None = None,
        sync_interval_minutes: int = 1440,
    ) -> ConnectorConfigDTO:
        payload = {
            "name": name,
            "connector_type": connector_type,
            "configuration": configuration or {},
            "sync_interval_minutes": sync_interval_minutes,
        }
        resp = self._client.post(
            f"/v1/admin/tenants/{self.tenant_id}/connectors",
            json=payload,
        )
        _handle_error(resp)
        return ConnectorConfigDTO.model_validate(resp.json())

    def trigger_connector_sync(self, connector_id: str) -> ConnectorSyncResponseDTO:
        resp = self._client.post(
            f"/v1/admin/tenants/{self.tenant_id}/connectors/{connector_id}/sync"
        )
        _handle_error(resp)
        return ConnectorSyncResponseDTO.model_validate(resp.json())

    # ── Multimodal Vision GraphRAG & Schematic Ingestion (Battery #29) ─────────

    def extract_schematic_text(
        self,
        content: str,
        filename: str = "architecture.svg",
        document_id: str | None = None,
    ) -> SchematicDiagramDTO:
        payload = {"content": content, "filename": filename, "document_id": document_id}
        resp = self._client.post(
            f"/v1/tenants/{self.tenant_id}/vision/schematic/extract-text",
            json=payload,
        )
        _handle_error(resp)
        return SchematicDiagramDTO.model_validate(resp.json())

    def query_multimodal_graph(
        self,
        entity_query: str,
        max_hops: int = 2,
    ) -> MultimodalGraphResponseDTO:
        payload = {
            "tenant_id": self.tenant_id,
            "entity_query": entity_query,
            "max_hops": max_hops,
            "include_visual_boxes": True,
        }
        resp = self._client.post(
            f"/v1/tenants/{self.tenant_id}/vision/graph/query",
            json=payload,
        )
        _handle_error(resp)
        return MultimodalGraphResponseDTO.model_validate(resp.json())

    def get_document_schematics(self, document_id: str) -> dict[str, Any]:
        resp = self._client.get(f"/v1/tenants/{self.tenant_id}/vision/schematics/{document_id}")
        _handle_error(resp)
        return resp.json()

    def get_multimodal_vision_status(self) -> dict[str, Any]:
        resp = self._client.get("/v1/graph/multimodal/status")
        _handle_error(resp)
        return resp.json()

    def get_voice_stream_url(
        self,
        session_id: str,
        sensitivity: float = 0.65,
        silence_threshold_ms: int = 400,
        voice: str = "neural_natural",
        speed: float = 1.0,
    ) -> str:
        """Returns the full WebSocket URL for full-duplex real-time voice streaming."""
        ws_proto = "wss" if self.base_url.startswith("https") else "ws"
        host = self.base_url.split("://")[-1].rstrip("/")
        return (
            f"{ws_proto}://{host}/v1/tenants/{self.tenant_id}/voice/stream/{session_id}"
            f"?token={self.api_key}&sensitivity={sensitivity}&silence_threshold_ms={silence_threshold_ms}&voice={voice}&speed={speed}"
        )

    # ── Distributed MCP Mesh & Agent Federation (Battery #30 / M115) ──────────

    def get_mesh_status(self) -> MeshStatusSummaryDTO:
        resp = self._client.get("/v1/mesh/status")
        _handle_error(resp)
        return MeshStatusSummaryDTO.model_validate(resp.json())

    def list_mesh_nodes(self, status_filter: str | None = None) -> list[MeshPeerNodeDTO]:
        params = {"status": status_filter} if status_filter else {}
        resp = self._client.get("/v1/mesh/nodes", params=params)
        _handle_error(resp)
        return [MeshPeerNodeDTO.model_validate(n) for n in resp.json()]

    def list_mesh_tools(self) -> list[dict[str, Any]]:
        resp = self._client.get("/v1/mesh/tools")
        _handle_error(resp)
        return resp.json()

    def execute_mesh_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        target_cluster_id: str = "cluster_local",
        policy: str = "local_first",
    ) -> dict[str, Any]:
        payload = {
            "call_id": "call_py_client",
            "tool_name": tool_name,
            "arguments": arguments or {},
            "tenant_id": self.tenant_id,
            "source_cluster_id": "cluster_python_sdk",
            "target_cluster_id": target_cluster_id,
        }
        resp = self._client.post(f"/v1/mesh/tools/execute?policy={policy}", json=payload)
        _handle_error(resp)
        return resp.json()

    def delegate_federated_task(
        self,
        target_cluster_id: str,
        intent: str,
        target_agent_role: str = "forensic_auditor",
        context_scope: dict[str, Any] | None = None,
        max_depth: int = 2,
        visited_clusters: list[str] | None = None,
    ) -> FederatedDelegationResponseDTO:
        payload = {
            "target_cluster_id": target_cluster_id,
            "tenant_id": self.tenant_id,
            "intent": intent,
            "target_agent_role": target_agent_role,
            "context_scope": context_scope or {},
            "max_depth": max_depth,
            "visited_clusters": visited_clusters or [],
        }
        resp = self._client.post("/v1/mesh/federation/delegate", json=payload)
        _handle_error(resp)
        return FederatedDelegationResponseDTO.model_validate(resp.json())

    def get_federated_task_status(self, delegation_id: str) -> FederatedDelegationResponseDTO:
        resp = self._client.get(f"/v1/mesh/federation/tasks/{delegation_id}")
        _handle_error(resp)
        return FederatedDelegationResponseDTO.model_validate(resp.json())

    # ── Autonomous Mesh Dynamic Load-Balancing & Autoscaling (Battery #31 / M116) ──

    def get_mesh_load_metrics(self) -> dict[str, Any]:
        resp = self._client.get("/v1/mesh/load/metrics")
        _handle_error(resp)
        return resp.json()

    def get_autoscaling_events(self, limit: int = 50) -> list[AutoscalingEventDTO]:
        resp = self._client.get(f"/v1/mesh/load/autoscaling/events?limit={limit}")
        _handle_error(resp)
        return [AutoscalingEventDTO.model_validate(e) for e in resp.json()]

    def update_autoscaling_policy(
        self, policy: dict[str, Any] | AutoscalingPolicyDTO
    ) -> AutoscalingPolicyDTO:
        body = policy.model_dump() if isinstance(policy, AutoscalingPolicyDTO) else policy
        resp = self._client.post("/v1/mesh/load/autoscaling/policy", json=body)
        _handle_error(resp)
        return AutoscalingPolicyDTO.model_validate(resp.json())

    def report_node_capacity_telemetry(
        self, node_id: str, metrics: dict[str, Any]
    ) -> MeshPeerNodeDTO:
        resp = self._client.post(
            "/v1/mesh/load/heartbeat-telemetry",
            json={"node_id": node_id, "metrics": metrics},
        )
        _handle_error(resp)
        return MeshPeerNodeDTO.model_validate(resp.json())

    def reap_idle_enclaves(
        self, cluster_id: str = "cluster-primary"
    ) -> list[AutoscalingEventDTO]:
        resp = self._client.post(f"/v1/mesh/load/scale-down/reap?cluster_id={cluster_id}")
        _handle_error(resp)
        return [AutoscalingEventDTO.model_validate(e) for e in resp.json()]

    # ── Decentralized Vector Sharding & Distributed Raft Consensus (Battery #32 / M117) ──

    def get_shard_topology(self) -> ShardTopologyResponse:
        resp = self._client.get("/v1/shards/topology")
        _handle_error(resp)
        return ShardTopologyResponse.model_validate(resp.json())

    def query_sharded_vectors(
        self, query: dict[str, Any] | ScatterGatherQuery
    ) -> ScatterGatherResponse:
        body = query.model_dump() if isinstance(query, ScatterGatherQuery) else query
        resp = self._client.post("/v1/shards/query", json=body)
        _handle_error(resp)
        return ScatterGatherResponse.model_validate(resp.json())

    def mutate_sharded_vectors(
        self, mutation: dict[str, Any] | ShardMutationRequest
    ) -> ShardMutationResponse:
        body = mutation.model_dump() if isinstance(mutation, ShardMutationRequest) else mutation
        resp = self._client.post("/v1/shards/mutate", json=body)
        _handle_error(resp)
        return ShardMutationResponse.model_validate(resp.json())

    def get_raft_consensus_status(self) -> RaftConsensusStatus:
        resp = self._client.get("/v1/shards/raft/status")
        _handle_error(resp)
        return RaftConsensusStatus.model_validate(resp.json())

    def trigger_raft_election(self, candidate_node_id: str) -> dict[str, Any]:
        resp = self._client.post("/v1/shards/election", json={"candidate_node_id": candidate_node_id})
        _handle_error(resp)
        return resp.json()

    def rebalance_shards(
        self, payload: dict[str, Any] | None = None
    ) -> ShardRebalancePlan:
        resp = self._client.post("/v1/shards/rebalance", json=payload or {})
        _handle_error(resp)
        return ShardRebalancePlan.model_validate(resp.json())

    def snapshot_shard(self, shard_id: str) -> dict[str, Any]:
        resp = self._client.post(f"/v1/shards/{shard_id}/snapshot")
        _handle_error(resp)
        return resp.json()


class AsyncRetrieverClient:
    """Asynchronous Client for Retriever Cognitive Engine."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000",
        tenant_id: str = "00000000-0000-0000-0000-000000000001",
        user_id: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.tenant_id = tenant_id
        self.user_id = user_id
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
        }
        if self.user_id:
            headers["X-User-ID"] = self.user_id

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
        )

    async def __aenter__(self) -> "AsyncRetrieverClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def search(
        self,
        query: str,
        limit: int = 10,
        enable_colbert_rerank: bool = True,
        hybrid_alpha: float = 0.7,
        filters: list[dict[str, Any]] | None = None,
        tags: list[str] | None = None,
    ) -> SearchResponse:
        payload = {
            "query": query,
            "limit": limit,
            "enable_hybrid": True,
            "hybrid_alpha": hybrid_alpha,
            "reranker_engine": "colbert" if enable_colbert_rerank else "cohere",
            "filters": filters or [],
            "tags": tags or [],
        }
        resp = await self._client.post(
            f"/v1/tenants/{self.tenant_id}/search",
            json=payload,
        )
        _handle_error(resp)
        data = resp.json()
        items = [
            SearchResultItem(
                chunk_id=item.get("chunkId") or item.get("chunk_id", ""),
                document_id=item.get("documentId") or item.get("document_id", ""),
                content=item["content"],
                score=item["score"],
                metadata=item.get("metadata", {}),
            )
            for item in data.get("results", [])
        ]
        return SearchResponse(
            results=items,
            total=data.get("total", len(items)),
            latency_ms=data.get("latency_ms", 0.0),
            strategy_used=data.get("strategy_used", "hybrid"),
            cached=data.get("cached", False),
        )

    async def chat_stream(
        self,
        session_id: str,
        message: str,
    ) -> AsyncIterator[ReActEvent]:
        payload = {
            "content": message,
            "stream": True,
            "agentic_mode": True,
        }
        async with self._client.stream(
            "POST",
            f"/v1/tenants/{self.tenant_id}/chat/sessions/{session_id}/messages",
            json=payload,
            headers={"Accept": "text/event-stream"},
        ) as response:
            _handle_error(response)
            async for line in response.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line.removeprefix("data:").strip()
                if data_str == "[DONE]":
                    break
                try:
                    parsed = json.loads(data_str)
                    yield ReActEvent.model_validate(parsed)
                except Exception:
                    yield ReActEvent(type="token", content=data_str)

    async def swarm_debate(
        self,
        task: str,
        roles: list[str] | None = None,
        max_rounds: int = 2,
    ) -> SwarmDebateResult:
        payload = {
            "task": task,
            "roles": roles or ["planner", "auditor", "synthesizer", "skeptic"],
            "max_rounds": max_rounds,
        }
        resp = await self._client.post(
            f"/v1/tenants/{self.tenant_id}/swarm/debate",
            json=payload,
        )
        _handle_error(resp)
        return SwarmDebateResult.model_validate(resp.json())

    # ── Community Connectors & CDC Pipeline (Battery #27) ──────────────────────

    async def list_connector_manifests(self) -> list[ConnectorManifestDTO]:
        resp = await self._client.get("/v1/admin/connectors/manifests")
        _handle_error(resp)
        data = resp.json()
        return [ConnectorManifestDTO.model_validate(m) for m in data.get("manifests", [])]

    async def list_connectors(self) -> list[ConnectorConfigDTO]:
        resp = await self._client.get(f"/v1/admin/tenants/{self.tenant_id}/connectors")
        _handle_error(resp)
        return [ConnectorConfigDTO.model_validate(c) for c in resp.json()]

    async def create_connector(
        self,
        name: str,
        connector_type: str,
        configuration: dict[str, Any] | None = None,
        sync_interval_minutes: int = 1440,
    ) -> ConnectorConfigDTO:
        payload = {
            "name": name,
            "connector_type": connector_type,
            "configuration": configuration or {},
            "sync_interval_minutes": sync_interval_minutes,
        }
        resp = await self._client.post(
            f"/v1/admin/tenants/{self.tenant_id}/connectors",
            json=payload,
        )
        _handle_error(resp)
        return ConnectorConfigDTO.model_validate(resp.json())

    async def trigger_connector_sync(self, connector_id: str) -> ConnectorSyncResponseDTO:
        resp = await self._client.post(
            f"/v1/admin/tenants/{self.tenant_id}/connectors/{connector_id}/sync"
        )
        _handle_error(resp)
        return ConnectorSyncResponseDTO.model_validate(resp.json())

    # ── Multimodal Vision GraphRAG & Schematic Ingestion (Battery #29) ─────────

    async def extract_schematic_text(
        self,
        content: str,
        filename: str = "architecture.svg",
        document_id: str | None = None,
    ) -> SchematicDiagramDTO:
        payload = {"content": content, "filename": filename, "document_id": document_id}
        resp = await self._client.post(
            f"/v1/tenants/{self.tenant_id}/vision/schematic/extract-text",
            json=payload,
        )
        _handle_error(resp)
        return SchematicDiagramDTO.model_validate(resp.json())

    async def query_multimodal_graph(
        self,
        entity_query: str,
        max_hops: int = 2,
    ) -> MultimodalGraphResponseDTO:
        payload = {
            "tenant_id": self.tenant_id,
            "entity_query": entity_query,
            "max_hops": max_hops,
            "include_visual_boxes": True,
        }
        resp = await self._client.post(
            f"/v1/tenants/{self.tenant_id}/vision/graph/query",
            json=payload,
        )
        _handle_error(resp)
        return MultimodalGraphResponseDTO.model_validate(resp.json())

    async def get_document_schematics(self, document_id: str) -> dict[str, Any]:
        resp = await self._client.get(f"/v1/tenants/{self.tenant_id}/vision/schematics/{document_id}")
        _handle_error(resp)
        return resp.json()

    async def get_multimodal_vision_status(self) -> dict[str, Any]:
        resp = await self._client.get("/v1/graph/multimodal/status")
        _handle_error(resp)
        return resp.json()

    def get_voice_stream_url(
        self,
        session_id: str,
        sensitivity: float = 0.65,
        silence_threshold_ms: int = 400,
        voice: str = "neural_natural",
        speed: float = 1.0,
    ) -> str:
        """Returns the full WebSocket URL for full-duplex real-time voice streaming."""
        ws_proto = "wss" if self.base_url.startswith("https") else "ws"
        host = self.base_url.split("://")[-1].rstrip("/")
        return (
            f"{ws_proto}://{host}/v1/tenants/{self.tenant_id}/voice/stream/{session_id}"
            f"?token={self.api_key}&sensitivity={sensitivity}&silence_threshold_ms={silence_threshold_ms}&voice={voice}&speed={speed}"
        )

    # ── Distributed MCP Mesh & Agent Federation (Battery #30 / M115) ──────────

    async def get_mesh_status(self) -> MeshStatusSummaryDTO:
        resp = await self._client.get("/v1/mesh/status")
        _handle_error(resp)
        return MeshStatusSummaryDTO.model_validate(resp.json())

    async def list_mesh_nodes(self, status_filter: str | None = None) -> list[MeshPeerNodeDTO]:
        params = {"status": status_filter} if status_filter else {}
        resp = await self._client.get("/v1/mesh/nodes", params=params)
        _handle_error(resp)
        return [MeshPeerNodeDTO.model_validate(n) for n in resp.json()]

    async def list_mesh_tools(self) -> list[dict[str, Any]]:
        resp = await self._client.get("/v1/mesh/tools")
        _handle_error(resp)
        return resp.json()

    async def execute_mesh_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        target_cluster_id: str = "cluster_local",
        policy: str = "local_first",
    ) -> dict[str, Any]:
        payload = {
            "call_id": "call_py_async_client",
            "tool_name": tool_name,
            "arguments": arguments or {},
            "tenant_id": self.tenant_id,
            "source_cluster_id": "cluster_python_sdk",
            "target_cluster_id": target_cluster_id,
        }
        resp = await self._client.post(f"/v1/mesh/tools/execute?policy={policy}", json=payload)
        _handle_error(resp)
        return resp.json()

    async def delegate_federated_task(
        self,
        target_cluster_id: str,
        intent: str,
        target_agent_role: str = "forensic_auditor",
        context_scope: dict[str, Any] | None = None,
        max_depth: int = 2,
        visited_clusters: list[str] | None = None,
    ) -> FederatedDelegationResponseDTO:
        payload = {
            "target_cluster_id": target_cluster_id,
            "tenant_id": self.tenant_id,
            "intent": intent,
            "target_agent_role": target_agent_role,
            "context_scope": context_scope or {},
            "max_depth": max_depth,
            "visited_clusters": visited_clusters or [],
        }
        resp = await self._client.post("/v1/mesh/federation/delegate", json=payload)
        _handle_error(resp)
        return FederatedDelegationResponseDTO.model_validate(resp.json())

    async def get_federated_task_status(self, delegation_id: str) -> FederatedDelegationResponseDTO:
        resp = await self._client.get(f"/v1/mesh/federation/tasks/{delegation_id}")
        _handle_error(resp)
        return FederatedDelegationResponseDTO.model_validate(resp.json())

    # ── Autonomous Mesh Dynamic Load-Balancing & Autoscaling (Battery #31 / M116) ──

    async def get_mesh_load_metrics(self) -> dict[str, Any]:
        resp = await self._client.get("/v1/mesh/load/metrics")
        _handle_error(resp)
        return resp.json()

    async def get_autoscaling_events(self, limit: int = 50) -> list[AutoscalingEventDTO]:
        resp = await self._client.get(f"/v1/mesh/load/autoscaling/events?limit={limit}")
        _handle_error(resp)
        return [AutoscalingEventDTO.model_validate(e) for e in resp.json()]

    async def update_autoscaling_policy(
        self, policy: dict[str, Any] | AutoscalingPolicyDTO
    ) -> AutoscalingPolicyDTO:
        body = policy.model_dump() if isinstance(policy, AutoscalingPolicyDTO) else policy
        resp = await self._client.post("/v1/mesh/load/autoscaling/policy", json=body)
        _handle_error(resp)
        return AutoscalingPolicyDTO.model_validate(resp.json())

    async def report_node_capacity_telemetry(
        self, node_id: str, metrics: dict[str, Any]
    ) -> MeshPeerNodeDTO:
        resp = await self._client.post(
            "/v1/mesh/load/heartbeat-telemetry",
            json={"node_id": node_id, "metrics": metrics},
        )
        _handle_error(resp)
        return MeshPeerNodeDTO.model_validate(resp.json())

    async def reap_idle_enclaves(
        self, cluster_id: str = "cluster-primary"
    ) -> list[AutoscalingEventDTO]:
        resp = await self._client.post(f"/v1/mesh/load/scale-down/reap?cluster_id={cluster_id}")
        _handle_error(resp)
        return [AutoscalingEventDTO.model_validate(e) for e in resp.json()]

    # ── Decentralized Vector Sharding & Distributed Raft Consensus (Battery #32 / M117) ──

    async def get_shard_topology(self) -> ShardTopologyResponse:
        resp = await self._client.get("/v1/shards/topology")
        _handle_error(resp)
        return ShardTopologyResponse.model_validate(resp.json())

    async def query_sharded_vectors(
        self, query: dict[str, Any] | ScatterGatherQuery
    ) -> ScatterGatherResponse:
        body = query.model_dump() if isinstance(query, ScatterGatherQuery) else query
        resp = await self._client.post("/v1/shards/query", json=body)
        _handle_error(resp)
        return ScatterGatherResponse.model_validate(resp.json())

    async def mutate_sharded_vectors(
        self, mutation: dict[str, Any] | ShardMutationRequest
    ) -> ShardMutationResponse:
        body = mutation.model_dump() if isinstance(mutation, ShardMutationRequest) else mutation
        resp = await self._client.post("/v1/shards/mutate", json=body)
        _handle_error(resp)
        return ShardMutationResponse.model_validate(resp.json())

    async def get_raft_consensus_status(self) -> RaftConsensusStatus:
        resp = await self._client.get("/v1/shards/raft/status")
        _handle_error(resp)
        return RaftConsensusStatus.model_validate(resp.json())

    async def trigger_raft_election(self, candidate_node_id: str) -> dict[str, Any]:
        resp = await self._client.post("/v1/shards/election", json={"candidate_node_id": candidate_node_id})
        _handle_error(resp)
        return resp.json()

    async def rebalance_shards(
        self, payload: dict[str, Any] | None = None
    ) -> ShardRebalancePlan:
        resp = await self._client.post("/v1/shards/rebalance", json=payload or {})
        _handle_error(resp)
        return ShardRebalancePlan.model_validate(resp.json())

    async def snapshot_shard(self, shard_id: str) -> dict[str, Any]:
        resp = await self._client.post(f"/v1/shards/{shard_id}/snapshot")
        _handle_error(resp)
        return resp.json()

    # ── Zero-Knowledge Proof (ZKP) Vector Attestation & Grounding (Battery #33 / M118) ──

    async def get_zkp_health(self) -> dict[str, Any]:
        resp = await self._client.get("/v1/zkp/health")
        _handle_error(resp)
        return resp.json()

    async def compute_document_merkle_root(
        self, document_id: str, chunks: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        resp = await self._client.post(
            f"/v1/tenants/{self.tenant_id}/zkp/merkle-root/{document_id}",
            json={"chunks": chunks or []},
        )
        _handle_error(resp)
        return resp.json()

    async def get_chunk_inclusion_proof(
        self, chunk_id: str, document_id: str, chunks: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        resp = await self._client.post(
            f"/v1/tenants/{self.tenant_id}/zkp/proof/chunk/{chunk_id}",
            json={"document_id": document_id, "chunks": chunks or []},
        )
        _handle_error(resp)
        return resp.json()

    async def issue_grounding_certificate(
        self,
        document_id: str,
        query: str,
        response_text: str,
        cited_chunks: list[dict[str, Any]],
        all_document_chunks: list[dict[str, Any]],
        similarity_bound: float = 0.7,
        ttl_seconds: float = 86400.0,
    ) -> dict[str, Any]:
        payload = {
            "document_id": document_id,
            "query": query,
            "response": response_text,
            "cited_chunks": cited_chunks,
            "all_document_chunks": all_document_chunks,
            "similarity_bound": similarity_bound,
            "ttl_seconds": ttl_seconds,
        }
        resp = await self._client.post(f"/v1/tenants/{self.tenant_id}/zkp/attest", json=payload)
        _handle_error(resp)
        return resp.json()

    async def verify_grounding_certificate(
        self,
        certificate: dict[str, Any],
        query: str | None = None,
        response_text: str | None = None,
        expected_document_root: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "certificate": certificate,
            "query": query,
            "response": response_text,
            "expected_document_root": expected_document_root,
        }
        resp = await self._client.post("/v1/zkp/verify", json=payload)
        _handle_error(resp)
        return resp.json()

    async def list_grounding_certificates(self, limit: int = 50) -> list[dict[str, Any]]:
        resp = await self._client.get(
            f"/v1/tenants/{self.tenant_id}/zkp/certificates", params={"limit": limit}
        )
        _handle_error(resp)
        return resp.json()

    # --- Enterprise Identity Federation & RB-VAC (M119, Battery #34) ---

    async def get_saml_config(self) -> dict[str, Any]:
        resp = await self._client.get(f"/v1/tenants/{self.tenant_id}/identity/saml/config")
        _handle_error(resp)
        return resp.json()

    async def configure_saml_idp(self, config: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.post(
            f"/v1/tenants/{self.tenant_id}/identity/saml/config", json=config
        )
        _handle_error(resp)
        return resp.json()

    async def get_sp_metadata_xml(self) -> str:
        resp = await self._client.get(f"/v1/tenants/{self.tenant_id}/identity/saml/metadata")
        _handle_error(resp)
        return resp.text

    async def validate_saml_acs(self, saml_response_b64: str) -> dict[str, Any]:
        resp = await self._client.post(
            f"/v1/tenants/{self.tenant_id}/identity/saml/acs",
            json={"saml_response": saml_response_b64},
        )
        _handle_error(resp)
        return resp.json()

    async def generate_scim_token(self) -> dict[str, Any]:
        resp = await self._client.post(f"/v1/tenants/{self.tenant_id}/identity/scim/token")
        _handle_error(resp)
        return resp.json()

    async def list_scim_users(
        self, start_index: int = 1, count: int = 20, filter_query: str | None = None
    ) -> dict[str, Any]:
        params = {"startIndex": start_index, "count": count}
        if filter_query:
            params["filter"] = filter_query
        resp = await self._client.get(
            f"/v1/scim/v2/tenants/{self.tenant_id}/Users", params=params
        )
        _handle_error(resp)
        return resp.json()

    async def create_scim_user(self, user_payload: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.post(
            f"/v1/scim/v2/tenants/{self.tenant_id}/Users", json=user_payload
        )
        _handle_error(resp)
        return resp.json()

    async def patch_scim_user(
        self, user_id: str, operations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        resp = await self._client.patch(
            f"/v1/scim/v2/tenants/{self.tenant_id}/Users/{user_id}",
            json={"Operations": operations},
        )
        _handle_error(resp)
        return resp.json()

    async def delete_scim_user(self, user_id: str) -> bool:
        resp = await self._client.delete(f"/v1/scim/v2/tenants/{self.tenant_id}/Users/{user_id}")
        _handle_error(resp)
        return True

    async def list_scim_groups(self, start_index: int = 1, count: int = 20) -> dict[str, Any]:
        params = {"startIndex": start_index, "count": count}
        resp = await self._client.get(
            f"/v1/scim/v2/tenants/{self.tenant_id}/Groups", params=params
        )
        _handle_error(resp)
        return resp.json()

    async def create_scim_group(self, group_payload: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.post(
            f"/v1/scim/v2/tenants/{self.tenant_id}/Groups", json=group_payload
        )
        _handle_error(resp)
        return resp.json()

    async def simulate_rbvac(
        self,
        user_id: str,
        email: str,
        security_groups: list[str],
        candidates: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "user_id": user_id,
            "email": email,
            "security_groups": security_groups,
            "candidates": candidates or [],
        }
        resp = await self._client.post(
            f"/v1/tenants/{self.tenant_id}/identity/rbvac/simulate", json=payload
        )
        _handle_error(resp)
        return resp.json()

    # --- Continuous DPO / ORPO Preference Fine-Tuning (M120) ---

    async def get_tuning_config(self) -> dict[str, Any]:
        resp = await self._client.get(f"/v1/tenants/{self.tenant_id}/tuning/config")
        _handle_error(resp)
        return resp.json()

    async def update_tuning_config(self, config_payload: dict[str, Any]) -> dict[str, Any]:
        config_payload["tenant_id"] = self.tenant_id
        resp = await self._client.put(
            f"/v1/tenants/{self.tenant_id}/tuning/config", json=config_payload
        )
        _handle_error(resp)
        return resp.json()

    async def list_preference_pairs(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        params = {"limit": limit, "offset": offset}
        resp = await self._client.get(
            f"/v1/tenants/{self.tenant_id}/tuning/pairs", params=params
        )
        _handle_error(resp)
        return resp.json()

    async def harvest_preference_pair(
        self,
        prompt: str,
        winning_response: str,
        losing_response: str,
        source_message_id: str | None = None,
        feedback_rating: int = 1,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "prompt": prompt,
            "winning_response": winning_response,
            "losing_response": losing_response,
            "source_message_id": source_message_id,
            "feedback_rating": feedback_rating,
            "tags": tags or [],
        }
        resp = await self._client.post(
            f"/v1/tenants/{self.tenant_id}/tuning/pairs", json=payload
        )
        _handle_error(resp)
        return resp.json()

    async def delete_preference_pair(self, pair_id: str) -> bool:
        resp = await self._client.delete(
            f"/v1/tenants/{self.tenant_id}/tuning/pairs/{pair_id}"
        )
        _handle_error(resp)
        return True

    async def trigger_tuning_job(
        self,
        objective: str = "dpo",
        hyperparams: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {"objective": objective, "hyperparameters": hyperparams}
        resp = await self._client.post(
            f"/v1/tenants/{self.tenant_id}/tuning/jobs", json=payload
        )
        _handle_error(resp)
        return resp.json()

    async def list_tuning_jobs(self, limit: int = 20) -> list[dict[str, Any]]:
        params = {"limit": limit}
        resp = await self._client.get(
            f"/v1/tenants/{self.tenant_id}/tuning/jobs", params=params
        )
        _handle_error(resp)
        return resp.json()

    async def get_tuning_job(self, job_id: str) -> dict[str, Any]:
        resp = await self._client.get(
            f"/v1/tenants/{self.tenant_id}/tuning/jobs/{job_id}"
        )
        _handle_error(resp)
        return resp.json()

    async def promote_tuning_adapter(self, job_id: str) -> dict[str, Any]:
        resp = await self._client.post(
            f"/v1/tenants/{self.tenant_id}/tuning/jobs/{job_id}/promote"
        )
        _handle_error(resp)
        return resp.json()

    async def rollback_tuning_adapter(self, target_adapter_id: str | None = None) -> dict[str, Any]:
        url = f"/v1/tenants/{self.tenant_id}/tuning/rollback"
        params = {"target_adapter_id": target_adapter_id} if target_adapter_id else {}
        resp = await self._client.post(url, params=params)
        _handle_error(resp)
        return resp.json()

    async def simulate_tuning_math(
        self,
        prompt: str,
        beta: float = 0.1,
        lambda_orpo: float = 0.1,
        pi_theta_win_prob: float = 0.85,
        pi_ref_win_prob: float = 0.50,
        pi_theta_lose_prob: float = 0.15,
        pi_ref_lose_prob: float = 0.50,
    ) -> dict[str, Any]:
        payload = {
            "prompt": prompt,
            "beta": beta,
            "lambda_orpo": lambda_orpo,
            "pi_theta_win_prob": pi_theta_win_prob,
            "pi_ref_win_prob": pi_ref_win_prob,
            "pi_theta_lose_prob": pi_theta_lose_prob,
            "pi_ref_lose_prob": pi_ref_lose_prob,
        }
        resp = await self._client.post("/v1/tuning/math/simulate", json=payload)
        _handle_error(resp)
        return resp.json()

    # ── Confidential Multi-Party Vector Computation (MPC) (Battery #36 / M121) ─

    async def create_mpc_session(
        self,
        title: str,
        protocol: str = "beaver_triples",
        required_parties_count: int = 2,
        dimension: int = 768,
        privacy_threshold: float = 0.70,
        top_k: int = 5,
        epsilon_budget: float = 10.0,
    ) -> dict[str, Any]:
        payload = {
            "title": title,
            "protocol": protocol,
            "required_parties_count": required_parties_count,
            "dimension": dimension,
            "privacy_threshold": privacy_threshold,
            "top_k": top_k,
            "epsilon_budget": epsilon_budget,
        }
        resp = await self._client.post(f"/v1/tenants/{self.tenant_id}/mpc/sessions", json=payload)
        _handle_error(resp)
        return resp.json()

    async def list_mpc_sessions(self) -> list[dict[str, Any]]:
        resp = await self._client.get(f"/v1/tenants/{self.tenant_id}/mpc/sessions")
        _handle_error(resp)
        return resp.json()

    async def get_mpc_session(self, session_id: str) -> dict[str, Any]:
        resp = await self._client.get(f"/v1/tenants/{self.tenant_id}/mpc/sessions/{session_id}")
        _handle_error(resp)
        return resp.json()

    async def join_mpc_session(
        self,
        session_id: str,
        party_id: str,
        display_name: str,
        public_key: str,
        role: str = "evaluator",
    ) -> dict[str, Any]:
        payload = {
            "party_id": party_id,
            "display_name": display_name,
            "public_key": public_key,
            "role": role,
        }
        resp = await self._client.post(
            f"/v1/tenants/{self.tenant_id}/mpc/sessions/{session_id}/join",
            json=payload,
        )
        _handle_error(resp)
        return resp.json()

    async def submit_mpc_vector_shares(
        self,
        session_id: str,
        party_id: str,
        shares: list[dict[str, Any]],
    ) -> dict[str, Any]:
        payload = {"party_id": party_id, "shares": shares}
        resp = await self._client.post(
            f"/v1/tenants/{self.tenant_id}/mpc/sessions/{session_id}/shares",
            json=payload,
        )
        _handle_error(resp)
        return resp.json()

    async def execute_mpc_compute(self, session_id: str) -> dict[str, Any]:
        resp = await self._client.post(f"/v1/tenants/{self.tenant_id}/mpc/sessions/{session_id}/compute")
        _handle_error(resp)
        return resp.json()

    async def get_mpc_results(self, session_id: str) -> dict[str, Any]:
        resp = await self._client.get(f"/v1/tenants/{self.tenant_id}/mpc/sessions/{session_id}/results")
        _handle_error(resp)
        return resp.json()

    async def abort_mpc_session(self, session_id: str, reason: str = "User aborted") -> dict[str, Any]:
        resp = await self._client.post(
            f"/v1/tenants/{self.tenant_id}/mpc/sessions/{session_id}/abort",
            json={"reason": reason},
        )
        _handle_error(resp)
        return resp.json()

    async def simulate_mpc_math(
        self,
        vector_dimension: int = 8,
        parties_count: int = 3,
        fixed_point_scale: int = 65536,
        query_vector: list[float] | None = None,
        candidate_vector: list[float] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "vector_dimension": vector_dimension,
            "parties_count": parties_count,
            "fixed_point_scale": fixed_point_scale,
            "query_vector": query_vector,
            "candidate_vector": candidate_vector,
        }
        resp = await self._client.post("/v1/mpc/math/simulate", json=payload)
        _handle_error(resp)
        return resp.json()

    # --- Benchmark Gatekeeper (M122) ---

    async def list_benchmark_suites(self) -> list[dict[str, Any]]:
        resp = await self._client.get(f"/v1/tenants/{self.tenant_id}/benchmarks/suites")
        _handle_error(resp)
        return resp.json()

    async def create_benchmark_suite(
        self,
        name: str,
        description: str = "",
        k_cutoff: int = 10,
        gate_policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "name": name,
            "description": description,
            "k_cutoff": k_cutoff,
            "gate_policy": gate_policy,
        }
        resp = await self._client.post(f"/v1/tenants/{self.tenant_id}/benchmarks/suites", json=payload)
        _handle_error(resp)
        return resp.json()

    async def list_benchmark_runs(self, suite_id: str | None = None) -> list[dict[str, Any]]:
        query = f"?suite_id={suite_id}" if suite_id else ""
        resp = await self._client.get(f"/v1/tenants/{self.tenant_id}/benchmarks/runs{query}")
        _handle_error(resp)
        return resp.json()

    async def get_benchmark_run(self, run_id: str) -> dict[str, Any]:
        resp = await self._client.get(f"/v1/tenants/{self.tenant_id}/benchmarks/runs/{run_id}")
        _handle_error(resp)
        return resp.json()

    async def trigger_benchmark_run(
        self,
        suite_id: str,
        checkpoint_or_commit: str,
        is_baseline: bool = False,
        samples: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "suite_id": suite_id,
            "checkpoint_or_commit": checkpoint_or_commit,
            "is_baseline": is_baseline,
            "samples": samples,
        }
        resp = await self._client.post(f"/v1/tenants/{self.tenant_id}/benchmarks/runs", json=payload)
        _handle_error(resp)
        return resp.json()

    async def evaluate_regression_gate(
        self,
        suite_id: str,
        candidate_run_id: str,
        baseline_run_id: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "suite_id": suite_id,
            "candidate_run_id": candidate_run_id,
            "baseline_run_id": baseline_run_id,
        }
        resp = await self._client.post(f"/v1/tenants/{self.tenant_id}/benchmarks/evaluate-gate", json=payload)
        _handle_error(resp)
        return resp.json()

    async def simulate_benchmark_math(
        self,
        baseline_mean: float,
        baseline_std: float,
        candidate_mean: float,
        candidate_std: float,
        baseline_n: int = 30,
        candidate_n: int = 30,
        metric_type: str = "latency_p95",
        alpha: float = 0.05,
        tolerance_threshold_pct: float = 10.0,
    ) -> dict[str, Any]:
        payload = {
            "metric_type": metric_type,
            "baseline_mean": baseline_mean,
            "baseline_std": baseline_std,
            "baseline_n": baseline_n,
            "candidate_mean": candidate_mean,
            "candidate_std": candidate_std,
            "candidate_n": candidate_n,
            "alpha": alpha,
            "tolerance_threshold_pct": tolerance_threshold_pct,
        }
        resp = await self._client.post("/v1/benchmarks/math/simulate", json=payload)
        _handle_error(resp)
        return resp.json()





