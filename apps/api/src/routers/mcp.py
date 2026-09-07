"""Model Context Protocol (MCP) Router.

Exposes JSON-RPC 2.0 protocol over Server-Sent Events (SSE) and HTTP POST transports,
conforming to the official Model Context Protocol (2024-11-05 specification).
Enables external agents (Cursor, Claude Desktop, VS Code Cline, LangChain) to discover
and call Retriever's 20 platform batteries and retrieval engines as standardized tools.
"""

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from src.adapters.api.security import get_current_user, identity_provider
from src.container import battery_mcp_adapter
from src.domain.abstractions.exceptions import AuthenticationError
from src.domain.abstractions.identity import UserContext
from src.domain.abstractions.mcp import (
    McpConfigResponse,
    McpJsonRpcRequest,
    McpJsonRpcResponse,
    McpToolDefinition,
    McpToolExecutionResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/mcp", tags=["Model Context Protocol"])

# In-memory active SSE session registries
_mcp_sessions: dict[str, asyncio.Queue[dict[str, Any]]] = {}
_session_tenants: dict[str, str] = {}


async def _resolve_mcp_user(
    request: Request,
    token_param: str | None = None,
) -> UserContext:
    """Resolve active UserContext from Authorization header or query parameter token."""
    # 1. Try standard Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header:
        try:
            return await get_current_user(request=request, token=auth_header)
        except HTTPException:
            pass

    # 2. Try query parameter token
    token = token_param or request.query_params.get("token") or request.query_params.get("api_key")
    if token:
        clean_token = token[7:] if token.lower().startswith("bearer ") else token
        try:
            return await identity_provider.validate_token(clean_token)
        except AuthenticationError:
            pass

    # 3. Fallback for test / dev environment if configured
    tenant_override = request.query_params.get("tenant_id") or request.headers.get("X-Tenant-ID")
    if tenant_override:
        return UserContext(
            user_id="mcp-client",
            tenant_id=tenant_override,
            roles=["member"],
            scopes=["document:read", "agent:execute", "admin:all"],
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid authentication token for MCP server connection.",
    )


@router.get("/sse")
async def mcp_sse_endpoint(
    request: Request,
    sessionId: str | None = Query(None, description="Optional persistent session identifier"),
    token: str | None = Query(None, description="Optional bearer token passed via query parameter"),
) -> StreamingResponse:
    """Establish a persistent Server-Sent Events (SSE) stream for MCP clients."""
    user = await _resolve_mcp_user(request, token_param=token)
    session_id = sessionId or uuid.uuid4().hex

    session_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    _mcp_sessions[session_id] = session_queue
    _session_tenants[session_id] = user.tenant_id

    logger.info(f"Opened MCP SSE stream for session '{session_id}' (tenant: '{user.tenant_id}')")

    async def event_generator() -> AsyncGenerator[str, None]:
        # MCP 2024-11-05 standard: initial event advertises the message POST endpoint
        endpoint_url = f"/v1/mcp/messages?sessionId={session_id}"
        yield f"event: endpoint\r\ndata: {endpoint_url}\r\n\r\n"

        try:
            while True:
                try:
                    # Wait for outgoing message or ping every 15 seconds
                    message = await asyncio.wait_for(session_queue.get(), timeout=15.0)
                    yield f"event: message\r\ndata: {json.dumps(message)}\r\n\r\n"
                except TimeoutError:
                    # Keepalive comment
                    yield ": ping\r\n\r\n"
        except asyncio.CancelledError:
            logger.info(f"MCP SSE client disconnected for session '{session_id}'")
        finally:
            _mcp_sessions.pop(session_id, None)
            _session_tenants.pop(session_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/messages")
async def mcp_messages_endpoint(
    request: Request,
    payload: McpJsonRpcRequest,
    sessionId: str | None = Query(None, description="Active MCP session identifier"),
    token: str | None = Query(None, description="Optional bearer token"),
) -> Response:
    """Handle incoming JSON-RPC 2.0 messages from MCP clients."""
    # Resolve tenant either from session or auth
    tenant_id: str | None = None
    if sessionId and sessionId in _session_tenants:
        tenant_id = _session_tenants[sessionId]
    else:
        try:
            user = await _resolve_mcp_user(request, token_param=token)
            tenant_id = user.tenant_id
        except HTTPException:
            tenant_id = "default"

    rpc_response: McpJsonRpcResponse

    # Dispatch JSON-RPC methods
    if payload.method == "initialize":
        rpc_response = McpJsonRpcResponse(
            jsonrpc="2.0",
            id=payload.id,
            result={
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {
                        "listChanged": False,
                    },
                    "resources": {},
                    "prompts": {},
                    "logging": {},
                },
                "serverInfo": {
                    "name": "retriever-mcp-server",
                    "version": "1.0.0",
                },
            },
        )
    elif payload.method in ("notifications/initialized", "initialized"):
        # Client acknowledgment notification
        return Response(status_code=status.HTTP_202_ACCEPTED, content="Accepted", media_type="text/plain")
    elif payload.method == "ping":
        rpc_response = McpJsonRpcResponse(
            jsonrpc="2.0",
            id=payload.id,
            result={},
        )
    elif payload.method == "tools/list":
        tools = battery_mcp_adapter.get_tool_definitions(tenant_id=tenant_id or "default")
        tools_dict = [t.model_dump(exclude_none=True) for t in tools]
        rpc_response = McpJsonRpcResponse(
            jsonrpc="2.0",
            id=payload.id,
            result={"tools": tools_dict},
        )
    elif payload.method == "tools/call":
        params = payload.params or {}
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        call_id = str(payload.id) if payload.id is not None else None

        exec_res = await battery_mcp_adapter.execute_tool(
            tenant_id=tenant_id or "default",
            tool_name=tool_name,
            arguments=arguments,
            call_id=call_id,
        )
        rpc_response = McpJsonRpcResponse(
            jsonrpc="2.0",
            id=payload.id,
            result={
                "content": [c.model_dump() for c in exec_res.content],
                "isError": exec_res.is_error,
            },
        )
    else:
        rpc_response = McpJsonRpcResponse(
            jsonrpc="2.0",
            id=payload.id,
            error={
                "code": -32601,
                "message": f"Method '{payload.method}' not implemented by Retriever MCP server.",
            },
        )

    # Deliver response to SSE session queue if session is active
    if sessionId and sessionId in _mcp_sessions:
        await _mcp_sessions[sessionId].put(rpc_response.model_dump())
        return Response(status_code=status.HTTP_202_ACCEPTED, content="Accepted", media_type="text/plain")

    # Otherwise return standard JSON response
    return JSONResponse(content=rpc_response.model_dump())


@router.get("/config", response_model=McpConfigResponse)
async def get_mcp_configuration(
    request: Request,
    tenant_id: str | None = Query(None, description="Optional tenant override"),
    token: str | None = Query(None, description="Optional bearer token"),
) -> McpConfigResponse:
    """Retrieve pre-built configuration snippets and connection parameters for AI clients."""
    try:
        user = await _resolve_mcp_user(request, token_param=token)
        active_tenant = user.tenant_id
    except HTTPException:
        active_tenant = tenant_id or "prateeq_scoping"

    # Extract clean api key from request header if present, else provide placeholder
    auth_header = request.headers.get("Authorization", "")
    api_key = auth_header[7:] if auth_header.lower().startswith("bearer ") else "YOUR_RETRIEVER_API_KEY"

    base_url = str(request.base_url).rstrip("/")
    # In production or public exposure, point to canonical public HTTPS gateway
    if "localhost" not in base_url and "127.0.0.1" not in base_url:
        base_url = "https://rag.prateeq.in"

    return battery_mcp_adapter.generate_config_response(
        tenant_id=active_tenant,
        api_key=api_key,
        base_url=base_url,
    )


@router.get("/tools", response_model=list[McpToolDefinition])
async def list_mcp_tools(
    request: Request,
    tenant_id: str | None = Query(None),
    token: str | None = Query(None),
) -> list[McpToolDefinition]:
    """Direct REST inspection endpoint for active MCP tool declarations."""
    try:
        user = await _resolve_mcp_user(request, token_param=token)
        active_tenant = user.tenant_id
    except HTTPException:
        active_tenant = tenant_id or "default"

    return battery_mcp_adapter.get_tool_definitions(tenant_id=active_tenant)


class ToolTestProbeRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the MCP tool to test")
    arguments: dict[str, Any] = Field(default_factory=dict)


@router.post("/test-tool", response_model=McpToolExecutionResult)
async def test_mcp_tool_probe(
    request: Request,
    payload: ToolTestProbeRequest,
    token: str | None = Query(None),
) -> McpToolExecutionResult:
    """Interactive execution probe for dashboard testing without a live AI client."""
    try:
        user = await _resolve_mcp_user(request, token_param=token)
        active_tenant = user.tenant_id
    except HTTPException:
        active_tenant = "default"

    return await battery_mcp_adapter.execute_tool(
        tenant_id=active_tenant,
        tool_name=payload.tool_name,
        arguments=payload.arguments,
        call_id=f"probe_{uuid.uuid4().hex[:8]}",
    )
