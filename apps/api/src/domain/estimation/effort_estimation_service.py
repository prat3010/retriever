"""Domain service for project effort vectorization and sprint estimation orchestration."""

from src.domain.abstractions.effort_estimation import (
    EffortEstimatorInterface,
    EffortPrediction,
    ProjectScopeInput,
    ScopeFeatureVector,
    TopEffortDriver,
)

# Known subsystem categories and baseline empirical weights
FEATURE_TAXONOMY: dict[str, dict[str, str]] = {
    "auth": {"category": "Auth & Security", "risk": "medium"},
    "rbac": {"category": "Auth & Security", "risk": "medium"},
    "portal": {"category": "Auth & Security", "risk": "low"},
    "database": {"category": "Database & Storage", "risk": "medium"},
    "postgres": {"category": "Database & Storage", "risk": "medium"},
    "vector": {"category": "AI / RAG / Vector", "risk": "high"},
    "rag": {"category": "AI / RAG / Vector", "risk": "high"},
    "agents": {"category": "AI / RAG / Vector", "risk": "high"},
    "vision": {"category": "AI / RAG / Vector", "risk": "medium"},
    "ocr": {"category": "AI / RAG / Vector", "risk": "medium"},
    "voice": {"category": "Real-Time / Voice AI", "risk": "high"},
    "webrtc": {"category": "Real-Time / Voice AI", "risk": "high"},
    "payment": {"category": "Payment & Commerce", "risk": "medium"},
    "razorpay": {"category": "Payment & Commerce", "risk": "medium"},
    "stripe": {"category": "Payment & Commerce", "risk": "medium"},
    "crm": {"category": "Admin & Operations", "risk": "low"},
    "admin": {"category": "Admin & Operations", "risk": "low"},
    "cms": {"category": "Admin & Operations", "risk": "low"},
    "blog": {"category": "Admin & Operations", "risk": "low"},
}


class EffortEstimationService:
    """Orchestrates project scope vectorization and delegates to the ML regression estimator."""

    def __init__(self, estimator: EffortEstimatorInterface):
        self.estimator = estimator

    def extract_feature_vector(self, scope: ProjectScopeInput) -> ScopeFeatureVector:
        """Parse raw scope inputs into normalized numerical features for the ML model."""
        feature_ids = [f.lower() for f in scope.feature_ids]
        total_features = len(feature_ids)

        auth_count = 0
        db_count = 0
        ai_count = 0
        voice_count = 0
        payment_count = 0
        admin_count = 0

        for fid in feature_ids:
            if any(k in fid for k in ["voice", "webrtc", "call"]):
                voice_count += 1
            elif any(k in fid for k in ["vector", "rag", "agent", "vision", "ocr", "ai"]):
                ai_count += 1
            elif any(k in fid for k in ["auth", "rbac", "portal", "login"]):
                auth_count += 1
            elif any(k in fid for k in ["database", "postgres", "storage", "cache"]):
                db_count += 1
            elif any(k in fid for k in ["pay", "razorpay", "stripe", "billing", "invoice", "escrow"]):
                payment_count += 1
            elif any(k in fid for k in ["admin", "crm", "cms", "blog", "dashboard"]):
                admin_count += 1

        # Dependency depth estimation (heuristically based on architectural layer combinations)
        depth = 1
        if auth_count > 0:
            depth += 1
        if db_count > 0 or payment_count > 0 or admin_count > 0:
            depth += 1
        if ai_count > 0 or voice_count > 0:
            depth += 1

        brand_weight = 1.0
        if scope.brand_asset_id:
            bid = scope.brand_asset_id.lower()
            if "complete" in bid or "enterprise" in bid:
                brand_weight = 2.0
            elif "essential" in bid or "motion" in bid:
                brand_weight = 1.5

        maintenance_weight = 0.0
        if scope.maintenance_plan_id:
            mid = scope.maintenance_plan_id.lower()
            if "enterprise" in mid or "24_7" in mid:
                maintenance_weight = 2.0
            elif "growth" in mid or "pro" in mid:
                maintenance_weight = 1.0
            else:
                maintenance_weight = 0.5

        return ScopeFeatureVector(
            engine_id=scope.engine_id,
            total_features=total_features,
            auth_security_count=auth_count,
            database_storage_count=db_count,
            ai_vector_count=ai_count,
            realtime_voice_count=voice_count,
            payment_billing_count=payment_count,
            admin_rbac_count=admin_count,
            dependency_depth=depth,
            brand_complexity_weight=brand_weight,
            maintenance_tier_weight=maintenance_weight,
        )

    def estimate(self, scope: ProjectScopeInput) -> EffortPrediction:
        """Generate statistical effort estimation with enriched risk factors and drivers."""
        vector = self.extract_feature_vector(scope)
        prediction = self.estimator.predict_effort(vector)

        # Enrich with domain risk factors
        risk_factors: list[str] = []
        if vector.realtime_voice_count > 0:
            risk_factors.append("Real-Time WebRTC / Voice AI integration introduces audio stream latency variance (+18-24h)")
        if vector.ai_vector_count >= 2:
            risk_factors.append("Multi-model AI & Vector RAG pipelines require rigorous evaluation testbeds (+14-20h)")
        if vector.dependency_depth >= 4:
            risk_factors.append("Deep architectural DAG coupling requires staged milestone integration gates")
        if vector.payment_billing_count > 0 and vector.auth_security_count == 0:
            risk_factors.append("Payment processing without dedicated user authentication requires custom webhook guards")

        # Extract top effort drivers
        drivers: list[TopEffortDriver] = []
        for fid in scope.feature_ids:
            fid_low = fid.lower()
            if any(k in fid_low for k in ["voice", "webrtc"]):
                drivers.append(TopEffortDriver(feature_name=fid, category="Real-Time / Voice AI", added_hours_estimate=22.0, risk_level="high"))
            elif any(k in fid_low for k in ["rag", "vector", "agent"]):
                drivers.append(TopEffortDriver(feature_name=fid, category="AI / RAG / Vector", added_hours_estimate=16.0, risk_level="high"))
            elif any(k in fid_low for k in ["pay", "billing", "razorpay"]):
                drivers.append(TopEffortDriver(feature_name=fid, category="Payment & Commerce", added_hours_estimate=10.0, risk_level="medium"))
            elif any(k in fid_low for k in ["auth", "rbac"]):
                drivers.append(TopEffortDriver(feature_name=fid, category="Auth & Security", added_hours_estimate=8.0, risk_level="medium"))
            elif any(k in fid_low for k in ["admin", "crm"]):
                drivers.append(TopEffortDriver(feature_name=fid, category="Admin & Operations", added_hours_estimate=7.0, risk_level="low"))

        drivers.sort(key=lambda d: d.added_hours_estimate, reverse=True)

        prediction.risk_factors = risk_factors
        prediction.top_effort_drivers = drivers[:5]
        return prediction
