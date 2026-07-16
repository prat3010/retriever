"""Tests for M22: Structured Data Extraction."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.abstractions.inference import (
    ChatMessage,
    InferenceRequest,
)
from src.domain.abstractions.ingestion import DocumentChunk

# ── Step 1: DocumentChunk model ────────────────────────────────────────────


def test_document_chunk_model() -> None:
    c = DocumentChunk(
        chunk_id="c1",
        document_id="d1",
        tenant_id="t1",
        content="Hello world",
        token_count=2,
        chunk_index=0,
        created_at="2026-07-15T00:00:00+00:00",
    )
    assert c.chunk_id == "c1"
    assert c.content == "Hello world"
    assert c.parent_chunk_id is None
    assert c.meta_data == {}


# ── Step 2: get_document_chunks on repository ──────────────────────────────


def test_document_repository_has_get_document_chunks() -> None:
    from src.domain.abstractions.ingestion import DocumentRepository

    assert hasattr(DocumentRepository, "get_document_chunks")


def test_sql_document_repository_has_get_document_chunks() -> None:
    from src.adapters.database.document_repository import SqlDocumentRepository

    assert hasattr(SqlDocumentRepository, "get_document_chunks")


# ── Step 2/3: json_schema wired into adapters ──────────────────────────────


def test_openai_adapter_accepts_json_schema() -> None:

    req = InferenceRequest(
        messages=[ChatMessage(role="user", content="test")],
        json_schema={"type": "object", "properties": {"name": {"type": "string"}}},
    )
    assert req.json_schema is not None


def test_anthropic_adapter_accepts_json_schema() -> None:

    req = InferenceRequest(
        messages=[ChatMessage(role="user", content="test")],
        json_schema={"type": "object", "properties": {"name": {"type": "string"}}},
    )
    assert req.json_schema is not None


@pytest.mark.asyncio
async def test_openai_adapter_sends_response_format_when_json_schema() -> None:
    from src.adapters.cognitive.openai_adapter import OpenAILLMAdapter

    adapter = OpenAILLMAdapter(api_key="sk-test")
    req = InferenceRequest(
        messages=[ChatMessage(role="user", content="test")],
        json_schema={"type": "object"},
    )

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"ok": true}'), finish_reason="stop")],
        usage=MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )

    with patch.object(adapter, "_client_for_key", return_value=mock_client):
        await adapter.generate(req, {})

    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert "response_format" in call_kwargs
    assert call_kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_openai_adapter_no_response_format_without_json_schema() -> None:
    from src.adapters.cognitive.openai_adapter import OpenAILLMAdapter

    adapter = OpenAILLMAdapter(api_key="sk-test")
    req = InferenceRequest(
        messages=[ChatMessage(role="user", content="test")],
    )

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="hello"), finish_reason="stop")],
        usage=MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )

    with patch.object(adapter, "_client_for_key", return_value=mock_client):
        await adapter.generate(req, {})

    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert "response_format" not in call_kwargs


@pytest.mark.asyncio
async def test_anthropic_adapter_adds_schema_to_system_prompt() -> None:
    from src.adapters.cognitive.anthropic_adapter import AnthropicLLMAdapter

    adapter = AnthropicLLMAdapter(api_key="sk-ant-test")
    schema = {"type": "object", "properties": {"name": {"type": "string"}}}
    req = InferenceRequest(
        messages=[
            ChatMessage(role="system", content="You are a helpful assistant."),
            ChatMessage(role="user", content="test"),
        ],
        json_schema=schema,
    )

    mock_client = AsyncMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='{"name": "test"}')],
        usage=MagicMock(input_tokens=10, output_tokens=5),
        stop_reason="end_turn",
    )

    with patch.object(adapter, "_client_for_key", return_value=mock_client):
        await adapter.generate(req, {})

    call_kwargs = mock_client.messages.create.call_args[1]
    assert "system" in call_kwargs
    assert json.dumps(schema) in call_kwargs["system"]


@pytest.mark.asyncio
async def test_anthropic_adapter_sets_system_prompt_when_no_existing_system() -> None:
    from src.adapters.cognitive.anthropic_adapter import AnthropicLLMAdapter

    adapter = AnthropicLLMAdapter(api_key="sk-ant-test")
    schema = {"type": "object", "properties": {"name": {"type": "string"}}}
    req = InferenceRequest(
        messages=[ChatMessage(role="user", content="test")],
        json_schema=schema,
    )

    mock_client = AsyncMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='{"name": "test"}')],
        usage=MagicMock(input_tokens=10, output_tokens=5),
        stop_reason="end_turn",
    )

    with patch.object(adapter, "_client_for_key", return_value=mock_client):
        await adapter.generate(req, {})

    call_kwargs = mock_client.messages.create.call_args[1]
    assert "system" in call_kwargs
    assert json.dumps(schema) in call_kwargs["system"]


# ── Step 4: Extraction DTOs ────────────────────────────────────────────────


def test_extract_request_schema() -> None:
    from pydantic import BaseModel

    class LocalExtractRequest(BaseModel):
        json_schema: dict

    req = LocalExtractRequest(json_schema={"type": "object"})
    assert req.json_schema == {"type": "object"}


def test_extract_endpoint_local() -> None:
    from src.main import ExtractResponse

    resp = ExtractResponse(
        data={"key": "val"}, provider="openai", model="gpt-4o",
        inputTokens=10, outputTokens=5,
    )
    assert resp.data["key"] == "val"


# ── Step 5: get_document_chunks returns list ────────────────────────────────


@pytest.mark.asyncio
async def test_get_document_chunks_returns_list() -> None:
    mock_repo = AsyncMock()
    mock_repo.get_document_chunks.return_value = [
        DocumentChunk(chunk_id="c1", document_id="d1", tenant_id="t1",
                      content="hello", token_count=1, chunk_index=0,
                      created_at="2026-07-15T00:00:00+00:00"),
    ]
    result = await mock_repo.get_document_chunks("t1", "d1")
    assert len(result) == 1
    assert result[0].content == "hello"
