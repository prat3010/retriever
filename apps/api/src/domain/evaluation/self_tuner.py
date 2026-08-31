"""Closed-Loop Telemetry Self-Tuning Engine for Autonomous RAG Optimization.

Monitors real-time evaluation telemetry (faithfulness, context precision, hallucination index,
user ratings) and dynamically calibrates retrieval parameters (top_k, reranking_threshold,
rrf_k, graph search) within safe operational bounds.
"""

from dataclasses import dataclass, field
from typing import Any

from src.domain.evaluation.online_evaluator import QualityMetrics


@dataclass
class SelfTuningReport:
    """Detailed report of dynamic parameter adjustments computed by the self-tuner."""

    tenant_id: str
    status: str  # "tuned" | "stable" | "insufficient_data"
    current_settings: dict[str, Any]
    recommended_settings: dict[str, Any]
    adjustments: list[str] = field(default_factory=list)
    average_faithfulness: float = 1.0
    average_precision: float = 1.0
    hallucination_index: float = 0.0
    confidence_score: float = 1.0


class SelfTuningEngine:
    """Closed-loop autonomous optimizer for multi-tenant RAG retrieval parameters."""

    # Operational Safety Bounds
    MIN_TOP_K = 3
    MAX_TOP_K = 15
    MIN_RERANK_THRESHOLD = 0.15
    MAX_RERANK_THRESHOLD = 0.70
    MIN_RRF_K = 20
    MAX_RRF_K = 100

    def __init__(self, min_sample_size: int = 1) -> None:
        self.min_sample_size = min_sample_size

    def calculate_tuning(
        self,
        tenant_id: str,
        recent_metrics: list[QualityMetrics],
        current_settings: dict[str, Any],
    ) -> SelfTuningReport:
        """Analyze recent telemetry metrics and compute optimal parameter adjustments."""
        curr_top_k = int(current_settings.get("top_k", 5))
        curr_threshold = float(current_settings.get("reranking_threshold", current_settings.get("rerank_threshold", 0.30)))
        curr_rrf_k = int(current_settings.get("rrf_k", 60))
        curr_enable_rerank = bool(current_settings.get("enable_reranking", True))
        curr_enable_graph = bool(current_settings.get("enable_graph_search", False))


        if not recent_metrics or len(recent_metrics) < self.min_sample_size:
            return SelfTuningReport(
                tenant_id=tenant_id,
                status="insufficient_data",
                current_settings=current_settings,
                recommended_settings=current_settings,
                adjustments=["Insufficient telemetry samples for self-tuning."],
            )

        # Compute rolling averages
        avg_faithfulness = sum(m.faithfulness for m in recent_metrics) / len(recent_metrics)
        avg_precision = sum(m.context_precision for m in recent_metrics) / len(recent_metrics)
        avg_hallucination = round(1.0 - avg_faithfulness, 4)

        new_top_k = curr_top_k
        new_threshold = curr_threshold
        new_rrf_k = curr_rrf_k
        new_enable_graph = curr_enable_graph
        adjustments: list[str] = []

        # 1. Faithfulness & Hallucination Guardrail
        if avg_faithfulness < 0.60 or avg_hallucination > 0.35:
            # Raise reranking threshold to aggressively discard hallucinated/irrelevant contexts
            delta_threshold = 0.08 if avg_faithfulness < 0.45 else 0.04
            new_threshold = min(self.MAX_RERANK_THRESHOLD, round(curr_threshold + delta_threshold, 2))
            if new_threshold != curr_threshold:
                adjustments.append(
                    f"Raised reranking_threshold from {curr_threshold:.2f} to {new_threshold:.2f} "
                    f"due to elevated hallucination index ({avg_hallucination:.2f})."
                )

            # Boost top-ranked fusion candidates by narrowing RRF denominator
            if curr_rrf_k > 40:
                new_rrf_k = max(self.MIN_RRF_K, curr_rrf_k - 15)
                adjustments.append(f"Tightened rrf_k from {curr_rrf_k} to {new_rrf_k} to prioritize top-fused candidates.")

            # Suggest activating graph evidence if available
            if not curr_enable_graph:
                new_enable_graph = True
                adjustments.append("Enabled GraphRAG entity search pass to reinforce factual grounding.")

        elif avg_faithfulness > 0.90 and avg_precision > 0.80:
            # High-confidence regime: gently relax threshold if it was overly restrictive
            if curr_threshold > 0.25:
                new_threshold = max(self.MIN_RERANK_THRESHOLD, round(curr_threshold - 0.03, 2))
                adjustments.append(
                    f"Relaxed reranking_threshold from {curr_threshold:.2f} to {new_threshold:.2f} "
                    f"given high factual stability ({avg_faithfulness:.2f})."
                )

        # 2. Context Precision Guardrail
        if avg_precision < 0.35:
            # Lower top_k to eliminate noisy distractors from prompt context
            new_top_k = max(self.MIN_TOP_K, curr_top_k - 1)
            if new_top_k != curr_top_k:
                adjustments.append(
                    f"Reduced top_k from {curr_top_k} to {new_top_k} to reduce context noise (precision: {avg_precision:.2f})."
                )
        elif avg_precision > 0.85 and avg_faithfulness >= 0.80:
            # Expand top_k to provide richer context for complex multi-hop synthesis
            new_top_k = min(self.MAX_TOP_K, curr_top_k + 1)
            if new_top_k != curr_top_k:
                adjustments.append(
                    f"Expanded top_k from {curr_top_k} to {new_top_k} given high precision ({avg_precision:.2f})."
                )

        # Check for user negative feedback trend
        feedback_scores = [m.user_feedback_score for m in recent_metrics if m.user_feedback_score is not None]
        if feedback_scores and sum(feedback_scores) / len(feedback_scores) < 0.5:
            # Explicit negative user feedback: enable hybrid search & reranker
            if not curr_enable_rerank:
                adjustments.append("Forced enable_reranking=True in response to negative user feedback.")

        recommended = {
            "top_k": new_top_k,
            "reranking_threshold": new_threshold,
            "rerank_threshold": new_threshold,
            "rrf_k": new_rrf_k,
            "enable_hybrid": True,
            "enable_reranking": True,
            "enable_graph_search": new_enable_graph,
        }

        status = "tuned" if adjustments else "stable"
        if not adjustments:
            adjustments.append("Retrieval parameters are optimal for current traffic characteristics.")

        return SelfTuningReport(
            tenant_id=tenant_id,
            status=status,
            current_settings=current_settings,
            recommended_settings=recommended,
            adjustments=adjustments,
            average_faithfulness=round(avg_faithfulness, 4),
            average_precision=round(avg_precision, 4),
            hallucination_index=round(avg_hallucination, 4),
            confidence_score=round(min(1.0, len(recent_metrics) / 10.0), 2),
        )

    async def tune_and_apply(
        self,
        tenant_id: str,
        recent_metrics: list[QualityMetrics],
        config_service: Any,
    ) -> SelfTuningReport:
        """Compute tuning adjustments and hot-reload tenant configuration in ConfigurationService."""
        # 1. Fetch current tenant config
        tenant_cfg = await config_service.get_tenant_config(tenant_id)
        current_settings = {
            "top_k": tenant_cfg.retrieval_settings.top_k,
            "reranking_threshold": tenant_cfg.retrieval_settings.reranking_threshold,
            "rrf_k": getattr(tenant_cfg.retrieval_settings, "rrf_k", 60),
            "enable_hybrid": tenant_cfg.feature_flags.enable_hybrid_search,
            "enable_reranking": tenant_cfg.feature_flags.enable_reranking,
            "enable_graph_search": tenant_cfg.feature_flags.enable_graph_rag,
        }

        # 2. Compute report
        report = self.calculate_tuning(tenant_id, recent_metrics, current_settings)

        # 3. Apply changes if tuned
        if report.status == "tuned":
            tenant_cfg.retrieval_settings.top_k = report.recommended_settings["top_k"]
            tenant_cfg.retrieval_settings.reranking_threshold = report.recommended_settings["reranking_threshold"]
            if hasattr(tenant_cfg.retrieval_settings, "rrf_k"):
                tenant_cfg.retrieval_settings.rrf_k = report.recommended_settings["rrf_k"]
            if hasattr(tenant_cfg.feature_flags, "enable_graph_rag"):
                tenant_cfg.feature_flags.enable_graph_rag = report.recommended_settings["enable_graph_search"]
            if hasattr(tenant_cfg.feature_flags, "enable_reranking"):
                tenant_cfg.feature_flags.enable_reranking = report.recommended_settings["enable_reranking"]

            await config_service.update_tenant_config(tenant_id, tenant_cfg)

        return report

