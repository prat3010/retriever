"""Generative Inference Tests.

Verifies:
- PromptBuilder template resolution and token compression
- CitationValidator citation extraction and validation
- InferenceOrchestrator pipeline dispatch
- OpenAI adapter lazy initialization
- Chat session API endpoints
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.domain.abstractions.identity import UserContext
from src.domain.abstractions.inference import (
    ChatMessage,
    InferenceResponse,
    PromptTemplate,
    Usage,
)
from src.domain.abstractions.retrieval import SearchResult
from src.domain.inference.citation_validator import CitationValidator
from src.domain.inference.orchestrator import InferenceOrchestrator
from src.domain.inference.prompt_builder import PromptBuilder
from src.main import app

client = TestClient(app)


# ── 1. PromptBuilder ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_prompt_builder_fails_when_no_template() -> None:
    """Verify builder raises when no template is found in DB."""
    from src.domain.abstractions.exceptions import PromptTemplateNotFoundError

    mock_registry = AsyncMock()
    mock_registry.get_template.return_value = None

    builder = PromptBuilder(template_registry=mock_registry)
    with pytest.raises(PromptTemplateNotFoundError):
        await builder.build_messages(
            tenant_id="t1",
            query="test query",
            history=[],
            context_chunks=[],
        )


@pytest.mark.asyncio
async def test_prompt_builder_uses_template() -> None:
    """Verify builder uses the system prompt template from registry."""
    mock_registry = AsyncMock()
    mock_registry.get_template.return_value = PromptTemplate(
        name="default",
        content="Custom system prompt from DB.",
    )

    builder = PromptBuilder(template_registry=mock_registry)
    messages = await builder.build_messages(
        tenant_id="t1",
        query="test query",
        history=[],
        context_chunks=[],
    )

    assert messages[0].content == "Custom system prompt from DB."


@pytest.mark.asyncio
async def test_prompt_builder_injects_context() -> None:
    """Verify context chunks are included in the prompt."""
    mock_registry = AsyncMock()
    mock_registry.get_template.return_value = PromptTemplate(
        name="default",
        content="You are a helpful grounding assistant.",
    )

    builder = PromptBuilder(template_registry=mock_registry)
    messages = await builder.build_messages(
        tenant_id="t1",
        query="what is the budget?",
        history=[],
        context_chunks=[
            {"chunk_id": "chk_001", "content": "Budget is $450k."},
        ],
    )

    context_msg = messages[1] if len(messages) > 1 else messages[0]
    assert "[Source: chk_001]" in context_msg.content
    assert "Budget is $450k." in context_msg.content


@pytest.mark.asyncio
async def test_prompt_builder_compression_trims_history() -> None:
    """Verify compression removes oldest history when over token budget."""
    mock_registry = AsyncMock()
    mock_registry.get_template.return_value = PromptTemplate(
        name="default",
        content="You are a helpful grounding assistant.",
    )

    builder = PromptBuilder(template_registry=mock_registry)
    long_history = [
        ChatMessage(role="user", content="x" * 2000),
        ChatMessage(role="assistant", content="y" * 2000),
        ChatMessage(role="user", content="z" * 2000),
    ]

    messages = await builder.build_messages(
        tenant_id="t1",
        query="short query",
        history=long_history,
        context_chunks=[{"chunk_id": "chk_001", "content": "short"}],
        max_tokens=500,
    )

    # Should have been compressed below 500 tokens
    total_chars = sum(len(m.content) for m in messages)
    assert total_chars <= 500 * 4 + 100  # ~4 chars/token with margin


# ── 2. CitationValidator ────────────────────────────────────────────────────


def test_citation_validator_extract() -> None:
    """Verify citations are extracted correctly."""
    v = CitationValidator()
    text = "The budget is [Source: chk_001] and [Source: chk_002]."
    citations = v.extract_citations(text)
    assert citations == ["chk_001", "chk_002"]


def test_citation_validator_no_citations() -> None:
    """Verify empty result when no citations present."""
    v = CitationValidator()
    assert v.extract_citations("No sources here.") == []


def test_citation_validator_validates() -> None:
    """Verify validation passes for known chunk IDs."""
    v = CitationValidator()
    v.set_valid_ids(["chk_001", "chk_002"])
    assert v.validate("Content [Source: chk_001] is valid.")
    assert not v.validate("Content [Source: chk_999] is invalid.")


def test_citation_validator_invalid_list() -> None:
    """Verify get_invalid_citations returns only unmatched IDs."""
    v = CitationValidator()
    v.set_valid_ids(["chk_001"])
    invalid = v.get_invalid_citations("[Source: chk_001] and [Source: chk_999]")
    assert invalid == ["chk_999"]


# ── 3. OpenAI Adapter Lazy Init ────────────────────────────────────────────


def test_openai_adapter_lazy_init() -> None:
    """Verify adapter does not fail at init — client created lazily."""
    from src.adapters.cognitive.openai_adapter import OpenAILLMAdapter

    adapter = OpenAILLMAdapter(api_key="test-key")  # no error at init
    assert adapter.client is not None  # property creates client


# ── 4. InferenceOrchestrator ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_orchestrator_generate_success() -> None:
    """Verify orchestrator executes full pipeline with mocked dependencies."""
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = InferenceResponse(
        content="Budget is $450k. [Source: chk_001]",
        usage=Usage(input_tokens=50, output_tokens=10, total_tokens=60),
    )

    mock_registry = AsyncMock()
    mock_registry.get_template.return_value = PromptTemplate(
        name="default",
        content="You are a helpful grounding assistant.",
    )

    mock_session_repo = AsyncMock()
    mock_session_repo.get_messages.return_value = []
    mock_session_repo.add_message.return_value = None

    mock_log_writer = AsyncMock()

    orchestrator = InferenceOrchestrator(
        llm_provider=mock_llm,
        prompt_builder=PromptBuilder(template_registry=mock_registry),
        citation_validator=CitationValidator(),
        session_repo=mock_session_repo,
        log_writer=mock_log_writer,
    )

    from src.domain.abstractions.config import TenantConfiguration

    config = TenantConfiguration(tenant_id="t1")
    context_chunks = [
        SearchResult(
            chunk_id="chk_001",
            document_id="doc_001",
            content="Budget is $450k.",
            score=0.95,
        )
    ]

    response = await orchestrator.generate(
        tenant_id="t1",
        session_id="ses_001",
        query="What's the budget?",
        context_chunks=context_chunks,
        tenant_config=config,
    )

    assert "Budget is $450k." in response.content
    mock_llm.generate.assert_called_once()
    mock_session_repo.get_messages.assert_awaited_once_with("t1", "ses_001")
    mock_session_repo.add_message.assert_any_await(
        "t1", "ses_001", ChatMessage(role="user", content="What's the budget?"), None
    )
    mock_session_repo.add_message.assert_any_await(
        "t1",
        "ses_001",
        ChatMessage(role="assistant", content="Budget is $450k. [Source: chk_001]"),
        None,
    )
    mock_log_writer.write_log.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_create_session() -> None:
    """Verify session creation delegates to repository."""
    mock_llm = AsyncMock()
    mock_registry = AsyncMock()
    mock_session_repo = AsyncMock()
    mock_session_repo.create_session.return_value = MagicMock(
        session_id="ses_001", tenant_id="t1", created_at="2026-01-01T00:00:00"
    )
    mock_log_writer = AsyncMock()

    orchestrator = InferenceOrchestrator(
        llm_provider=mock_llm,
        prompt_builder=PromptBuilder(template_registry=mock_registry),
        citation_validator=CitationValidator(),
        session_repo=mock_session_repo,
        log_writer=mock_log_writer,
    )

    session = await orchestrator.create_session("t1")
    assert session.session_id == "ses_001"
    mock_session_repo.create_session.assert_called_once_with("t1", None)


# ── 5. Chat API Endpoints ──────────────────────────────────────────────────


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.main.inference_orchestrator.create_session", new_callable=AsyncMock)
def test_create_chat_session_endpoint(
    mock_create_session, mock_validate
) -> None:
    """Verify POST /v1/tenants/{tenantId}/chat/sessions returns 201."""
    tenant_id = str(uuid.uuid4())
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id=tenant_id,
        roles=["client"],
        scopes=["document:write"],
    )
    mock_create_session.return_value = MagicMock(
        session_id="ses_001", tenant_id=tenant_id, created_at="2026-01-01T00:00:00"
    )

    headers = {"Authorization": "Bearer ret_live_validtoken.secret", "X-User-ID": "user_42"}
    response = client.post(
        f"/v1/tenants/{tenant_id}/chat/sessions",
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert "sessionId" in body
    assert body["sessionId"] == "ses_001"


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.main.inference_orchestrator.get_session", new_callable=AsyncMock)
@patch("src.main.config_service.get_tenant_config", new_callable=AsyncMock)
@patch("src.main.search_service.search", new_callable=AsyncMock)
@patch("src.main.inference_orchestrator.generate", new_callable=AsyncMock)
def test_chat_message_endpoint_non_streaming(
    mock_generate, mock_search, mock_get_config,
    mock_get_session, mock_validate,
) -> None:
    """Verify POST chat/messages returns non-streaming response."""
    from src.domain.abstractions.config import TenantConfiguration
    from src.domain.abstractions.retrieval import SearchMeta, SearchResponse

    tenant_id = str(uuid.uuid4())
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id=tenant_id,
        roles=["client"],
        scopes=["document:write"],
    )
    mock_get_session.return_value = MagicMock(
        session_id="ses_001", tenant_id=tenant_id
    )
    mock_get_config.return_value = TenantConfiguration(tenant_id=tenant_id)
    mock_search.return_value = SearchResponse(
        query="test",
        results=[],
        search_meta=SearchMeta(strategy="none", total_candidates=0, returned_results=0, duration_ms=0),
    )
    mock_generate.return_value = InferenceResponse(
        content="Test response",
        usage=Usage(input_tokens=10, output_tokens=5, total_tokens=15),
        finish_reason="stop",
    )

    headers = {"Authorization": "Bearer ret_live_validtoken.secret", "X-User-ID": "user_42"}
    response = client.post(
        f"/v1/tenants/{tenant_id}/chat/sessions/ses_001/messages",
        json={"query": "test", "stream": False},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["content"] == "Test response"
    assert body["finish_reason"] == "stop"


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.main.inference_orchestrator.get_session", new_callable=AsyncMock)
def test_chat_message_requires_auth(mock_get_session, mock_validate) -> None:
    """Verify chat message endpoint rejects requests without authorization."""
    tenant_id = str(uuid.uuid4())
    mock_get_session.return_value = MagicMock(session_id="ses_001")

    response = client.post(
        f"/v1/tenants/{tenant_id}/chat/sessions/ses_001/messages",
        json={"query": "test"},
    )
    assert response.status_code == 401


@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.main.inference_orchestrator.get_session", new_callable=AsyncMock)
def test_chat_message_session_not_found(mock_get_session, mock_validate) -> None:
    """Verify chat message returns 404 for non-existent session."""

    tenant_id = str(uuid.uuid4())
    mock_validate.return_value = UserContext(
        user_id="user_123",
        tenant_id=tenant_id,
        roles=["client"],
        scopes=["document:write"],
    )
    mock_get_session.return_value = None

    headers = {"Authorization": "Bearer ret_live_validtoken.secret", "X-User-ID": "user_42"}
    response = client.post(
        f"/v1/tenants/{tenant_id}/chat/sessions/nonexistent/messages",
        json={"query": "test"},
        headers=headers,
    )
    assert response.status_code == 404
