"""Scikit-Learn Visitor Persona KMeans Clusterer & Lead Propensity Logistic Regression Classifier."""

import math

import numpy as np
from apps.api.src.domain.abstractions.persona_classifier import (
    LeadFeatureVector,
    LeadPropensityScore,
    LeadScorerInterface,
    PersonaClassifierInterface,
    VisitorPersonaPrediction,
    VisitorTelemetryVector,
)
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression

DOMAIN_CODE_MAP: dict[str, float] = {
    "ai_ml": 1.0,
    "enterprise_saas": 0.85,
    "fintech": 0.80,
    "health_tech": 0.70,
    "agency_consulting": 0.65,
    "e_commerce": 0.55,
    "other": 0.40,
}

SENIORITY_CODE_MAP: dict[str, float] = {
    "founder_cxo": 1.0,
    "engineering_leadership": 0.90,
    "technical_staff": 0.70,
    "talent_acquisition": 0.75,
    "other": 0.40,
}


class ScikitPersonaClusterer(PersonaClassifierInterface):
    """Unsupervised KMeans clusterer mapping visitor telemetry into universal persona archetypes."""

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self._model = KMeans(n_clusters=4, n_init=10, random_state=random_state)
        self._cluster_persona_map: dict[int, str] = {}
        self._is_trained = False
        self._fit_baseline_clusters()

    def _vector_to_features(self, v: VisitorTelemetryVector) -> list[float]:
        return [
            v.commercial_intent_ratio,
            v.credibility_intent_ratio,
            v.product_intent_ratio,
            v.content_intent_ratio,
            math.log1p(v.dwell_time_seconds),
            v.interaction_depth_score,
        ]

    def _fit_baseline_clusters(self) -> None:
        rng = np.random.RandomState(self.random_state)
        x_matrix = []

        # Generate 4 distinct behavioral distributions
        # Archetype 0: Commercial Buyer (high commercial ratio)
        for _ in range(80):
            comm = rng.uniform(0.65, 0.95)
            cred = rng.uniform(0.05, 0.20)
            prod = rng.uniform(0.05, 0.20)
            cont = max(0.0, 1.0 - (comm + cred + prod))
            dwell = rng.uniform(60, 600)
            depth = rng.uniform(0.4, 0.9)
            x_matrix.append([comm, cred, prod, cont, math.log1p(dwell), depth])

        # Archetype 1: Technical Evaluator (high product/sandbox ratio)
        for _ in range(80):
            comm = rng.uniform(0.05, 0.20)
            cred = rng.uniform(0.05, 0.20)
            prod = rng.uniform(0.65, 0.95)
            cont = max(0.0, 1.0 - (comm + cred + prod))
            dwell = rng.uniform(90, 900)
            depth = rng.uniform(0.6, 1.0)
            x_matrix.append([comm, cred, prod, cont, math.log1p(dwell), depth])

        # Archetype 2: Talent Recruiter (high credibility/resume ratio)
        for _ in range(80):
            comm = rng.uniform(0.02, 0.15)
            cred = rng.uniform(0.65, 0.95)
            prod = rng.uniform(0.05, 0.20)
            cont = max(0.0, 1.0 - (comm + cred + prod))
            dwell = rng.uniform(45, 300)
            depth = rng.uniform(0.2, 0.6)
            x_matrix.append([comm, cred, prod, cont, math.log1p(dwell), depth])

        # Archetype 3: Community Peer (high content / casual exploration)
        for _ in range(80):
            comm = rng.uniform(0.02, 0.15)
            cred = rng.uniform(0.05, 0.20)
            prod = rng.uniform(0.10, 0.30)
            cont = rng.uniform(0.55, 0.85)
            dwell = rng.uniform(30, 400)
            depth = rng.uniform(0.1, 0.5)
            x_matrix.append([comm, cred, prod, cont, math.log1p(dwell), depth])

        x_arr = np.array(x_matrix)
        self._model.fit(x_arr)

        # Inspect cluster centers to determine persona alignment
        centers = self._model.cluster_centers_
        assigned: dict[int, str] = {}
        archetypes = ["commercial_buyer", "technical_evaluator", "talent_recruiter", "community_peer"]
        used_indices = set()

        # Match each archetype to its dominant dimension
        dim_targets = [0, 2, 1, 3]  # commercial, product, credibility, content
        for arch, target_dim in zip(archetypes, dim_targets, strict=True):
            best_cluster = -1
            best_val = -1.0
            for c_idx in range(4):
                if c_idx not in used_indices:
                    val = centers[c_idx][target_dim]
                    if val > best_val:
                        best_val = val
                        best_cluster = c_idx
            assigned[best_cluster] = arch
            used_indices.add(best_cluster)

        self._cluster_persona_map = assigned
        self._is_trained = True

    def classify_visitor(self, vector: VisitorTelemetryVector) -> VisitorPersonaPrediction:
        if not self._is_trained:
            self._fit_baseline_clusters()

        feat = np.array([self._vector_to_features(vector)])
        cluster_id = int(self._model.predict(feat)[0])
        persona = self._cluster_persona_map.get(cluster_id, "commercial_buyer")

        # Calculate distances to compute confidence score
        center = self._model.cluster_centers_[cluster_id]
        dist = float(np.linalg.norm(feat[0] - center))
        confidence = max(0.60, min(0.98, round(1.0 / (1.0 + 0.5 * dist), 2)))

        actions = {
            "commercial_buyer": "Present Interactive Scoping Lab and instant SOW proposal generator",
            "technical_evaluator": "Highlight live Retriever RAG sandbox, interactive terminal, and 7-day trial",
            "talent_recruiter": "Elevate 1-Page Systems Architect Resume PDF export and core competencies",
            "community_peer": "Surface open-source GitHub architecture specifications and interactive terminal",
        }

        affinity = {
            "commercial": round(vector.commercial_intent_ratio, 2),
            "credibility": round(vector.credibility_intent_ratio, 2),
            "product": round(vector.product_intent_ratio, 2),
            "content": round(vector.content_intent_ratio, 2),
        }

        return VisitorPersonaPrediction(
            persona_category=persona,  # type: ignore
            confidence_score=confidence,
            intent_affinity=affinity,
            recommended_action=actions.get(persona, "Present platform portfolio"),
            cluster_id=cluster_id,
        )


class ScikitLeadPropensityScorer(LeadScorerInterface):
    """Supervised Logistic Regression model predicting lead reply and conversion propensity."""

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self._model = LogisticRegression(class_weight="balanced", random_state=random_state, max_iter=1000)
        self._is_trained = False
        self._fit_baseline_model()

    def _lead_to_features(self, v: LeadFeatureVector) -> list[float]:
        domain_val = DOMAIN_CODE_MAP.get(v.domain_vertical, 0.5)
        seniority_val = SENIORITY_CODE_MAP.get(v.role_seniority, 0.5)
        log_budget = math.log10(max(1000.0, v.budget_tier_usd))
        remote_val = 1.0 if v.is_remote else 0.0
        return [
            float(v.company_size_tier),
            domain_val,
            seniority_val,
            v.tech_stack_affinity,
            log_budget,
            remote_val,
        ]

    def _fit_baseline_model(self) -> None:
        rng = np.random.RandomState(self.random_state)
        n_samples = 350

        x_matrix = []
        y_labels = []

        for _ in range(n_samples):
            size = rng.choice([1, 2, 3, 4, 5], p=[0.2, 0.3, 0.25, 0.15, 0.1])
            domain = rng.choice(list(DOMAIN_CODE_MAP.values()))
            seniority = rng.choice(list(SENIORITY_CODE_MAP.values()))
            tech = rng.uniform(0.2, 0.95)
            budget = rng.uniform(15000, 180000)
            log_budget = math.log10(budget)
            remote = rng.choice([0.0, 1.0], p=[0.25, 0.75])

            feats = [float(size), domain, seniority, tech, log_budget, remote]

            # True latent conversion propensity formula
            latent_score = (
                (seniority * 2.2)
                + (tech * 2.5)
                + (domain * 1.5)
                + ((log_budget - 4.0) * 0.8)
                + (remote * 0.5)
                - 3.2
            )
            prob = 1.0 / (1.0 + math.exp(-latent_score))
            label = 1 if prob > 0.5 else 0

            x_matrix.append(feats)
            y_labels.append(label)

        x_arr = np.array(x_matrix)
        y_arr = np.array(y_labels)
        self._model.fit(x_arr, y_arr)
        self._is_trained = True

    def score_lead(self, vector: LeadFeatureVector) -> LeadPropensityScore:
        if not self._is_trained:
            self._fit_baseline_model()

        feat = np.array([self._lead_to_features(vector)])
        prob = float(self._model.predict_proba(feat)[0][1])
        prob = round(prob, 2)

        drivers: list[str] = []
        if vector.tech_stack_affinity >= 0.75:
            drivers.append("High engineering stack alignment (Python, FastAPI, Postgres, RAG)")
        if vector.role_seniority in ["founder_cxo", "engineering_leadership"]:
            drivers.append(f"Direct decision maker reach ({vector.role_seniority})")
        if vector.is_remote:
            drivers.append("Remote-first operating model matches engagement profile")
        if vector.budget_tier_usd >= 75000:
            drivers.append(f"Strong enterprise budget allocation (${int(vector.budget_tier_usd):,})")

        if prob >= 0.75:
            tier = "A+ High Value"
            strategy = "Immediate high-signal pitch highlighting Retriever architecture and FDE solutions consultation"
        elif prob >= 0.45:
            tier = "B Qualified"
            strategy = "Standard tailored introduction focused on specific tech stack synergies"
        else:
            tier = "C Low Priority"
            strategy = "Automated nurturing or backlog review"

        return LeadPropensityScore(
            conversion_probability=prob,
            priority_tier=tier,  # type: ignore
            recommended_engagement_strategy=strategy,
            key_scoring_drivers=drivers,
        )
