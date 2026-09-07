"""Tests for Model Context Protocol (MCP) server integration."""

import ast
import os

import pytest
from fastapi.testclient import TestClient

from src.container import battery_mcp_adapter
from src.domain.abstractions.mcp import (
    McpConfigResponse,
    McpToolDefinition,
    McpToolExecutionResult,
)
from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_mcp_hexagonal_architecture():
    """Verify src/domain/abstractions/mcp.py has zero forbidden framework dependencies."""
    filepath = os.path.join(
        os.path.dirname(__file__), "../src/domain/abstractions/mcp.py"
    )
    with open(filepath) as f:
        tree = ast.parse(f.read(), filename=filepath)

    forbidden_prefixes = ("src.adapters", "src.routers", "sqlalchemy", "fastapi")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for forbidden in forbidden_prefixes:
                    assert not alias.name.startswith(forbidden), (
                        f"Forbidden import '{alias.name}' in {filepath}"
                    )
        elif isinstance(node, ast.ImportFrom) and node.module:
            for forbidden in forbidden_prefixes:
                assert not node.module.startswith(forbidden), (
                    f"Forbidden import '{node.module}' in {filepath}"
                )


def test_battery_mcp_adapter_definitions():
    """Verify tool definitions are correctly extracted from platform batteries."""
    tools = battery_mcp_adapter.get_tool_definitions(tenant_id="test_tenant")
    assert len(tools) >= 8

    tool_names = {t.name for t in tools}
    assert "hybrid_search" in tool_names
    assert "document_reader" in tool_names
    assert "graph_query" in tool_names
    assert "rlm_execute" in tool_names
    assert "calculator" in tool_names
    assert "system_metrics" in tool_names
    assert "list_batteries" in tool_names

    for tool in tools:
        assert isinstance(tool, McpToolDefinition)
        assert tool.name
        assert tool.description
        assert tool.inputSchema.type == "object"


@pytest.mark.asyncio
async def test_battery_mcp_adapter_execution():
    """Verify tool execution via the adapter."""
    # Test calculator
    calc_res = await battery_mcp_adapter.execute_tool(
        tenant_id="test_tenant",
        tool_name="calculator",
        arguments={"expression": "25 * 4"},
    )
    assert isinstance(calc_res, McpToolExecutionResult)
    assert not calc_res.is_error
    assert "100" in calc_res.content[0].text

    # Test list_batteries
    batteries_res = await battery_mcp_adapter.execute_tool(
        tenant_id="test_tenant",
        tool_name="list_batteries",
        arguments={},
    )
    assert not batteries_res.is_error
    assert "bm25_sparse_retrieval" in batteries_res.content[0].text


def test_battery_mcp_adapter_generate_config():
    """Verify client configuration generation for Cursor, Claude Desktop, and Cline."""
    cfg = battery_mcp_adapter.generate_config_response(
        tenant_id="tenant_alpha",
        api_key="retriever_sk_test_12345",
        base_url="https://rag.prateeq.in",
    )
    assert isinstance(cfg, McpConfigResponse)
    assert cfg.tenant_id == "tenant_alpha"
    assert "retriever" in cfg.cursor_config["mcpServers"]
    assert "retriever" in cfg.claude_desktop_config["mcpServers"]
    assert "retriever" in cfg.cline_config["mcpServers"]
    assert len(cfg.snippets) == 4
    snippet_names = {s.name for s in cfg.snippets}
    assert "Cursor IDE" in snippet_names
    assert "Claude Desktop" in snippet_names
    assert "VS Code / Cline" in snippet_names
    assert "Python / LangChain" in snippet_names


def test_mcp_initialize_rpc(client):
    """Test MCP JSON-RPC 2.0 initialize request."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "cursor", "version": "0.45.0"},
        },
    }
    response = client.post("/v1/mcp/messages?tenant_id=tenant_test", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == 1
    assert data["result"]["protocolVersion"] == "2024-11-05"
    assert "tools" in data["result"]["capabilities"]
    assert data["result"]["serverInfo"]["name"] == "retriever-mcp-server"


def test_mcp_tools_list_rpc(client):
    """Test MCP JSON-RPC 2.0 tools/list request."""
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    }
    response = client.post("/v1/mcp/messages?tenant_id=tenant_test", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 2
    tools = data["result"]["tools"]
    assert isinstance(tools, list)
    assert any(t["name"] == "hybrid_search" for t in tools)
    assert any(t["name"] == "calculator" for t in tools)


def test_mcp_tools_call_calculator_rpc(client):
    """Test MCP JSON-RPC 2.0 tools/call request for calculator."""
    payload = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "calculator",
            "arguments": {"expression": "50 + 25"},
        },
    }
    response = client.post("/v1/mcp/messages?tenant_id=tenant_test", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 3
    assert data["result"]["isError"] is False
    assert "75" in data["result"]["content"][0]["text"]


def test_mcp_ping_rpc(client):
    """Test MCP JSON-RPC 2.0 ping request."""
    payload = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "ping",
    }
    response = client.post("/v1/mcp/messages?tenant_id=tenant_test", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 4
    assert data["result"] == {}


def test_mcp_unknown_method_rpc(client):
    """Test MCP JSON-RPC 2.0 error handling on unrecognized method."""
    payload = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "unknown_future_method",
    }
    response = client.post("/v1/mcp/messages?tenant_id=tenant_test", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 5
    assert data.get("result") is None
    assert data["error"]["code"] == -32601


def test_mcp_rest_endpoints(client):
    """Test REST GET /v1/mcp/config, GET /v1/mcp/tools, and POST /v1/mcp/test-tool."""
    # Test /v1/mcp/config
    cfg_resp = client.get("/v1/mcp/config?tenant_id=tenant_test")
    assert cfg_resp.status_code == 200
    cfg_data = cfg_resp.json()
    assert cfg_data["total_tools"] >= 8
    assert "cursor_config" in cfg_data

    # Test /v1/mcp/tools
    tools_resp = client.get("/v1/mcp/tools?tenant_id=tenant_test")
    assert tools_resp.status_code == 200
    tools_data = tools_resp.json()
    assert len(tools_data) >= 8

    # Test /v1/mcp/test-tool
    probe_resp = client.post(
        "/v1/mcp/test-tool?tenant_id=tenant_test",
        json={"tool_name": "calculator", "arguments": {"expression": "7 * 8"}},
    )
    assert probe_resp.status_code == 200
    probe_data = probe_resp.json()
    assert probe_data["is_error"] is False
    assert "56" in probe_data["content"][0]["text"]


@pytest.mark.asyncio
async def test_mcp_sse_endpoint():
    """Test GET /v1/mcp/sse creates SSE session and emits endpoint announcement event."""
    from starlette.requests import Request

    from src.routers.mcp import mcp_sse_endpoint

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/v1/mcp/sse",
        "headers": [],
        "query_string": b"tenant_id=tenant_test",
    }
    req = Request(scope)
    resp = await mcp_sse_endpoint(request=req, sessionId="test_session_123", token=None)
    assert resp.status_code == 200
    assert resp.media_type == "text/event-stream"

    gen = resp.body_iterator
    first_event = await gen.__anext__()
    assert "event: endpoint" in first_event
    assert "/v1/mcp/messages?sessionId=test_session_123" in first_event
    await gen.aclose()
