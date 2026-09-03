"""Tests for Scoping Intent Classification Endpoint (M85.11)."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.adapters.api.security import verify_tenant_or_admin
from src.domain.abstractions.inference import InferenceResponse, Usage
from src.main import app


@pytest.fixture(autouse=True)
def setup_dependency_overrides():
    """Automatically set up and clean up dependency overrides for each test."""
    app.dependency_overrides[verify_tenant_or_admin] = lambda: True
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {
        "Authorization": "Bearer test-admin-key",
        "X-Tenant-ID": "test-tenant",
    }


@pytest.mark.asyncio
async def test_classify_intent_success_mock_llm(auth_headers: dict[str, str]) -> None:
    mock_llm_json = {
        "archetype_id": "voice_ai_agent_app",
        "base_engine_id": "saas",
        "feature_ids": ["ai_voice_agent", "ai_rag", "auth", "admin", "email"],
        "brand_asset_id": "comprehensive",
        "maintenance_plan_id": "premium",
        "suggested_timeline": "4 to 5 Weeks",
        "confidence_score": 0.96,
        "summary_rationale": "Configured with conversational Voice AI agent and Retriever RAG.",
        "retriever_engine_recommended": True,
        "unrecognized_requirements": [],
    }

    mock_resp = InferenceResponse(
        content=json.dumps(mock_llm_json),
        usage=Usage(input_tokens=150, output_tokens=85, total_tokens=235),
        finish_reason="stop",
    )

    with patch("src.container.inference_orchestrator.llm.generate", new_callable=AsyncMock) as mock_gen, \
         patch("src.container.config_service.get_tenant_config", new_callable=AsyncMock) as mock_config:

        mock_gen.return_value = mock_resp
        mock_cfg = AsyncMock()
        mock_cfg.ai_provider.model = "meta-llama/llama-3.3-70b-instruct"
        mock_cfg.ai_provider.provider_name = "groq"
        mock_config.return_value = mock_cfg

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/tenants/test-tenant/intent/classify",
                headers=auth_headers,
                json={"prompt": "Build a conversational Voice AI calling bot with ElevenLabs and knowledge base"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["archetype_id"] == "voice_ai_agent_app"
        assert body["data"]["base_engine_id"] == "saas"
        assert "ai_voice_agent" in body["data"]["feature_ids"]
        assert body["data"]["confidence_score"] == 0.96
        assert body["data"]["retriever_engine_recommended"] is True
        assert body["inputTokens"] == 150
        assert body["outputTokens"] == 85
        assert body["latencyMs"] >= 0


@pytest.mark.asyncio
async def test_classify_intent_fallback_on_llm_error(auth_headers: dict[str, str]) -> None:
    with patch("src.container.inference_orchestrator.llm.generate", side_effect=RuntimeError("LLM offline")), \
         patch("src.container.config_service.get_tenant_config", new_callable=AsyncMock) as mock_config:

        mock_cfg = AsyncMock()
        mock_cfg.ai_provider.model = "meta-llama/llama-3.3-70b-instruct"
        mock_cfg.ai_provider.provider_name = "groq"
        mock_config.return_value = mock_cfg

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/tenants/test-tenant/intent/classify",
                headers=auth_headers,
                json={"prompt": "Build a private RAG knowledge base for internal document search"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["archetype_id"] == "ai_rag_app"
        assert body["data"]["base_engine_id"] == "saas"
        assert "ai_rag" in body["data"]["feature_ids"]
        assert body["provider"] == "fallback"


@pytest.mark.asyncio
async def test_classify_intent_rejects_empty_prompt(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/tenants/test-tenant/intent/classify",
            headers=auth_headers,
            json={"prompt": ""},
        )

    assert resp.status_code == 422
