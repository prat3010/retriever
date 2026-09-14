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
    CognitiveMemoryNode,
    ConnectorConfigDTO,
    ConnectorManifestDTO,
    ConnectorSyncResponseDTO,
    DocumentResponse,
    EnclaveEvidence,
    McpToolDefinition,
    MultimodalGraphResponseDTO,
    ReActEvent,
    SchematicDiagramDTO,
    SearchResponse,
    SearchResultItem,
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


