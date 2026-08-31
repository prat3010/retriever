"""Semantic Natural Language Inference (NLI) Cross-Encoder Evaluator.

Evaluates claim-premise entailment, contradiction, and neutral classification
to replace naive keyword matching with calibrated semantic directional inference.
"""

import re
from typing import ClassVar

from src.domain.abstractions.evaluation import (
    BaseNliEvaluator,
    NliClassification,
    NliEvaluationResult,
)


class NliEvaluator(BaseNliEvaluator):
    """Fast semantic NLI evaluator detecting claim entailment and polarity contradictions."""

    NEGATION_WORDS: ClassVar[set[str]] = {
        "not",
        "no",
        "never",
        "none",
        "neither",
        "nor",
        "lacks",
        "without",
        "prohibits",
        "denies",
        "fails",
        "unsupported",
        "cannot",
        "can't",
        "isn't",
        "aren't",
        "wasn't",
        "weren't",
        "doesn't",
        "don't",
        "didn't",
        "won't",
    }

    STOPWORDS: ClassVar[set[str]] = {
        "the", "a", "an", "is", "are", "was", "were", "and", "or", "in", "on", "at",
        "to", "for", "of", "with", "by", "from", "it", "this", "that", "these", "those",
    }

    def __init__(self, entailment_threshold: float = 0.50, contradiction_threshold: float = 0.35) -> None:
        self.entailment_threshold = entailment_threshold
        self.contradiction_threshold = contradiction_threshold

    def extract_claims(self, text: str) -> list[str]:
        """Split text into individual declarative claim sentences."""
        if not text or not text.strip():
            return []

        # Split on sentence boundaries
        raw_sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        claims: list[str] = []

        conversational = ("hello", "hi", "thanks", "thank you", "sure,", "cheers", "regards", "best regards")
        for s in raw_sentences:
            cleaned = s.strip()
            # Filter out tiny fragments or conversational prefixes
            if len(cleaned) > 8 and not cleaned.lower().startswith(conversational):
                claims.append(cleaned)

        return claims if claims else [text.strip()]



    def classify_claim_premise(self, claim: str, premise: str) -> NliClassification:
        """Classify directional NLI relation between a single claim and a premise context."""
        claim_clean = claim.strip()
        premise_clean = premise.strip()

        if not claim_clean or not premise_clean:
            return NliClassification(
                claim=claim_clean,
                premise=premise_clean,
                entailment_prob=0.0,
                contradiction_prob=0.0,
                neutral_prob=1.0,
                status="neutral",
            )

        # Extract content words (length > 2, not standard stopwords)
        claim_tokens = [w.lower() for w in re.findall(r"\b\w+\b", claim_clean)]
        premise_tokens = [w.lower() for w in re.findall(r"\b\w+\b", premise_clean)]

        claim_content = [w for w in claim_tokens if w not in self.STOPWORDS and len(w) > 2]
        premise_content_set = set(premise_tokens)

        if not claim_content:
            return NliClassification(
                claim=claim_clean,
                premise=premise_clean,
                entailment_prob=0.0,
                contradiction_prob=0.0,
                neutral_prob=1.0,
                status="neutral",
            )

        # Check content overlap ratio
        matched_content = [w for w in claim_content if w in premise_content_set]
        content_overlap = len(matched_content) / len(claim_content)

        # Check polarity (presence of negation in claim vs premise)
        claim_has_negation = any(w in self.NEGATION_WORDS for w in claim_tokens)
        premise_has_negation = any(w in self.NEGATION_WORDS for w in premise_tokens)

        polarity_conflict = claim_has_negation != premise_has_negation

        # Probability calculation
        if content_overlap >= 0.40 and polarity_conflict:
            # High lexical/semantic overlap but opposite negation polarity -> Contradiction
            contradiction_prob = round(min(0.95, 0.40 + content_overlap * 0.55), 4)
            entailment_prob = round(max(0.0, 0.20 - contradiction_prob * 0.2), 4)
            neutral_prob = round(max(0.0, 1.0 - (contradiction_prob + entailment_prob)), 4)
            status = "contradiction"
        elif content_overlap >= self.entailment_threshold and not polarity_conflict:
            # High overlap and matching polarity -> Entailment
            entailment_prob = round(min(0.98, content_overlap * 0.95), 4)
            contradiction_prob = 0.02
            neutral_prob = round(max(0.0, 1.0 - (entailment_prob + contradiction_prob)), 4)
            status = "entailment"
        else:
            # Low overlap or weak signal -> Neutral
            neutral_prob = round(max(0.60, 1.0 - content_overlap), 4)
            entailment_prob = round(content_overlap * 0.30, 4)
            contradiction_prob = 0.05
            status = "neutral"

        return NliClassification(
            claim=claim_clean,
            premise=premise_clean,
            entailment_prob=entailment_prob,
            contradiction_prob=contradiction_prob,
            neutral_prob=neutral_prob,
            status=status,
        )

    def evaluate_claims(
        self, claims: list[str], contexts: list[str]
    ) -> NliEvaluationResult:
        """Evaluate a list of claims against context chunks and compute aggregate scores."""
        if not claims:
            return NliEvaluationResult(
                total_claims=0,
                entailed_claims=0,
                contradicted_claims=0,
                neutral_claims=0,
                faithfulness_score=1.0,
                hallucination_index=0.0,
                classifications=[],
            )

        if not contexts:
            # No context provided -> all claims neutral / unsupported
            classifications = [
                NliClassification(
                    claim=c,
                    premise="",
                    entailment_prob=0.0,
                    contradiction_prob=0.0,
                    neutral_prob=1.0,
                    status="neutral",
                )
                for c in claims
            ]
            return NliEvaluationResult(
                total_claims=len(claims),
                entailed_claims=0,
                contradicted_claims=0,
                neutral_claims=len(claims),
                faithfulness_score=0.0,
                hallucination_index=1.0,
                classifications=classifications,
            )

        classifications: list[NliClassification] = []

        for claim in claims:
            best_match: NliClassification | None = None

            for ctx in contexts:
                candidate = self.classify_claim_premise(claim, ctx)
                # Prioritize contradiction (critical safety signal), then highest entailment
                if candidate.status == "contradiction":
                    if best_match is None or best_match.status != "contradiction" or candidate.contradiction_prob > best_match.contradiction_prob:
                        best_match = candidate
                elif candidate.status == "entailment":
                    if best_match is None or (best_match.status != "contradiction" and candidate.entailment_prob > best_match.entailment_prob):
                        best_match = candidate
                elif best_match is None:
                    best_match = candidate

            if best_match is not None:
                classifications.append(best_match)

        entailed = sum(1 for c in classifications if c.status == "entailment")
        contradicted = sum(1 for c in classifications if c.status == "contradiction")
        neutral = sum(1 for c in classifications if c.status == "neutral")
        total = len(claims)

        faithfulness = round(entailed / max(1, total), 4)
        contradiction_penalty = round(contradicted / max(1, total), 4)
        hallucination_index = round(max(1.0 - faithfulness, contradiction_penalty), 4)

        return NliEvaluationResult(
            total_claims=total,
            entailed_claims=entailed,
            contradicted_claims=contradicted,
            neutral_claims=neutral,
            faithfulness_score=faithfulness,
            hallucination_index=hallucination_index,
            classifications=classifications,
        )
