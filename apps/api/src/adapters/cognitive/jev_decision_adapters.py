"""TypeSafe AI Jev Decision Adapters (Battery #42).

Implements pure domain retrieval protocols (QueryIntentClassifier,
CorrectiveRetrievalProvider) using TypeSafe AI's Jev non-autoregressive
decision engine with sub-100ms latency and resilient cascading fallback.
"""

import logging
from typing import Any

from src.adapters.cognitive.jev_client import JevClient
from src.domain.abstractions.retrieval import (
    CorrectiveRetrievalDecision,
    CorrectiveRetrievalProvider,
    QueryIntent,
    QueryIntentClassifier,
    SearchResult,
)

logger = logging.getLogger("api")


def _extract_decision_value(decision_entry: Any, default: Any) -> Any:
    """Helper to extract value whether returned as scalar or nested dict with 'value'."""
    if isinstance(decision_entry, dict):
        return decision_entry.get("value", default)
    if decision_entry is not None:
        return decision_entry
    return default


def _extract_confidence(decision_entry: Any, default: float = 0.85) -> float:
    """Helper to extract confidence probability from Jev decision payload."""
    if isinstance(decision_entry, dict):
        conf = decision_entry.get("confidence") or decision_entry.get("probability")
        if conf is not None:
            try:
                return float(conf)
            except (ValueError, TypeError):
                pass
    return default


class JevQueryIntentAdapter(QueryIntentClassifier):
    """Sub-100ms Query Intent Classifier backed by TypeSafe AI Jev."""

    def __init__(
        self,
        jev_client: JevClient,
        fallback: QueryIntentClassifier | None = None,
    ) -> None:
        self.jev_client = jev_client
        self.fallback = fallback

    async def classify(self, query: str) -> QueryIntent:
        """Classify user query intent into search parameters in sub-100ms."""
        if self.jev_client.is_available:
            questions = {
                "top_k": {
                    "type": "integer",
                    "enum": [3, 7, 15],
                    "description": "3 for simple factoids, 7 for standard inquiries, 15 for complex/exploratory questions",
                },
                "enable_hybrid": {
                    "type": "boolean",
                    "description": "false for simple factoid lookups, true for comprehensive domain queries",
                },
                "enable_reranking": {
                    "type": "boolean",
                    "description": "false for basic lookups, true when precision cross-attention reranking is needed",
                },
                "enable_web_search": {
                    "type": "boolean",
                    "description": "true if query likely requires real-time external info or recent events",
                },
            }

            try:
                decisions = await self.jev_client.decide(
                    state=f"User Search Query: {query}",
                    questions=questions,
                )

                raw_top_k = _extract_decision_value(decisions.get("top_k"), 7)
                try:
                    top_k_val = int(raw_top_k)
                except (ValueError, TypeError):
                    top_k_val = 7

                enable_hybrid_val = bool(
                    _extract_decision_value(decisions.get("enable_hybrid"), True)
                )
                enable_reranking_val = bool(
                    _extract_decision_value(decisions.get("enable_reranking"), True)
                )
                enable_web_search_val = bool(
                    _extract_decision_value(decisions.get("enable_web_search"), False)
                )

                logger.debug(
                    "JevQueryIntentAdapter classified query in %.1fms (top_k=%d, hybrid=%s, web=%s)",
                    self.jev_client.ewma_latency_ms,
                    top_k_val,
                    enable_hybrid_val,
                    enable_web_search_val,
                )

                return QueryIntent(
                    top_k=top_k_val,
                    enable_hybrid=enable_hybrid_val,
                    enable_reranking=enable_reranking_val,
                    enable_web_search=enable_web_search_val,
                )
            except Exception as err:
                logger.warning(
                    "JevQueryIntentAdapter failed (%s); cascading to fallback classifier",
                    err,
                )

        if self.fallback:
            return await self.fallback.classify(query)

        return QueryIntent()


class JevCorrectiveRetrievalAdapter(CorrectiveRetrievalProvider):
    """Sub-150ms Corrective RAG (CRAG) Evaluator backed by TypeSafe AI Jev."""

    def __init__(
        self,
        jev_client: JevClient,
        fallback: CorrectiveRetrievalProvider | None = None,
    ) -> None:
        self.jev_client = jev_client
        self.fallback = fallback

    async def evaluate_candidates(
        self,
        query: str,
        candidates: list[SearchResult],
        upper_threshold: float = 0.75,
        lower_threshold: float = 0.40,
    ) -> CorrectiveRetrievalDecision:
        """Evaluate retrieved candidate relevance in sub-150ms without autoregressive tokens."""
        if not candidates:
            return CorrectiveRetrievalDecision(
                status="INCORRECT",
                needs_re_retrieval=True,
                needs_web_search=True,
                confidence_score=0.0,
                reason="No candidate documents retrieved.",
                reformulated_query=query,
            )

        if self.jev_client.is_available:
            context_snippet = "\n".join(
                f"[{i}] {c.content[:400]}" for i, c in enumerate(candidates[:5])
            )
            state = (
                f"USER QUERY: {query}\n"
                f"RETRIEVED CONTEXT CHUNKS:\n{context_snippet}"
            )
            questions = {
                "status": {
                    "type": "string",
                    "enum": ["CORRECT", "AMBIGUOUS", "INCORRECT"],
                    "description": "CORRECT if context is sufficient; AMBIGUOUS if partial; INCORRECT if off-topic",
                },
                "confidence_score": {
                    "type": "number",
                    "description": "Confidence score between 0.0 and 1.0",
                },
                "needs_web_search": {
                    "type": "boolean",
                    "description": "true if external web search is needed to answer query",
                },
            }

            try:
                decisions = await self.jev_client.decide(
                    state=state,
                    questions=questions,
                )

                raw_status = str(
                    _extract_decision_value(decisions.get("status"), "CORRECT")
                ).upper()
                if raw_status not in ("CORRECT", "AMBIGUOUS", "INCORRECT"):
                    raw_status = "CORRECT"

                raw_conf = _extract_decision_value(decisions.get("confidence_score"), None)
                if raw_conf is not None:
                    try:
                        conf_val = float(raw_conf)
                    except (ValueError, TypeError):
                        conf_val = _extract_confidence(decisions.get("status"), 0.85)
                else:
                    conf_val = _extract_confidence(decisions.get("status"), 0.85)

                needs_web = raw_status in ("AMBIGUOUS", "INCORRECT") or bool(
                    _extract_decision_value(decisions.get("needs_web_search"), False)
                )

                logger.debug(
                    "JevCorrectiveRetrievalAdapter evaluated candidates: status=%s, conf=%.2f",
                    raw_status,
                    conf_val,
                )

                return CorrectiveRetrievalDecision(
                    status=raw_status,
                    needs_re_retrieval=needs_web,
                    needs_web_search=needs_web,
                    confidence_score=conf_val,
                    reason=f"Jev System 1 Decision: evaluated as {raw_status} (conf={conf_val:.2f})",
                    reformulated_query=query if needs_web else None,
                )
            except Exception as err:
                logger.warning(
                    "JevCorrectiveRetrievalAdapter evaluate_candidates failed (%s); cascading to fallback",
                    err,
                )

        if self.fallback:
            return await self.fallback.evaluate_candidates(
                query, candidates, upper_threshold, lower_threshold
            )

        # Local heuristic fallback based on candidate similarity scores
        avg_score = sum(c.score for c in candidates) / len(candidates)
        if avg_score >= upper_threshold:
            return CorrectiveRetrievalDecision(
                status="CORRECT",
                needs_re_retrieval=False,
                needs_web_search=False,
                confidence_score=avg_score,
                reason="Heuristic evaluation: high retrieval candidate scores.",
            )
        elif avg_score >= lower_threshold:
            return CorrectiveRetrievalDecision(
                status="AMBIGUOUS",
                needs_re_retrieval=True,
                needs_web_search=True,
                confidence_score=avg_score,
                reason="Heuristic evaluation: moderate retrieval candidate scores.",
                reformulated_query=query,
            )
        return CorrectiveRetrievalDecision(
            status="INCORRECT",
            needs_re_retrieval=True,
            needs_web_search=True,
            confidence_score=avg_score,
            reason="Heuristic evaluation: low retrieval candidate scores.",
            reformulated_query=query,
        )

    async def evaluate_response(
        self,
        query: str,
        response: str,
        context_chunks: list[SearchResult],
    ) -> CorrectiveRetrievalDecision:
        """Evaluate if synthesized response is well-supported by retrieved context."""
        if self.jev_client.is_available:
            context_snippet = "\n".join(
                f"[{i}] {c.content[:400]}" for i, c in enumerate(context_chunks[:5])
            )
            state = (
                f"USER QUERY: {query}\n"
                f"SYNTHESIZED ANSWER: {response[:1500]}\n"
                f"RETRIEVED CONTEXT:\n{context_snippet or '(no context)'}"
            )
            questions = {
                "is_well_supported": {
                    "type": "boolean",
                    "description": "true if the answer directly addresses query and is supported by context",
                },
                "confidence_score": {
                    "type": "number",
                    "description": "Grounding confidence between 0.0 and 1.0",
                },
            }

            try:
                decisions = await self.jev_client.decide(
                    state=state,
                    questions=questions,
                )

                is_supported = bool(
                    _extract_decision_value(decisions.get("is_well_supported"), True)
                )
                raw_conf = _extract_decision_value(decisions.get("confidence_score"), None)
                if raw_conf is not None:
                    try:
                        conf_val = float(raw_conf)
                    except (ValueError, TypeError):
                        conf_val = 0.9 if is_supported else 0.3
                else:
                    conf_val = 0.9 if is_supported else 0.3

                needs_re = not is_supported
                status = "CORRECT" if is_supported else "AMBIGUOUS"

                return CorrectiveRetrievalDecision(
                    status=status,
                    needs_re_retrieval=needs_re,
                    needs_web_search=needs_re,
                    confidence_score=conf_val,
                    reason=f"Jev System 1 Grounding: supported={is_supported} (conf={conf_val:.2f})",
                    reformulated_query=query if needs_re else None,
                )
            except Exception as err:
                logger.warning(
                    "JevCorrectiveRetrievalAdapter evaluate_response failed (%s); cascading to fallback",
                    err,
                )

        if self.fallback:
            return await self.fallback.evaluate_response(
                query, response, context_chunks
            )

        return CorrectiveRetrievalDecision(
            status="CORRECT",
            needs_re_retrieval=False,
            needs_web_search=False,
            confidence_score=1.0,
            reason="Proceeding with synthesized response (fallback).",
        )
