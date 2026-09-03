"""Automated Verification Suite for Scikit-Learn Project Effort & Sprint Timeline Regression (Milestone 84)."""

import pytest
from apps.api.src.adapters.ml.scikit_effort_regressor import ScikitEffortRegressor
from apps.api.src.domain.abstractions.effort_estimation import (
    ProjectScopeInput,
    ScopeFeatureVector,
)
from apps.api.src.domain.estimation.effort_estimation_service import (
    EffortEstimationService,
)
from apps.api.src.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def regressor():
    return ScikitEffortRegressor(random_state=42)


@pytest.fixture
def service(regressor):
    return EffortEstimationService(regressor)


@pytest.fixture
def client():
    return TestClient(app)


def test_effort_regressor_quantiles(regressor):
    """Verify that P90 is always strictly greater than P50 with a risk buffer."""
    test_vectors = [
        ScopeFeatureVector(engine_id="landing", total_features=1),
        ScopeFeatureVector(engine_id="multipage", total_features=4, auth_security_count=1),
        ScopeFeatureVector(engine_id="saas", total_features=8, ai_vector_count=2, realtime_voice_count=1),
    ]

    for v in test_vectors:
        pred = regressor.predict_effort(v)
        assert pred.hours_p90 >= pred.hours_p50 * 1.15
        assert pred.calendar_days_max >= pred.calendar_days_min
        assert 1.0 <= pred.complexity_index <= 5.0
        assert pred.confidence_score > 0.8


def test_effort_regressor_monotonicity(regressor):
    """Verify that expanding architectural scope monotonically increases hours and complexity."""
    simple_landing = ScopeFeatureVector(engine_id="landing", total_features=0, dependency_depth=1)
    complex_saas = ScopeFeatureVector(
        engine_id="saas",
        total_features=8,
        auth_security_count=1,
        database_storage_count=1,
        ai_vector_count=2,
        realtime_voice_count=1,
        payment_billing_count=1,
        admin_rbac_count=1,
        dependency_depth=4,
        brand_complexity_weight=2.0,
    )

    pred_simple = regressor.predict_effort(simple_landing)
    pred_complex = regressor.predict_effort(complex_saas)

    assert pred_complex.hours_p50 > pred_simple.hours_p50
    assert pred_complex.hours_p90 > pred_simple.hours_p90
    assert pred_complex.complexity_index > pred_simple.complexity_index
    assert pred_complex.calendar_days_max > pred_simple.calendar_days_max


def test_service_risk_factors_and_drivers(service):
    """Verify that high-variance features trigger contextual risk warnings and drivers."""
    scope = ProjectScopeInput(
        engine_id="saas",
        feature_ids=[
            "realtime_voice_agent_app",
            "ai_rag_app",
            "razorpay_checkout",
            "admin_crm",
        ],
        brand_asset_id="brand_complete",
        maintenance_plan_id="care_enterprise",
    )

    pred = service.estimate(scope)

    assert len(pred.risk_factors) >= 1
    assert any("Voice AI" in rf or "WebRTC" in rf for rf in pred.risk_factors)
    assert len(pred.top_effort_drivers) >= 2
    # Verify driver ordering (Voice should be top estimate)
    assert pred.top_effort_drivers[0].added_hours_estimate >= pred.top_effort_drivers[1].added_hours_estimate


def test_scoping_estimate_timeline_api_endpoint(client):
    """Verify HTTP 200 response and structured contract from /v1/scoping/estimate-timeline."""
    payload = {
        "engine_id": "saas",
        "feature_ids": ["auth_portal", "ai_rag_app", "admin_dashboard"],
        "brand_asset_id": "brand_essential",
        "maintenance_plan_id": "care_basic",
        "custom_notes": "Fast-turnaround MVP for fintech client",
    }

    response = client.post("/v1/scoping/estimate-timeline", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "hours_p50" in data
    assert "hours_p90" in data
    assert "calendar_days_min" in data
    assert "calendar_days_max" in data
    assert "complexity_index" in data
    assert "recommended_sprint_weeks" in data
    assert data["hours_p90"] >= data["hours_p50"]
    assert data["calendar_days_max"] >= data["calendar_days_min"]


def test_hexagonal_boundary_conformance():
    """Verify that domain estimation modules do not import infrastructure or framework packages."""
    import ast
    import os

    domain_file = os.path.join(
        os.path.dirname(__file__),
        "../src/domain/estimation/effort_estimation_service.py"
    )

    with open(domain_file) as f:
        tree = ast.parse(f.read())

    forbidden_modules = ["fastapi", "sqlalchemy", "starlette", "requests", "httpx", "sklearn"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for forbidden in forbidden_modules:
                    assert forbidden not in alias.name, f"Domain violates Hexagonal boundary: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for forbidden in forbidden_modules:
                    assert forbidden not in node.module, f"Domain violates Hexagonal boundary: {node.module}"
