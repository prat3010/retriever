"""Domain abstractions for Model Context Protocol (MCP) server.

Strictly adheres to Hexagonal Architecture: pure Pydantic contracts and enums with
zero external framework dependencies.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class McpTransportType(StrEnum):
    SSE = "sse"
    STDIO = "stdio"


class McpToolInputSchema(BaseModel):
    type: str = "object"
    properties: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)


class McpToolDefinition(BaseModel):
    name: str = Field(..., description="Unique tool identifier, e.g. 'hybrid_search'")
    description: str = Field(..., description="Description of the tool purpose for the AI model")
    inputSchema: McpToolInputSchema = Field(default_factory=McpToolInputSchema)
    category: str = Field(default="general")
    risk_level: str = Field(default="low", description="'low' | 'medium' | 'high' | 'critical'")
    requires_approval: bool = Field(default=False)
    battery_id: str | None = Field(default=None, description="Linked PlatformBattery identifier if applicable")


class McpToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    call_id: str | None = None


class McpContentItem(BaseModel):
    type: str = "text"
    text: str


class McpToolExecutionResult(BaseModel):
    content: list[McpContentItem]
    is_error: bool = False
    meta: dict[str, Any] = Field(default_factory=dict)


class McpJsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str
    params: dict[str, Any] | None = None


class McpJsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    result: Any | None = None
    error: dict[str, Any] | None = None


class McpClientSnippet(BaseModel):
    name: str
    filename: str
    language: str
    code: str
    description: str


class McpConfigResponse(BaseModel):
    tenant_id: str
    sse_endpoint: str
    message_endpoint: str
    total_tools: int
    active_batteries: int
    cursor_config: dict[str, Any]
    claude_desktop_config: dict[str, Any]
    cline_config: dict[str, Any]
    snippets: list[McpClientSnippet]
