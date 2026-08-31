"""Online Evaluator & Self-Correcting RAG Feedback Loop.

Monitors real-time search quality metrics (context precision, claim grounding, answer relevance),
computes dynamic feedback scores, and calculates recommended auto-tuned search settings.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class QualityMetrics:
    context_precision: float
    answer_relevance: float
    faithfulness: float
    user_feedback_score: float | None = None  # 1.0 for thumbs up, 0.0 for thumbs down


@dataclass
class AutoTunedSettings:
    top_k: int
    enable_hybrid: bool
    enable_reranking: bool
    hybrid_alpha: float
    rerank_threshold: float


class OnlineEvaluator:
    """Evaluates online RAG performance and auto-tunes search configurations."""

    def evaluate_response(
        self,
        retrieved_chunks: list[str],
        cited_chunks: list[str],
        response_length: int,
        feedback_score: float | None = None,
    ) -> QualityMetrics:
        """Compute real-time RAG quality metrics."""
        if not retrieved_chunks:
            return QualityMetrics(context_precision=0.0, answer_relevance=0.0, faithfulness=0.0)

        # Context Precision: Ratio of cited retrieved chunks to total retrieved
        cited_set = set(cited_chunks)
        hit_count = sum(1 for c in retrieved_chunks if c in cited_set)
        precision = hit_count / len(retrieved_chunks)

        # Faithfulness: 1.0 if cited claims exist, proportional to citations
        faithfulness = min(1.0, len(cited_chunks) * 0.5) if cited_chunks else 0.5

        # Answer relevance: bounded by response length and non-empty content
        relevance = 0.9 if response_length > 30 else 0.4

        return QualityMetrics(
            context_precision=round(precision, 4),
            answer_relevance=round(relevance, 4),
            faithfulness=round(faithfulness, 4),
            user_feedback_score=feedback_score,
        )

    def auto_tune_retrieval(
        self,
        recent_metrics: list[QualityMetrics],
        current_settings: dict[str, Any],
    ) -> AutoTunedSettings:
        """Calculate auto-tuned retrieval parameters based on aggregate quality trends."""
        if not recent_metrics:
            return AutoTunedSettings(
                top_k=current_settings.get("top_k", 5),
                enable_hybrid=current_settings.get("enable_hybrid", True),
                enable_reranking=current_settings.get("enable_reranking", True),
                hybrid_alpha=current_settings.get("hybrid_alpha", 0.7),
                rerank_threshold=current_settings.get("rerank_threshold", 0.3),
            )

        avg_precision = sum(m.context_precision for m in recent_metrics) / len(recent_metrics)
        avg_faithfulness = sum(m.faithfulness for m in recent_metrics) / len(recent_metrics)

        # Adjust top_k: if precision is low, reduce top_k to eliminate noisy chunks
        curr_top_k = current_settings.get("top_k", 5)
        if avg_precision < 0.3:
            new_top_k = max(3, curr_top_k - 1)
        elif avg_precision > 0.8:
            new_top_k = min(15, curr_top_k + 2)
        else:
            new_top_k = curr_top_k

        # Adjust rerank threshold: if faithfulness is low, raise threshold to filter low-confidence context
        curr_threshold = current_settings.get("rerank_threshold", 0.3)
        new_threshold = round(min(0.7, curr_threshold + 0.1) if avg_faithfulness < 0.5 else curr_threshold, 2)

        return AutoTunedSettings(
            top_k=new_top_k,
            enable_hybrid=True,
            enable_reranking=True,
            hybrid_alpha=0.7,
            rerank_threshold=new_threshold,
        )


class OnlineHallucinationEvaluator:
    """Online hallucination and precision evaluator for container dependency injection."""

    def __init__(self, repository: Any = None, config_service: Any = None) -> None:
        self.repository = repository
        self.config_service = config_service
        self.evaluator = OnlineEvaluator()
        from src.domain.evaluation.self_tuner import SelfTuningEngine
        self.self_tuner = SelfTuningEngine()

    def evaluate_response(
        self,
        retrieved_chunks: list[str],
        cited_chunks: list[str],
        response_length: int,
        feedback_score: float | None = None,
    ) -> QualityMetrics:
        return self.evaluator.evaluate_response(
            retrieved_chunks, cited_chunks, response_length, feedback_score
        )

    async def evaluate_and_record(
        self,
        tenant_id: str,
        session_id: str,
        response_text: str,
        retrieved_chunks: list[Any],
        cited_chunks: list[str] | None = None,
        settings: Any = None,
    ) -> QualityMetrics:
        retrieved_ids = [getattr(c, "chunk_id", str(c)) for c in retrieved_chunks]
        return self.evaluator.evaluate_response(
            retrieved_chunks=retrieved_ids,
            cited_chunks=cited_chunks or [],
            response_length=len(response_text),
        )

    async def evaluate_inference(
        self,
        tenant_id: str,
        query: str,
        answer: str,
        contexts: list[str],
        config: Any = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        eval_settings = getattr(config, "evaluation_settings", None)
        if eval_settings and not getattr(eval_settings, "enable_online_tracing", True):
            return {"status": "disabled", "is_alert": False}

        claims = extract_claims(answer)
        from src.domain.evaluation.nli_evaluator import NliEvaluator
        nli = NliEvaluator()
        nli_res = nli.evaluate_claims(claims, contexts)
        faithfulness = nli_res.faithfulness_score
        precision = calculate_context_precision(contexts, claims)
        hallucination_index = nli_res.hallucination_index
        threshold = getattr(eval_settings, "hallucination_threshold", 0.3) if eval_settings else 0.3
        is_alert = hallucination_index > threshold

        claim_items = [
            {
                "claim": c.claim,
                "premise": c.premise,
                "status": c.status,
                "entailment_prob": c.entailment_prob,
                "contradiction_prob": c.contradiction_prob,
                "neutral_prob": c.neutral_prob,
            }
            for c in nli_res.classifications
        ]

        payload = {
            "status": "evaluated",
            "faithfulness": faithfulness,
            "context_precision": precision,
            "hallucination_index": hallucination_index,
            "is_alert": is_alert,
            "claims_count": len(claims),
            "claims": claim_items,
        }

        # Closed-loop self-tuning trigger if alert fired and config service is available
        if is_alert and self.config_service is not None:
            try:
                metric = QualityMetrics(
                    context_precision=precision,
                    answer_relevance=0.9 if len(answer) > 30 else 0.5,
                    faithfulness=faithfulness,
                )
                tune_report = await self.self_tuner.tune_and_apply(
                    tenant_id=tenant_id,
                    recent_metrics=[metric],
                    config_service=self.config_service,
                )
                payload["self_tuning"] = {
                    "status": tune_report.status,
                    "adjustments": tune_report.adjustments,
                    "recommended": tune_report.recommended_settings,
                }
            except Exception:
                pass

        if self.repository and hasattr(self.repository, "save_evaluation"):
            try:
                save_data = {
                    **payload,
                    "tenant_id": tenant_id,
                    "session_id": session_id,
                    "query": query,
                    "answer": answer,
                }
                await self.repository.save_evaluation(save_data)
            except Exception:
                pass

        return payload


def extract_claims(text: str) -> list[str]:
    """Extract individual sentence claims from response text using NliEvaluator."""
    from src.domain.evaluation.nli_evaluator import NliEvaluator
    evaluator = NliEvaluator()
    return evaluator.extract_claims(text)


def calculate_context_precision(query_or_retrieved: Any, contexts: list[str]) -> float:
    """Calculate context precision for query string or retrieved chunk list against context documents."""
    if not query_or_retrieved or not contexts:
        return 0.0
    if isinstance(query_or_retrieved, str):
        query_terms = set(query_or_retrieved.lower().split())
        matched = sum(1 for c in contexts if any(term in c.lower() for term in query_terms if len(term) > 2))
        return round(matched / len(contexts), 4)
    elif isinstance(query_or_retrieved, list):
        cited_set = set(contexts)
        hit_count = sum(1 for c in query_or_retrieved if str(c) in cited_set)
        return round(hit_count / len(query_or_retrieved), 4)
    return 0.5


def calculate_faithfulness(claims: list[str], context_chunks: list[str]) -> float:
    """Calculate semantic faithfulness using Natural Language Inference (NLI)."""
    if not claims:
        return 1.0
    if not context_chunks:
        return 0.0

    from src.domain.evaluation.nli_evaluator import NliEvaluator
    nli = NliEvaluator()
    res = nli.evaluate_claims(claims, context_chunks)
    return res.faithfulness_score



