"""Automated Verification Suite for Visitor Persona Clustering & Lead Propensity Classifier (Milestone 85)."""

import pytest
from apps.api.src.adapters.ml.scikit_persona_classifier import (
    ScikitLeadPropensityScorer,
    ScikitPersonaClusterer,
)
from apps.api.src.domain.abstractions.persona_classifier import (
    LeadFeatureVector,
    VisitorTelemetryVector,
)
from apps.api.src.domain.clustering.persona_service import PersonaIntelligenceService
from apps.api.src.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def clusterer():
    return ScikitPersonaClusterer(random_state=42)


@pytest.fixture
def lead_scorer():
    return ScikitLeadPropensityScorer(random_state=42)


@pytest.fixture
def service(clusterer, lead_scorer):
    return PersonaIntelligenceService(persona_classifier=clusterer, lead_scorer=lead_scorer)


@pytest.fixture
def client():
    return TestClient(app)


def test_visitor_persona_clustering_archetypes(clusterer):
    """Verify that distinct intent ratios reliably converge to canonical persona archetypes."""
    comm_vec = VisitorTelemetryVector(
        commercial_intent_ratio=0.85,
        credibility_intent_ratio=0.05,
        product_intent_ratio=0.05,
        content_intent_ratio=0.05,
        dwell_time_seconds=240,
        interaction_depth_score=0.7,
    )
    pred_comm = clusterer.classify_visitor(comm_vec)
    assert pred_comm.persona_category == "commercial_buyer"
    assert pred_comm.confidence_score > 0.6
    assert "Scoping Lab" in pred_comm.recommended_action

    tech_vec = VisitorTelemetryVector(
        commercial_intent_ratio=0.05,
        credibility_intent_ratio=0.05,
        product_intent_ratio=0.85,
        content_intent_ratio=0.05,
        dwell_time_seconds=300,
        interaction_depth_score=0.8,
    )
    pred_tech = clusterer.classify_visitor(tech_vec)
    assert pred_tech.persona_category == "technical_evaluator"
    assert "Retriever RAG" in pred_tech.recommended_action

    recruiter_vec = VisitorTelemetryVector(
        commercial_intent_ratio=0.05,
        credibility_intent_ratio=0.85,
        product_intent_ratio=0.05,
        content_intent_ratio=0.05,
        dwell_time_seconds=180,
        interaction_depth_score=0.5,
    )
    pred_recruiter = clusterer.classify_visitor(recruiter_vec)
    assert pred_recruiter.persona_category == "talent_recruiter"
    assert "Resume" in pred_recruiter.recommended_action

    peer_vec = VisitorTelemetryVector(
        commercial_intent_ratio=0.05,
        credibility_intent_ratio=0.05,
        product_intent_ratio=0.15,
        content_intent_ratio=0.75,
        dwell_time_seconds=120,
        interaction_depth_score=0.3,
    )
    pred_peer = clusterer.classify_visitor(peer_vec)
    assert pred_peer.persona_category == "community_peer"


def test_lead_propensity_scoring(lead_scorer):
    """Verify that lead attributes produce calibrated conversion probability and priority tiers."""
    high_value = LeadFeatureVector(
        company_size_tier=3,
        domain_vertical="ai_ml",
        role_seniority="engineering_leadership",
        tech_stack_affinity=0.90,
        budget_tier_usd=120000.0,
        is_remote=True,
    )
    score_high = lead_scorer.score_lead(high_value)
    assert score_high.conversion_probability >= 0.70
    assert score_high.priority_tier in ["A+ High Value", "B Qualified"]
    assert len(score_high.key_scoring_drivers) >= 2

    low_value = LeadFeatureVector(
        company_size_tier=1,
        domain_vertical="other",
        role_seniority="other",
        tech_stack_affinity=0.20,
        budget_tier_usd=5000.0,
        is_remote=False,
    )
    score_low = lead_scorer.score_lead(low_value)
    assert score_low.conversion_probability < score_high.conversion_probability
    assert score_low.priority_tier in ["B Qualified", "C Low Priority"]


def test_api_endpoints(client):
    """Verify HTTP 200 contracts for /v1/ml/classify-visitor and /v1/ml/score-lead."""
    visitor_payload = {
        "commercial_intent_ratio": 0.1,
        "credibility_intent_ratio": 0.8,
        "product_intent_ratio": 0.05,
        "content_intent_ratio": 0.05,
        "dwell_time_seconds": 150.0,
        "interaction_depth_score": 0.6,
    }
    v_res = client.post("/v1/ml/classify-visitor", json=visitor_payload)
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert "persona_category" in v_data
    assert "confidence_score" in v_data
    assert "recommended_action" in v_data

    lead_payload = {
        "company_size_tier": 4,
        "domain_vertical": "ai_ml",
        "role_seniority": "founder_cxo",
        "tech_stack_affinity": 0.85,
        "budget_tier_usd": 150000.0,
        "is_remote": True,
    }
    l_res = client.post("/v1/ml/score-lead", json=lead_payload)
    assert l_res.status_code == 200
    l_data = l_res.json()
    assert "conversion_probability" in l_data
    assert "priority_tier" in l_data
    assert "recommended_engagement_strategy" in l_data


def test_hexagonal_boundary_conformance():
    """Verify that domain persona clustering does not import infrastructure or framework modules."""
    import ast
    import os

    domain_file = os.path.join(
        os.path.dirname(__file__),
        "../src/domain/clustering/persona_service.py",
    )

    with open(domain_file) as f:
        tree = ast.parse(f.read())

    forbidden_modules = ["fastapi", "sqlalchemy", "starlette", "requests", "httpx", "sklearn"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for forbidden in forbidden_modules:
                    assert forbidden not in alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for forbidden in forbidden_modules:
                    assert forbidden not in node.module
