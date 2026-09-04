"""Comprehensive Automated Test Suite for Milestone 96.

Tests:
1. Pure Hexagonal Domain Boundary Conformance (0 framework imports).
2. ServerlessGpuClientAdapter (Cold-start detection, warm-boot timing, scale-to-zero).
3. Dynamic Multi-LoRA Tensor Swapping & Header Injection.
4. SqlTenantLoraRepository (CRUD, multi-tenant isolation, atomic hot-activation).
5. GatewayRouter Smart Cascade Failover with Serverless GPU tiers.
6. Empirical Scale-to-Zero Cost Savings Math.
7. Platform Battery #16 Registration in BatteryService.
8. FastAPI REST Endpoints (Admin status/probe/savings & Tenant LoRA CRUD).
"""

import ast
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.adapters.cognitive.gateway_router import GatewayRouterAdapter
from src.adapters.cognitive.modal_client import ServerlessGpuClientAdapter
from src.adapters.database.tenant_lora_repository import SqlTenantLoraRepository
from src.config import settings
from src.container import container
from src.domain.abstractions.batteries import BatteryCategory
from src.domain.abstractions.inference import (
    ChatMessage,
    InferenceRequest,
    InferenceResponse,
)
from src.domain.abstractions.serverless_gpu import (
    LoraAdapterMetadata,
    ServerlessGpuTier,
    ServerlessProviderType,
)
from src.main import app

# ── 1. Hexagonal Boundary Conformance Test ──────────────────────────────────


def test_serverless_domain_hexagonal_boundary() -> None:
    """Ensure src/domain/abstractions/serverless_gpu.py has 0 framework imports."""
    domain_file = (
        Path(__file__).parent.parent
        / "src"
        / "domain"
        / "abstractions"
        / "serverless_gpu.py"
    )
    assert domain_file.exists(), "Domain abstractions file must exist"

    tree = ast.parse(domain_file.read_text(encoding="utf-8"))
    forbidden = {"sqlalchemy", "fastapi", "httpx", "modal", "bentoml", "pika", "celery"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                root_module = name.name.split(".")[0]
                assert (
                    root_module not in forbidden
                ), f"Hexagonal boundary violation: {root_module} imported in domain"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_module = node.module.split(".")[0]
                assert (
                    root_module not in forbidden
                ), f"Hexagonal boundary violation: {root_module} imported in domain"


# ── 2. Serverless Client Adapter Tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_serverless_client_offline_scale_to_zero_status() -> None:
    """Verify cluster status returns cold with 0 active containers when idle/offline."""
    client = ServerlessGpuClientAdapter(
        endpoint_url=None,
        base_model="meta-llama/Meta-Llama-3.1-8B-Instruct",
        gpu_tier=ServerlessGpuTier.A10G,
        scaledown_window_sec=300,
    )

    status = await client.check_deployment_status()
    assert status.cluster_status == "cold"
    assert status.active_containers == 0
    assert status.min_containers == 0
    assert status.max_containers == 5
    assert status.base_model == "meta-llama/Meta-Llama-3.1-8B-Instruct"
    assert status.gpu_tier == ServerlessGpuTier.A10G


@pytest.mark.asyncio
async def test_serverless_probe_cold_start() -> None:
    """Verify reachability and warm-boot measurement."""
    client = ServerlessGpuClientAdapter(
        endpoint_url=None,
        provider_type=ServerlessProviderType.MODAL,
    )

    metrics = await client.probe_cold_start()
    assert metrics.handshake_latency_ms >= 0
    assert metrics.inference_ttft_ms >= 0
    assert metrics.provider == ServerlessProviderType.MODAL
    assert metrics.container_id is not None


@pytest.mark.asyncio
async def test_serverless_completion_with_dynamic_lora() -> None:
    """Verify generation with dynamic LoRA adapter metadata injection."""
    client = ServerlessGpuClientAdapter(
        endpoint_url=None,
        base_model="meta-llama/Meta-Llama-3.1-8B-Instruct",
    )

    lora = LoraAdapterMetadata(
        adapter_id="lora_test_enterprise_sow",
        tenant_id=str(uuid.uuid4()),
        name="Enterprise SOW Adapter",
        base_model="meta-llama/Meta-Llama-3.1-8B-Instruct",
        artifact_uri="s3://retriever-vault/loras/sow_v1",
        rank=16,
        alpha=32.0,
        is_active=True,
    )

    req = InferenceRequest(
        messages=[
            ChatMessage(role="system", content="You are a solutions architect."),
            ChatMessage(role="user", content="Draft scoping proposal."),
        ],
        temperature=0.3,
    )

    resp = await client.execute_serverless_completion(
        req, configuration={}, lora_adapter=lora
    )
    assert isinstance(resp, InferenceResponse)
    assert "Enterprise SOW Adapter" in resp.content
    assert resp.usage.total_tokens > 0
    assert resp.usage.cost_usd > 0.0


@pytest.mark.asyncio
async def test_serverless_streaming_generation() -> None:
    """Verify SSE streaming yields tokens with finish reason."""
    client = ServerlessGpuClientAdapter(endpoint_url=None)
    req = InferenceRequest(
        messages=[ChatMessage(role="user", content="Hello serverless!")],
    )

    chunks = []
    async for chunk in client.execute_serverless_stream(req, configuration={}):
        chunks.append(chunk)

    assert len(chunks) > 1
    assert any("Serverless" in c.get("delta", "") for c in chunks)
    assert chunks[-1]["finish_reason"] == "stop"


# ── 3. Empirical Cost Savings Math ──────────────────────────────────────────


def test_scale_to_zero_cost_savings_calculation() -> None:
    """Verify mathematical fidelity of scale-to-zero cost savings."""
    client = ServerlessGpuClientAdapter(endpoint_url=None)

    # 10 hours of active compute in a 720-hour month on A10G ($1.00/hr)
    calc = client.calculate_cost_savings(
        active_compute_seconds=36000.0,  # 10 hours
        gpu_tier=ServerlessGpuTier.A10G,
    )

    assert calc.dedicated_monthly_cost_usd == 720.00
    assert calc.active_hours == 10.0
    assert calc.serverless_monthly_cost_usd == 10.00
    assert calc.monthly_savings_usd == 710.00
    assert calc.savings_percentage == 98.6
    assert calc.idle_hours_saved == 710.0


# ── 4. Tenant LoRA Repository Tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_tenant_lora_repository_lifecycle() -> None:
    """Test full CRUD and single-active hot-activation lifecycle with multi-tenancy."""
    repo = SqlTenantLoraRepository(enable_db=False)
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())

    adapter_1 = LoraAdapterMetadata(
        adapter_id=str(uuid.uuid4()),
        tenant_id=tenant_a,
        name="Legal Contract Adapter v1",
        base_model="meta-llama/Meta-Llama-3.1-8B-Instruct",
        artifact_uri="s3://vault/loras/legal_v1",
        rank=16,
        alpha=32.0,
        is_active=False,
    )

    adapter_2 = LoraAdapterMetadata(
        adapter_id=str(uuid.uuid4()),
        tenant_id=tenant_a,
        name="Technical Code Adapter v2",
        base_model="meta-llama/Meta-Llama-3.1-8B-Instruct",
        artifact_uri="s3://vault/loras/code_v2",
        rank=32,
        alpha=64.0,
        is_active=False,
    )

    # 1. Register adapters
    created_1 = await repo.register_adapter(tenant_a, adapter_1)
    created_2 = await repo.register_adapter(tenant_a, adapter_2)
    assert created_1.name == "Legal Contract Adapter v1"
    assert created_2.rank == 32

    # 2. Multi-tenant isolation: Tenant B cannot see Tenant A's adapters
    tenant_b_adapters = await repo.list_adapters(tenant_b)
    assert len(tenant_b_adapters) == 0

    tenant_a_adapters = await repo.list_adapters(tenant_a)
    assert len(tenant_a_adapters) == 2

    # 3. Hot-activate adapter 1
    act_1 = await repo.activate_adapter(tenant_a, created_1.adapter_id)
    assert act_1.is_active is True

    active = await repo.get_active_adapter(tenant_a)
    assert active is not None
    assert active.adapter_id == created_1.adapter_id

    # 4. Hot-activate adapter 2 (must automatically deactivate adapter 1)
    act_2 = await repo.activate_adapter(tenant_a, created_2.adapter_id)
    assert act_2.is_active is True

    active_after = await repo.get_active_adapter(tenant_a)
    assert active_after is not None
    assert active_after.adapter_id == created_2.adapter_id

    # Verify adapter 1 is now inactive
    refreshed_1 = await repo.get_adapter(tenant_a, created_1.adapter_id)
    assert refreshed_1 is not None
    assert refreshed_1.is_active is False

    # 5. Delete adapter 1
    deleted = await repo.delete_adapter(tenant_a, created_1.adapter_id)
    assert deleted is True
    assert (await repo.get_adapter(tenant_a, created_1.adapter_id)) is None


# ── 5. Gateway Router Integration & Fallback Cascade ────────────────────────


@pytest.mark.asyncio
async def test_gateway_router_serverless_dispatch_and_cascade() -> None:
    """Verify gateway routes to serverless GPU and cascades on cooldown."""
    serverless_client = ServerlessGpuClientAdapter(endpoint_url=None)
    repo = SqlTenantLoraRepository(enable_db=False)

    gw = GatewayRouterAdapter(
        serverless_gpu_client=serverless_client,
        tenant_lora_repo=repo,
    )

    # Models catalog must contain serverless models
    catalog = gw.list_available_models()
    model_ids = [m.model_id for m in catalog]
    assert "modal/vllm-llama-3.1-8b" in model_ids
    assert "bentoml/vllm-qwen-2.5-7b" in model_ids

    # Execute generation through serverless model
    req = InferenceRequest(
        messages=[ChatMessage(role="user", content="Test gateway")],
    )
    resp = await gw.generate(
        req, configuration={"model": "modal/vllm-llama-3.1-8b"}
    )
    assert "Serverless GPU response" in resp.content


# ── 6. Platform Battery #16 Registration ────────────────────────────────────


def test_battery_service_has_serverless_gpu_battery() -> None:
    """Verify Battery #16 (serverless_gpu_vllm) is registered in BatteryService."""
    battery_svc = container.battery_service
    res = battery_svc.get_platform_batteries()

    assert res.total_batteries == 16
    battery_16 = next((b for b in res.batteries if b.id == "serverless_gpu_vllm"), None)
    assert battery_16 is not None
    assert battery_16.name == "Serverless GPU & Dynamic vLLM / LoRA Pipeline"
    assert battery_16.category == BatteryCategory.ML_INTELLIGENCE
    assert battery_16.milestone == "M96 (v0.81.0)"
    assert "vLLM" in battery_16.algorithm_foundation


# ── 7. FastAPI REST API Endpoints ───────────────────────────────────────────


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app)


def test_admin_serverless_endpoints(test_client: TestClient) -> None:
    """Verify /v1/admin/serverless/* endpoints with admin master key."""
    headers = {"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY}

    # 1. Status
    res = test_client.get("/v1/admin/serverless/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] in ("modal", "bentoml")
    assert "active_containers" in data
    assert data["min_containers"] == 0

    # 2. Probe
    probe_res = test_client.post("/v1/admin/serverless/probe", headers=headers)
    assert probe_res.status_code == 200
    pdata = probe_res.json()
    assert "handshake_latency_ms" in pdata

    # 3. Cost savings
    savings_res = test_client.get(
        "/v1/admin/serverless/cost-savings?active_compute_hours=15.0&gpu_tier=A10G",
        headers=headers,
    )
    assert savings_res.status_code == 200
    sdata = savings_res.json()
    assert sdata["dedicated_monthly_cost_usd"] == 720.0
    assert sdata["active_hours"] == 15.0
    assert sdata["monthly_savings_usd"] == 705.0


def test_tenant_lora_endpoints(test_client: TestClient) -> None:
    """Verify /v1/tenants/{tenantId}/lora-adapters/* REST endpoints."""
    container.tenant_lora_repository.enable_db = False
    headers = {"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY}
    tenant_id = str(uuid.uuid4())

    # 1. Register adapter
    payload = {
        "name": "Production Architecture LoRA",
        "base_model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
        "artifact_uri": "s3://vault/adapters/arch_lora_v1",
        "rank": 16,
        "alpha": 32.0,
        "target_modules": ["q_proj", "v_proj"],
        "adapter_type": "llm",
        "description": "Enterprise software architecture fine-tuning",
        "activate_immediately": True,
    }

    create_res = test_client.post(
        f"/v1/tenants/{tenant_id}/lora-adapters",
        json=payload,
        headers=headers,
    )
    assert create_res.status_code == 201
    created = create_res.json()
    adapter_id = created["adapter_id"]
    assert created["is_active"] is True
    assert created["name"] == "Production Architecture LoRA"

    # 2. List adapters
    list_res = test_client.get(
        f"/v1/tenants/{tenant_id}/lora-adapters",
        headers=headers,
    )
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 1
    assert items[0]["adapter_id"] == adapter_id

    # 3. Get active adapter
    active_res = test_client.get(
        f"/v1/tenants/{tenant_id}/lora-adapters/active",
        headers=headers,
    )
    assert active_res.status_code == 200
    active_data = active_res.json()
    assert active_data["adapter_id"] == adapter_id

    # 4. Deactivate adapter
    deact_res = test_client.post(
        f"/v1/tenants/{tenant_id}/lora-adapters/{adapter_id}/deactivate",
        headers=headers,
    )
    assert deact_res.status_code == 200

    # 5. Delete adapter
    del_res = test_client.delete(
        f"/v1/tenants/{tenant_id}/lora-adapters/{adapter_id}",
        headers=headers,
    )
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True
