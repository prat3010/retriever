"""Unit tests for Scikit-Learn Isolation Forest & Robust Statistical Anomaly Detector (Milestone 83)."""

from datetime import UTC, datetime, timedelta

from src.adapters.cognitive.anomaly_detector_adapter import (
    FEATURE_NAMES,
    AnomalyDetectorAdapter,
)
from src.domain.abstractions.anomaly import AnomalyFeatureVector, AnomalyScore


def create_vector(
    entity_id: str,
    velocity: float = 10.0,
    token_ratio: float = 1.5,
    entropy: float = 3.5,
    latency_ms: float = 250.0,
    latency_var: float = 500.0,
    error_rate: float = 0.01,
    cost_usd: float = 0.05,
    tenant_id: str = "tn_test_m83",
) -> AnomalyFeatureVector:
    now = datetime.now(UTC)
    return AnomalyFeatureVector(
        entity_id=entity_id,
        entity_type="api_key",
        tenant_id=tenant_id,
        window_start=now - timedelta(minutes=60),
        window_end=now,
        request_count=int(velocity * 60),
        request_velocity_rpm=velocity,
        input_tokens_avg=500.0,
        output_tokens_avg=300.0,
        token_ratio=token_ratio,
        prompt_entropy=entropy,
        p99_latency_ms=latency_ms,
        latency_variance=latency_var,
        error_rate=error_rate,
        cost_velocity_usd=cost_usd,
    )


def test_empty_vectors_batch():
    """Verify empty input list returns empty list without error."""
    detector = AnomalyDetectorAdapter()
    results = detector.batch_detect([])
    assert results == []


def test_single_vector_scoring():
    """Verify single vector produces a valid calibrated AnomalyScore."""
    detector = AnomalyDetectorAdapter()
    vec = create_vector("key_nominal_1")
    score = detector.score(vec)

    assert isinstance(score, AnomalyScore)
    assert score.entity_id == "key_nominal_1"
    assert 0.0 <= score.anomaly_score <= 1.0
    assert score.risk_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert isinstance(score.features, dict)
    assert set(score.features.keys()) == set(FEATURE_NAMES)


def test_isolation_forest_outlier_detection():
    """Verify IsolationForest clearly separates nominal traffic from high-velocity prompt extraction attacks."""
    detector = AnomalyDetectorAdapter(contamination=0.05, n_estimators=50, random_state=42)

    # 40 nominal baseline clients (5 - 20 req/min, token_ratio 1 - 3, entropy 3.2 - 3.8)
    dataset: list[AnomalyFeatureVector] = []
    for i in range(40):
        dataset.append(
            create_vector(
                entity_id=f"key_normal_{i}",
                velocity=10.0 + (i % 8) * 1.5,
                token_ratio=1.5 + (i % 4) * 0.3,
                entropy=3.4 + (i % 3) * 0.1,
                latency_ms=200.0 + (i % 5) * 20.0,
                error_rate=0.01,
            )
        )

    # 2 extreme abusive anomaly keys (flooding + prompt extraction attack)
    abusive_key_1 = create_vector(
        entity_id="key_abusive_flood",
        velocity=550.0,  # 550 req/min
        token_ratio=85.0,  # 85x input vs output
        entropy=0.45,  # repetitive canary probing
        latency_ms=4500.0,
        error_rate=0.40,
        cost_usd=45.0,
    )
    abusive_key_2 = create_vector(
        entity_id="key_abusive_injection",
        velocity=380.0,
        token_ratio=45.0,
        entropy=5.8,
        latency_ms=6200.0,
        error_rate=0.35,
        cost_usd=28.0,
    )
    dataset.extend([abusive_key_1, abusive_key_2])

    detector.fit(dataset)
    results = detector.batch_detect(dataset)

    results_map = {r.entity_id: r for r in results}
    normal_score = results_map["key_normal_0"]
    abuse_score_1 = results_map["key_abusive_flood"]
    abuse_score_2 = results_map["key_abusive_injection"]

    # Abusive keys should have significantly higher anomaly scores than normal keys
    assert abuse_score_1.anomaly_score > normal_score.anomaly_score
    assert abuse_score_2.anomaly_score > normal_score.anomaly_score
    assert abuse_score_1.is_anomaly is True
    assert abuse_score_1.risk_level in ["HIGH", "CRITICAL"]

    # Explanatory factors must be populated
    assert len(abuse_score_1.contributing_factors) > 0
    factors_str = " ".join(abuse_score_1.contributing_factors)
    assert "Abnormal request velocity" in factors_str or "token ratio" in factors_str


def test_numpy_multivariate_fallback():
    """Verify authentic pure-NumPy statistical fallback runs when scikit-learn is unavailable."""
    detector = AnomalyDetectorAdapter()
    # Force fallback mode
    detector._sklearn_available = False

    dataset: list[AnomalyFeatureVector] = []
    for i in range(30):
        dataset.append(
            create_vector(
                entity_id=f"key_norm_{i}",
                velocity=12.0 + (i % 5),
                token_ratio=2.0,
                entropy=3.5,
                latency_ms=220.0,
            )
        )

    outlier = create_vector(
        entity_id="key_numpy_outlier",
        velocity=500.0,
        token_ratio=50.0,
        entropy=0.5,
        latency_ms=5000.0,
        error_rate=0.5,
    )
    dataset.append(outlier)

    results = detector.batch_detect(dataset)
    assert len(results) == 31

    results_map = {r.entity_id: r for r in results}
    outlier_score = results_map["key_numpy_outlier"]

    assert outlier_score.algorithm_used == "numpy_multivariate_baseline"
    assert outlier_score.anomaly_score > 0.60
    assert outlier_score.is_anomaly is True
    assert len(outlier_score.contributing_factors) > 0
