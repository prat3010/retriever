"""Domain service for continuous online production hallucination tracing."""

import logging
import re
from typing import Any

from src.domain.abstractions.config import TenantConfiguration

logger = logging.getLogger(__name__)


def extract_claims(text: str) -> list[str]:
    """Extract distinct sentence-level claims from generated answer text."""
    if not text or not text.strip():
        return []
    # Split text into sentences / key propositions
    raw_sentences = re.split(r"[.!?\n]+", text)
    claims = [s.strip() for s in raw_sentences if len(s.strip()) > 5]
    return claims


def calculate_faithfulness(claims: list[str], contexts: list[str]) -> float:
    """Calculate the fraction of generated claims supported by retrieved context chunks."""
    if not claims:
        return 1.0
    if not contexts:
        return 0.0

    combined_context = " ".join(contexts).lower()
    supported_count = 0

    for claim in claims:
        claim_lower = claim.lower()
        # Check token keyword overlap against context
        claim_words = [w for w in re.findall(r"\w+", claim_lower) if len(w) > 3]
        if not claim_words:
            supported_count += 1
            continue

        match_count = sum(1 for w in claim_words if w in combined_context)
        match_ratio = match_count / len(claim_words)
        if match_ratio >= 0.4:
            supported_count += 1

    return round(supported_count / len(claims), 4)


def calculate_context_precision(query: str, contexts: list[str]) -> float:
    """Calculate context precision based on query term overlap with retrieved contexts."""
    if not contexts or not query:
        return 1.0

    query_words = {w.lower() for w in re.findall(r"\w+", query) if len(w) > 3}
    if not query_words:
        return 1.0

    relevant_contexts = 0
    for ctx in contexts:
        ctx_lower = ctx.lower()
        if any(qw in ctx_lower for qw in query_words):
            relevant_contexts += 1

    return round(relevant_contexts / len(contexts), 4)


class OnlineHallucinationEvaluator:
    """Continuous online evaluator for scoring live inference requests in production."""

    def __init__(self, repository: Any = None) -> None:
        self.repository = repository

    async def evaluate_inference(
        self,
        tenant_id: str,
        query: str,
        answer: str,
        contexts: list[str],
        config: TenantConfiguration,
        session_id: str | None = None,
        message_id: str | None = None,
    ) -> dict[str, Any]:
        """Evaluate a live inference query-answer-context triple."""
        eval_settings = config.evaluation_settings

        if not eval_settings.enable_online_tracing:
            return {
                "tenant_id": tenant_id,
                "status": "disabled",
                "faithfulness": 1.0,
                "context_precision": 1.0,
                "hallucination_index": 0.0,
                "is_alert": False,
            }

        claims = extract_claims(answer)
        faithfulness = calculate_faithfulness(claims, contexts)
        context_precision = calculate_context_precision(query, contexts)
        hallucination_index = round(max(0.0, 1.0 - faithfulness), 4)

        is_alert = hallucination_index > eval_settings.hallucination_threshold
        if is_alert:
            logger.warning(
                f"[SLA Breach] Online Hallucination Alert for tenant '{tenant_id}': "
                f"Hallucination Index {hallucination_index:.2f} > Threshold {eval_settings.hallucination_threshold:.2f} "
                f"(Query: '{query[:50]}...')"
            )

        eval_payload = {
            "tenant_id": tenant_id,
            "session_id": session_id,
            "message_id": message_id,
            "query": query,
            "answer": answer,
            "faithfulness": faithfulness,
            "context_precision": context_precision,
            "hallucination_index": hallucination_index,
            "is_alert": is_alert,
        }

        if self.repository:
            try:
                saved = await self.repository.save_evaluation(eval_payload)
                return saved
            except Exception as err:
                logger.error(f"Failed to persist online evaluation log ({err}).")

        return eval_payload
