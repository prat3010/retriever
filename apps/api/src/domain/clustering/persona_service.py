"""Domain service for visitor persona classification and lead propensity scoring orchestration."""

from src.domain.abstractions.persona_classifier import (
    LeadFeatureVector,
    LeadPropensityScore,
    LeadScorerInterface,
    PersonaClassifierInterface,
    VisitorPersonaPrediction,
    VisitorTelemetryVector,
)


class PersonaIntelligenceService:
    """Orchestrates visitor persona clustering and lead propensity scoring."""

    def __init__(
        self,
        persona_classifier: PersonaClassifierInterface,
        lead_scorer: LeadScorerInterface,
    ):
        self.persona_classifier = persona_classifier
        self.lead_scorer = lead_scorer

    def classify_visitor(self, telemetry: VisitorTelemetryVector) -> VisitorPersonaPrediction:
        """Assign an anonymous session telemetry vector to a persona cluster with intent affinity."""
        return self.persona_classifier.classify_visitor(telemetry)

    def score_lead(self, lead: LeadFeatureVector) -> LeadPropensityScore:
        """Predict conversion probability and priority tier for a prospective lead."""
        return self.lead_scorer.score_lead(lead)
