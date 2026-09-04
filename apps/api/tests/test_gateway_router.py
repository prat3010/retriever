"""Unit and Integration Tests for Milestone 93: Enterprise LLM Gateway & Smart Router."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.cognitive.gateway_router import CATALOG_MODELS, GatewayRouterAdapter
from src.domain.abstractions.config import (
    BudgetSettings,
    GatewaySettings,
    TenantConfiguration,
)
from src.domain.abstractions.gateway import (
    BudgetExceededError,
    GatewayModelInfo,
    GatewayProbeResult,
    ModelRoutingConfig,
    VirtualTenantBudget,
)
from src.domain.abstractions.inference import (
    ChatMessage,
    InferenceRequest,
    InferenceResponse,
    Usage,
)
from src.domain.inference.cost_calculator import calculate_cost
from src.domain.inference.orchestrator import InferenceOrchestrator


def test_gateway_abstractions_and_models():
    """Verify domain abstractions and models conform to Pydantic contracts."""
    info = GatewayModelInfo(
        model_id="gemini-2.5-flash",
        provider="gemini",
        name="Google Gemini 2.5 Flash",
        input_cost_per_1k=0.075,
        output_cost_per_1k=0.30,
        capabilities=["chat", "vision"],
    )
    assert info.model_id == "gemini-2.5-flash"
    assert info.provider == "gemini"
    assert info.health_status == "healthy"

    routing = ModelRoutingConfig(
        primary_model="gemini-2.5-flash",
        fallback_models=["openai/gpt-4o-mini", "ollama/qwen2.5:14b"],
        cooldown_seconds=45,
    )
    assert routing.cooldown_seconds == 45
    assert len(routing.fallback_models) == 2

    budget = VirtualTenantBudget(
        daily_budget=5.0,
        monthly_budget=50.0,
        hard_limit_action="block",
        current_monthly_spend=55.20,
        is_budget_exceeded=True,
    )
    assert budget.is_budget_exceeded is True
    assert budget.hard_limit_action == "block"

    err = BudgetExceededError("tenant-123", 55.20, 50.0, period="monthly")
    assert "tenant-123" in str(err)
    assert err.current_spend == 55.20


def test_cost_calculator_prefix_normalization():
    """Verify calculate_cost handles both prefixed and unprefixed models."""
    from src.domain.abstractions.config import DEFAULT_PRICING
    usage = Usage(input_tokens=1000, output_tokens=1000)

    # 1. Unprefixed model
    cost1 = calculate_cost(usage, "gpt-4o-mini", DEFAULT_PRICING)
    assert cost1 > 0

    # 2. Prefixed model
    cost2 = calculate_cost(usage, "openai/gpt-4o-mini", DEFAULT_PRICING)
    assert cost2 == cost1

    # 3. Claude model
    cost_claude = calculate_cost(usage, "anthropic/claude-3-haiku", DEFAULT_PRICING)
    assert cost_claude > 0


@pytest.mark.asyncio
async def test_gateway_router_catalog_and_probe():
    """Verify catalog listing and upstream provider probe."""
    mock_openai = MagicMock()
    mock_anthropic = MagicMock()
    router = GatewayRouterAdapter(openai_adapter=mock_openai, anthropic_adapter=mock_anthropic)

    models = router.list_available_models()
    assert len(models) >= len(CATALOG_MODELS)
    assert any(m.model_id == "gemini-2.5-flash" for m in models)
    assert any(m.model_id == "ollama/qwen2.5:14b" for m in models)

    probes = await router.probe_providers()
    assert len(probes) >= 4
    for probe in probes:
        assert isinstance(probe, GatewayProbeResult)
        assert probe.reachable is True
        assert probe.latency_ms > 0


@pytest.mark.asyncio
async def test_gateway_router_cascade_fallback_on_failure():
    """Verify seamless cascade to fallback model when primary model fails."""
    mock_openai = MagicMock()
    mock_anthropic = MagicMock()
    router = GatewayRouterAdapter(openai_adapter=mock_openai, anthropic_adapter=mock_anthropic)

    # Simulate failing primary model and succeeding fallback model
    call_counts = {"attempts": 0}

    async def mock_exec(model, req, cfg):
        call_counts["attempts"] += 1
        if model == "primary-failing-model":
            raise RuntimeError("Rate limit 429")
        return InferenceResponse(
            content=f"Answer from {model}",
            usage=Usage(input_tokens=10, output_tokens=10),
        )

    router._execute_generate = mock_exec

    req = InferenceRequest(messages=[ChatMessage(role="user", content="Hello")])
    cfg = {
        "primary_model": "primary-failing-model",
        "fallback_models": ["secondary-working-model"],
        "cooldown_seconds": 60,
    }

    res = await router.generate(req, cfg)
    assert "Answer from secondary-working-model" in res.content
    assert call_counts["attempts"] == 2
    assert cfg["_actual_model"] == "secondary-working-model"
    assert router._is_in_cooldown("primary-failing-model", 60) is True


@pytest.mark.asyncio
async def test_gateway_router_cooldown_circuit_breaker():
    """Verify model in active cooldown is bypassed immediately."""
    router = GatewayRouterAdapter()
    router._mark_failure("broken-model")

    assert router._is_in_cooldown("broken-model", cooldown_seconds=10) is True

    cfg = {
        "primary_model": "broken-model",
        "fallback_models": ["backup-model"],
        "cooldown_seconds": 10,
    }

    called_models = []

    async def mock_exec(model, req, config):
        called_models.append(model)
        return InferenceResponse(content="ok", usage=Usage())

    router._execute_generate = mock_exec
    req = InferenceRequest(messages=[ChatMessage(role="user", content="test")])

    await router.generate(req, cfg)
    # broken-model must be skipped due to active cooldown
    assert "broken-model" not in called_models
    assert "backup-model" in called_models


@pytest.mark.asyncio
async def test_orchestrator_budget_block_action():
    """Verify InferenceOrchestrator raises BudgetExceededError when hard_limit_action is 'block'."""
    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(return_value=InferenceResponse(content="ans", usage=Usage()))
    mock_prompt_builder = MagicMock()
    mock_prompt_builder.build_messages = AsyncMock(return_value=[ChatMessage(role="user", content="hi")])
    mock_citation_validator = MagicMock()
    mock_citation_validator.get_invalid_citations = MagicMock(return_value=[])
    mock_session_repo = MagicMock()
    mock_session_repo.get_messages = AsyncMock(return_value=[])
    mock_session_repo.add_message = AsyncMock()
    mock_log_writer = MagicMock()
    mock_log_writer.write_log = AsyncMock()

    mock_budget_repo = MagicMock()
    # Monthly spend $120 exceeds budget $100
    mock_budget_repo.get_tenant_spend = AsyncMock(return_value=(10.0, 120.0, {"gpt-4o": 120.0}))

    orchestrator = InferenceOrchestrator(
        llm_provider=mock_llm,
        prompt_builder=mock_prompt_builder,
        citation_validator=mock_citation_validator,
        session_repo=mock_session_repo,
        log_writer=mock_log_writer,
        budget_repository=mock_budget_repo,
    )

    t_cfg = TenantConfiguration(
        tenant_id=str(uuid.uuid4()),
        budget_settings=BudgetSettings(
            monthly_cost_budget=100.0,
            hard_limit_action="block",
        ),
    )

    with pytest.raises(BudgetExceededError) as exc_info:
        await orchestrator.generate(
            tenant_id=t_cfg.tenant_id,
            session_id=str(uuid.uuid4()),
            query="Summarize",
            context_chunks=[],
            tenant_config=t_cfg,
        )

    assert "exceeded monthly budget ceiling" in str(exc_info.value)
    mock_llm.generate.assert_not_called()


@pytest.mark.asyncio
async def test_orchestrator_budget_downgrade_free_action():
    """Verify InferenceOrchestrator downgrades to local free model when budget is breached."""
    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(return_value=InferenceResponse(content="ans", usage=Usage()))
    mock_prompt_builder = MagicMock()
    mock_prompt_builder.build_messages = AsyncMock(return_value=[ChatMessage(role="user", content="hi")])
    mock_citation_validator = MagicMock()
    mock_citation_validator.get_invalid_citations = MagicMock(return_value=[])
    mock_session_repo = MagicMock()
    mock_session_repo.get_messages = AsyncMock(return_value=[])
    mock_session_repo.add_message = AsyncMock()
    mock_log_writer = MagicMock()
    mock_log_writer.write_log = AsyncMock()

    mock_budget_repo = MagicMock()
    # Daily spend $15 exceeds daily budget $10
    mock_budget_repo.get_tenant_spend = AsyncMock(return_value=(15.0, 45.0, {}))

    orchestrator = InferenceOrchestrator(
        llm_provider=mock_llm,
        prompt_builder=mock_prompt_builder,
        citation_validator=mock_citation_validator,
        session_repo=mock_session_repo,
        log_writer=mock_log_writer,
        budget_repository=mock_budget_repo,
    )

    t_cfg = TenantConfiguration(
        tenant_id=str(uuid.uuid4()),
        budget_settings=BudgetSettings(
            daily_cost_budget=10.0,
            hard_limit_action="downgrade_free_model",
            free_fallback_model="ollama/qwen2.5:14b",
        ),
    )

    res = await orchestrator.generate(
        tenant_id=t_cfg.tenant_id,
        session_id=str(uuid.uuid4()),
        query="Explain",
        context_chunks=[],
        tenant_config=t_cfg,
    )

    assert res.content == "ans"
    mock_llm.generate.assert_called_once()
    passed_cfg = mock_llm.generate.call_args[0][1]
    assert passed_cfg["model"] == "ollama/qwen2.5:14b"
    assert passed_cfg["_budget_downgraded"] is True


@pytest.mark.asyncio
async def test_gateway_api_endpoints():
    """Verify REST API endpoints for models, probes, routes, and budgets."""
    from httpx import ASGITransport, AsyncClient

    from src.config import settings
    from src.container import container
    from src.main import app

    admin_key = settings.ADMIN_MASTER_KEY or "dev-admin-secret"
    headers = {"X-Admin-Master-Key": admin_key}
    tenant_id = str(uuid.uuid4())

    mock_config_service = MagicMock()
    tenant_cfg = TenantConfiguration(
        tenant_id=tenant_id,
        gateway_settings=GatewaySettings(primary_model="gemini-2.5-flash"),
        budget_settings=BudgetSettings(monthly_cost_budget=50.0),
    )
    mock_config_service.get_tenant_config = AsyncMock(return_value=tenant_cfg)
    mock_config_service.update_tenant_config = AsyncMock(return_value=None)

    mock_budget_repo = MagicMock()
    mock_budget_repo.get_tenant_budget = AsyncMock(
        return_value=VirtualTenantBudget(
            monthly_budget=50.0,
            hard_limit_action="downgrade_free_model",
            current_monthly_spend=12.5,
        )
    )

    with container.override("config_service", mock_config_service), container.override("budget_repo", mock_budget_repo):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. List catalog models
            res_models = await client.get("/v1/gateway/models")
            assert res_models.status_code == 200
            models_data = res_models.json()
            assert len(models_data) >= 5
            assert any(m["model_id"] == "gemini-2.5-flash" for m in models_data)

            # 2. Probe upstream providers
            res_probe = await client.post("/v1/gateway/probe", headers=headers)
            assert res_probe.status_code == 200
            probe_data = res_probe.json()
            assert len(probe_data) >= 4
            assert any(p["provider"] == "gemini" for p in probe_data)

            # 3. Update tenant gateway routes & budget
            update_payload = {
                "primary_model": "gemini-2.5-flash",
                "fallback_models": ["openai/gpt-4o-mini", "ollama/qwen2.5:14b"],
                "latency_sla_ms": 3500,
                "cooldown_seconds": 45,
                "daily_cost_budget": 5.0,
                "monthly_cost_budget": 50.0,
                "hard_limit_action": "downgrade_free_model",
                "free_fallback_model": "ollama/qwen2.5:14b",
                "currency": "USD",
            }
            res_put = await client.put(
                f"/v1/tenants/{tenant_id}/gateway/routes",
                json=update_payload,
                headers=headers,
            )
            assert res_put.status_code == 200
            put_data = res_put.json()
            assert put_data["status"] == "updated"
            assert put_data["gateway_settings"]["primary_model"] == "gemini-2.5-flash"
            assert put_data["budget_settings"]["monthly_cost_budget"] == 50.0

            # 4. Get tenant gateway routes
            res_routes = await client.get(
                f"/v1/tenants/{tenant_id}/gateway/routes",
                headers=headers,
            )
            assert res_routes.status_code == 200
            routes_data = res_routes.json()
            assert routes_data["gateway_settings"]["primary_model"] == "gemini-2.5-flash"
            assert routes_data["budget_settings"]["monthly_cost_budget"] == 50.0

            # 5. Get tenant virtual budget
            res_budget = await client.get(
                f"/v1/tenants/{tenant_id}/gateway/budget",
                headers=headers,
            )
            assert res_budget.status_code == 200
            budget_data = res_budget.json()
            assert budget_data["monthly_budget"] == 50.0
            assert budget_data["hard_limit_action"] == "downgrade_free_model"
            assert "current_monthly_spend" in budget_data


def test_hexagonal_architecture_boundaries():
    """Verify gateway abstractions contain ZERO infrastructure framework imports."""
    import inspect

    import src.domain.abstractions.gateway as gw_module

    source = inspect.getsource(gw_module)
    forbidden = ["fastapi", "sqlalchemy", "litellm", "openai", "anthropic", "asyncpg"]
    for word in forbidden:
        assert f"import {word}" not in source, f"Hexagonal boundary violation: {word} found in domain abstractions!"
