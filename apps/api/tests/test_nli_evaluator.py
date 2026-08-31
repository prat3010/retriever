"""Unit tests for Milestone 74: Tier 1 Fast Semantic NLI Cross-Encoder Evaluator."""

from src.domain.evaluation.nli_evaluator import NliEvaluator


def test_nli_claim_extraction():
    """Verify NliEvaluator splits text into atomic claims and strips conversational fluff."""
    evaluator = NliEvaluator()
    text = "Hello! The subscription costs $49/month. Users can cancel anytime without penalty. Thank you."
    claims = evaluator.extract_claims(text)

    assert len(claims) == 2
    assert "The subscription costs $49/month." in claims
    assert "Users can cancel anytime without penalty." in claims


def test_nli_positive_entailment():
    """Verify NliEvaluator detects positive entailment when claims align with context premise."""
    evaluator = NliEvaluator()
    claim = "FastAPI uses Python for high performance async endpoints."
    premise = "FastAPI is a modern web framework that uses Python to build high performance async endpoints."

    classification = evaluator.classify_claim_premise(claim, premise)

    assert classification.status == "entailment"
    assert classification.entailment_prob >= 0.70
    assert classification.contradiction_prob < 0.10


def test_nli_explicit_contradiction_detection():
    """Verify NliEvaluator catches polarity contradictions (e.g. negation flip)."""
    evaluator = NliEvaluator()

    # Case 1: Claim has negation, premise is positive
    claim_neg = "The platform does not support Razorpay payment webhooks."
    premise_pos = "The platform supports Razorpay payment webhooks for invoice settlements."

    res1 = evaluator.classify_claim_premise(claim_neg, premise_pos)
    assert res1.status == "contradiction"
    assert res1.contradiction_prob >= 0.60
    assert res1.entailment_prob < 0.20

    # Case 2: Claim is positive, premise has negation
    claim_pos = "Clients can delete baseline system contracts."
    premise_neg = "Clients cannot delete baseline system contracts as they are marked permanent."

    res2 = evaluator.classify_claim_premise(claim_pos, premise_neg)
    assert res2.status == "contradiction"
    assert res2.contradiction_prob >= 0.60


def test_nli_neutral_unsupported_claim():
    """Verify NliEvaluator marks claims without premise grounding as neutral."""
    evaluator = NliEvaluator()
    claim = "Astronauts discovered water oceans on Jupiter moons."
    premise = "FastAPI uses Pydantic models for request validation and serialization."

    classification = evaluator.classify_claim_premise(claim, premise)

    assert classification.status == "neutral"
    assert classification.neutral_prob >= 0.60


def test_nli_evaluate_claims_aggregate():
    """Verify aggregate evaluation correctly tallies entailed, contradicted, and neutral claims."""
    evaluator = NliEvaluator()

    claims = [
        "Retriever uses pgvector for semantic vector search.",  # Entailed
        "The system does not support Redis caching.",           # Contradicted
        "Satellites orbit Mars in synchronous resonance.",      # Neutral
    ]

    contexts = [
        "Retriever uses PostgreSQL pgvector for semantic vector search and hybrid fusion.",
        "The system supports Redis caching for L1 configuration and query cache storage.",
    ]

    res = evaluator.evaluate_claims(claims, contexts)

    assert res.total_claims == 3
    assert res.entailed_claims == 1
    assert res.contradicted_claims == 1
    assert res.neutral_claims == 1
    assert res.faithfulness_score == round(1 / 3, 4)
    assert res.hallucination_index >= 0.33
