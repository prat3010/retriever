"""Unit tests for Milestone 73: Closed-Loop Telemetry Self-Tuning Engine."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.domain.abstractions.config import TenantConfiguration
from src.domain.abstractions.graph import EntityTriple
from src.domain.evaluation.online_evaluator import (
    OnlineHallucinationEvaluator,
    QualityMetrics,
)
from src.domain.evaluation.self_tuner import SelfTuningEngine
from src.main import app

client = TestClient(app)


# ── 1. Unit Test: SelfTuningEngine Calculations ──────────────────────────────

def test_self_tuning_on_hallucination_spike():
    """Verify self-tuner raises rerank threshold and tightens RRF on faithfulness drop."""
    tuner = SelfTuningEngine()
    tenant_id = str(uuid.uuid4())

    current_settings = {
        "top_k": 5,
        "reranking_threshold": 0.30,
        "rrf_k": 60,
        "enable_hybrid": True,
        "enable_reranking": True,
        "enable_graph_search": False,
    }

    # Low faithfulness metrics (hallucination spike)
    metrics = [
        QualityMetrics(context_precision=0.40, answer_relevance=0.70, faithfulness=0.45),
        QualityMetrics(context_precision=0.50, answer_relevance=0.60, faithfulness=0.50),
    ]

    report = tuner.calculate_tuning(tenant_id, metrics, current_settings)

    assert report.status == "tuned"
    assert report.recommended_settings["reranking_threshold"] > 0.30
    assert report.recommended_settings["rrf_k"] < 60
    assert report.recommended_settings["enable_graph_search"] is True
    assert len(report.adjustments) > 0


def test_self_tuning_on_low_precision():
    """Verify self-tuner lowers top_k when context precision is low."""
    tuner = SelfTuningEngine()
    tenant_id = str(uuid.uuid4())

    current_settings = {
        "top_k": 6,
        "reranking_threshold": 0.30,
        "rrf_k": 60,
    }

    # Low precision metrics
    metrics = [
        QualityMetrics(context_precision=0.20, answer_relevance=0.80, faithfulness=0.85),
    ]

    report = tuner.calculate_tuning(tenant_id, metrics, current_settings)

    assert report.status == "tuned"
    assert report.recommended_settings["top_k"] == 5
    assert any("Reduced top_k" in adj for adj in report.adjustments)


def test_self_tuning_safety_bounds():
    """Verify parameters never exceed strict safety limits."""
    tuner = SelfTuningEngine()
    tenant_id = str(uuid.uuid4())

    # Settings already at boundary
    current_settings = {
        "top_k": 3,
        "reranking_threshold": 0.70,
        "rrf_k": 20,
    }

    # Even with low precision and faithfulness, cannot breach minimum top_k or max threshold
    metrics = [
        QualityMetrics(context_precision=0.10, answer_relevance=0.30, faithfulness=0.20),
    ]

    report = tuner.calculate_tuning(tenant_id, metrics, current_settings)

    assert report.recommended_settings["top_k"] >= tuner.MIN_TOP_K
    assert report.recommended_settings["reranking_threshold"] <= tuner.MAX_RERANK_THRESHOLD
    assert report.recommended_settings["rrf_k"] >= tuner.MIN_RRF_K


# ── 2. Unit Test: tune_and_apply Hot-Reload ──────────────────────────────────

@pytest.mark.asyncio
async def test_tune_and_apply_updates_config_service():
    """Verify tune_and_apply updates TenantConfiguration in ConfigurationService."""
    tuner = SelfTuningEngine()
    tenant_id = str(uuid.uuid4())

    mock_cfg = TenantConfiguration()
    mock_cfg.retrieval_settings.top_k = 5
    mock_cfg.retrieval_settings.reranking_threshold = 0.30

    mock_config_service = AsyncMock()
    mock_config_service.get_tenant_config.return_value = mock_cfg
    mock_config_service.update_tenant_config = AsyncMock()

    metrics = [
        QualityMetrics(context_precision=0.30, answer_relevance=0.50, faithfulness=0.40),
    ]

    report = await tuner.tune_and_apply(tenant_id, metrics, mock_config_service)

    assert report.status == "tuned"
    assert mock_config_service.update_tenant_config.called
    updated_cfg = mock_config_service.update_tenant_config.call_args[0][1]
    assert updated_cfg.retrieval_settings.reranking_threshold > 0.30


# ── 3. Unit Test: OnlineHallucinationEvaluator Closed Loop ───────────────────

@pytest.mark.asyncio
async def test_evaluator_closed_loop_trigger():
    """Verify OnlineHallucinationEvaluator triggers self-tuning on hallucination alerts."""
    mock_config_service = AsyncMock()
    mock_cfg = TenantConfiguration()
    mock_cfg.retrieval_settings.top_k = 5
    mock_cfg.retrieval_settings.reranking_threshold = 0.30
    mock_config_service.get_tenant_config.return_value = mock_cfg

    evaluator = OnlineHallucinationEvaluator(config_service=mock_config_service)

    tenant_id = str(uuid.uuid4())
    query = "What is the warranty period?"
    # Hallucinated answer with zero grounding in context
    answer = "Astronauts launch interplanetary spacecraft from orbital stations around Jupiter."
    contexts = ["The domestic refrigerator includes a 12-month standard hardware warranty."]

    res = await evaluator.evaluate_inference(
        tenant_id=tenant_id,
        query=query,
        answer=answer,
        contexts=contexts,
    )

    assert res["status"] == "evaluated"
    assert res["is_alert"] is True
    assert "self_tuning" in res
    assert res["self_tuning"]["status"] in ("tuned", "stable")


# ── 4. API Test: Admin Endpoints ─────────────────────────────────────────────

@pytest.mark.asyncio
@patch("src.container.container")
async def test_admin_detect_communities_endpoint(mock_container):
    """Verify POST /v1/admin/tenants/{tenantId}/graph/communities/detect."""
    from src.config import settings

    tenant_id = str(uuid.uuid4())
    mock_repo = AsyncMock()
    mock_repo.get_all_triples.return_value = [
        EntityTriple(subject="Auth", predicate="USES", object="JWT"),
        EntityTriple(subject="Payment", predicate="USES", object="Stripe"),
    ]
    mock_container.graph_repository = mock_repo

    response = client.post(
        f"/v1/admin/tenants/{tenant_id}/graph/communities/detect",
        headers={"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY},
        json={"max_levels": 2, "resolution": 1.0, "generate_summaries": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == tenant_id
    assert data["total_communities"] >= 1
    assert "0" in data["levels"]


@pytest.mark.asyncio
@patch("src.container.container")
async def test_admin_self_tune_endpoint(mock_container):
    """Verify POST /v1/admin/tenants/{tenantId}/eval/self-tune."""
    from src.config import settings

    tenant_id = str(uuid.uuid4())
    mock_cfg_svc = AsyncMock()
    mock_cfg = TenantConfiguration()
    mock_cfg.retrieval_settings.top_k = 5
    mock_cfg.retrieval_settings.reranking_threshold = 0.30
    mock_cfg_svc.get_tenant_config.return_value = mock_cfg
    mock_container.configuration_service = mock_cfg_svc

    response = client.post(
        f"/v1/admin/tenants/{tenant_id}/eval/self-tune",
        headers={"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY},
        json={"apply_changes": False},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == tenant_id
    assert "recommended_settings" in data
    assert "adjustments" in data


