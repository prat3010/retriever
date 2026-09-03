"""Scikit-Learn Isolation Forest & Robust Statistical Anomaly Detection Adapter.

Analyzes multi-dimensional telemetry feature vectors to detect abusive usage patterns,
credential scraping, and prompt extraction attacks with calibrated risk scores
and explanatory factor attribution.
"""

import logging
import math
from typing import Any

import numpy as np

from src.domain.abstractions.anomaly import (
    AnomalyFeatureVector,
    AnomalyScore,
    BaseAnomalyDetector,
)

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "request_velocity_rpm",
    "token_ratio",
    "prompt_entropy",
    "p99_latency_ms",
    "latency_variance",
    "error_rate",
    "cost_velocity_usd",
]


class AnomalyDetectorAdapter(BaseAnomalyDetector):
    """Production-grade Isolation Forest Anomaly Detection Engine with pure-NumPy statistical fallback."""

    def __init__(
        self,
        contamination: float = 0.05,
        n_estimators: int = 100,
        random_state: int = 42,
    ) -> None:
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state

        self._sklearn_available = False
        self._scaler: Any = None
        self._model: Any = None

        # Baseline statistics for fallback and explanation attribution
        self._feature_medians: np.ndarray | None = None
        self._feature_mads: np.ndarray | None = None

        try:
            from sklearn.ensemble import IsolationForest
            from sklearn.preprocessing import StandardScaler

            self._sklearn_available = True
            self._scaler = StandardScaler()
            self._model = IsolationForest(
                n_estimators=self.n_estimators,
                contamination=self.contamination,
                random_state=self.random_state,
            )
            logger.info("Scikit-Learn IsolationForest initialized successfully.")
        except ImportError:
            logger.warning(
                "scikit-learn not available in environment; using pure NumPy multivariate baseline."
            )

    @property
    def is_sklearn_available(self) -> bool:
        return self._sklearn_available

    def _extract_feature_matrix(
        self, vectors: list[AnomalyFeatureVector]
    ) -> np.ndarray:
        """Convert list of AnomalyFeatureVector domain objects into an (N, D) float array."""
        matrix = []
        for v in vectors:
            row = [
                float(v.request_velocity_rpm),
                float(v.token_ratio),
                float(v.prompt_entropy),
                float(v.p99_latency_ms),
                float(v.latency_variance),
                float(v.error_rate),
                float(v.cost_velocity_usd),
            ]
            matrix.append(row)
        return np.array(matrix, dtype=np.float64)

    def fit(self, feature_matrix: list[AnomalyFeatureVector]) -> None:
        """Fit unsupervised model and calibrate baseline telemetry statistics."""
        if not feature_matrix:
            return

        feat_matrix = self._extract_feature_matrix(feature_matrix)
        if feat_matrix.shape[0] < 2:
            return

        # Always calculate robust non-parametric medians & MADs for factor attribution
        self._feature_medians = np.median(feat_matrix, axis=0)
        deviations = np.abs(feat_matrix - self._feature_medians)
        self._feature_mads = np.median(deviations, axis=0)
        # Avoid zero MAD
        self._feature_mads = np.where(self._feature_mads == 0.0, 1e-4, self._feature_mads)

        if self._sklearn_available and self._scaler is not None and self._model is not None:
            try:
                from sklearn.ensemble import IsolationForest
                from sklearn.preprocessing import StandardScaler

                self._scaler = StandardScaler()
                scaled_matrix = self._scaler.fit_transform(feat_matrix)
                self._model = IsolationForest(
                    n_estimators=self.n_estimators,
                    contamination=self.contamination,
                    random_state=self.random_state,
                )
                self._model.fit(scaled_matrix)
            except Exception as e:
                logger.warning(f"IsolationForest fit failed: {e}; falling back to NumPy baseline.")
                self._sklearn_available = False


    def _generate_contributing_factors(
        self, raw_row: np.ndarray, normalized_features: dict[str, float]
    ) -> list[str]:
        """Synthesize human-readable explanation factors for flagged metrics."""
        factors: list[str] = []
        velocity = raw_row[0]
        token_ratio = raw_row[1]
        entropy = raw_row[2]
        latency = raw_row[3]
        error_rate = raw_row[5]
        cost_vel = raw_row[6]

        meds = self._feature_medians if self._feature_medians is not None else np.zeros(len(FEATURE_NAMES))

        if velocity > max(50.0, meds[0] * 3.0):
            factors.append(
                f"Abnormal request velocity: {velocity:.1f} req/min (baseline: {meds[0]:.1f})"
            )
        if token_ratio > 20.0:
            factors.append(
                f"Severe token ratio asymmetry ({token_ratio:.1f}x input vs output) indicating prompt extraction"
            )
        if 0.0 < entropy < 1.0:
            factors.append(
                f"Abnormally low prompt entropy ({entropy:.2f}) indicating repetitive scripted canary probing"
            )
        elif entropy > 5.0:
            factors.append(
                f"High prompt entropy ({entropy:.2f}) suggesting randomized payload injection"
            )
        if error_rate >= 0.25:
            factors.append(
                f"Elevated failure rate: {error_rate * 100:.1f}% requests rejected or errored"
            )
        if latency > max(5000.0, meds[3] * 3.0):
            factors.append(
                f"P99 latency anomaly: {latency:.0f}ms (baseline: {meds[3]:.0f}ms)"
            )
        if cost_vel > max(10.0, meds[6] * 4.0):
            factors.append(
                f"Token cost surge: ${cost_vel:.2f}/hr consumption rate"
            )

        if not factors:
            factors.append("Multivariate anomaly: joint feature distribution deviated significantly from baseline")

        return factors

    def score(self, vector: AnomalyFeatureVector) -> AnomalyScore:
        """Score a single feature vector and return calibrated AnomalyScore."""
        return self.batch_detect([vector])[0]

    def batch_detect(
        self, vectors: list[AnomalyFeatureVector]
    ) -> list[AnomalyScore]:
        """Detect anomalies across a collection of feature vectors."""
        if not vectors:
            return []

        feat_matrix = self._extract_feature_matrix(vectors)
        n_samples = feat_matrix.shape[0]

        scores: list[float] = []
        algo_name = "isolation_forest"

        if self._sklearn_available and self._model is not None and self._scaler is not None:
            try:
                # Ensure model is fitted
                if not hasattr(self._model, "estimators_"):
                    # Quick fit on input if not pre-fitted
                    self.fit(vectors)

                scaled_matrix = self._scaler.transform(feat_matrix)
                # decision_function gives negative scores for outliers, positive for inliers
                decision_scores = self._model.decision_function(scaled_matrix)
                # Calibrate to [0.0, 1.0] where 1.0 is highest anomaly
                for ds in decision_scores:
                    # Sigmoidal mapping centered around the model threshold (0.0 in decision_function)
                    prob = 1.0 / (1.0 + math.exp(6.0 * ds))
                    scores.append(float(np.clip(prob, 0.0, 1.0)))
            except Exception as e:
                logger.warning(f"IsolationForest scoring failed: {e}; fallback to NumPy.")
                algo_name = "numpy_multivariate_baseline"
                scores = []
        else:
            algo_name = "numpy_multivariate_baseline"

        # Fallback to authentic robust mathematical distance if sklearn unavailable or failed
        if len(scores) != n_samples:
            algo_name = "numpy_multivariate_baseline"
            meds = self._feature_medians if self._feature_medians is not None else np.median(feat_matrix, axis=0)
            mads = self._feature_mads if self._feature_mads is not None else np.median(np.abs(feat_matrix - meds), axis=0)
            mads = np.where(mads == 0.0, 1e-4, mads)

            for i in range(n_samples):
                row = feat_matrix[i]

                # Modified Z-scores
                z_scores = 0.6745 * np.abs(row - meds) / mads
                # Quadratic mean of modified Z-scores
                d = float(np.sqrt(np.mean(z_scores**2)))
                # Probability mapping: d <= 2 is normal, d >= 3.5 is anomalous
                if d <= 1.5:
                    calibrated = d / 5.0  # 0.0 - 0.3
                else:
                    calibrated = 1.0 - math.exp(-0.45 * (d - 1.0))
                scores.append(float(np.clip(calibrated, 0.0, 1.0)))

        results: list[AnomalyScore] = []
        for i, vec in enumerate(vectors):
            prob = scores[i]
            is_anomaly = prob >= 0.70

            if prob >= 0.85:
                risk = "CRITICAL"
            elif prob >= 0.70:
                risk = "HIGH"
            elif prob >= 0.45:
                risk = "MEDIUM"
            else:
                risk = "LOW"

            raw_row = feat_matrix[i]
            feat_dict = {

                FEATURE_NAMES[j]: float(raw_row[j]) for j in range(len(FEATURE_NAMES))
            }

            contributing = (
                self._generate_contributing_factors(raw_row, feat_dict)
                if is_anomaly
                else []
            )

            results.append(
                AnomalyScore(
                    entity_id=vec.entity_id,
                    entity_type=vec.entity_type,
                    tenant_id=vec.tenant_id,
                    anomaly_score=round(prob, 4),
                    is_anomaly=is_anomaly,
                    risk_level=risk,
                    contributing_factors=contributing,
                    algorithm_used=algo_name,
                    features=feat_dict,
                )
            )

        return results
