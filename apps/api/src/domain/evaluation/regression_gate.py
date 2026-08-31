"""Automated CI/CD Regression Gate Engine.

Evaluates pipeline benchmark runs against strict quality thresholds (Faithfulness >= 0.90,
Precision >= 0.85, Hallucination <= 0.10) and produces GitHub Markdown PR reports.
"""

from datetime import UTC, datetime

from src.domain.abstractions.evaluation import (
    AggregateScores,
    BaseRegressionGate,
    RegressionGateReport,
    RegressionGateThresholds,
)


class RegressionGateEngine(BaseRegressionGate):
    """Evaluates RAG benchmarks and decides CI/CD gate passage or blockage."""

    def format_markdown_summary(
        self,
        passed: bool,
        scores: dict[str, float],
        thresholds: RegressionGateThresholds,
        violations: list[str],
        timestamp: str,
    ) -> str:
        """Format evaluation results into a GitHub Flavored Markdown summary table."""
        verdict_badge = "✅ **PASSED (RELEASE APPROVED)**" if passed else "❌ **BLOCKED (REGRESSION DETECTED)**"

        def status_icon(condition: bool) -> str:
            return "✅ PASS" if condition else "❌ VIOLATION"

        f_status = status_icon(scores["faithfulness"] >= thresholds.min_faithfulness)
        p_status = status_icon(scores["context_precision"] >= thresholds.min_context_precision)
        r_status = status_icon(scores["answer_relevancy"] >= thresholds.min_answer_relevancy)
        h_status = status_icon(scores["hallucination"] <= thresholds.max_hallucination)

        lines = [
            "## 🛡️ Retriever Cognitive Regression Gate Report",
            "",
            f"**Verdict:** {verdict_badge}",
            "",
            "| Metric | Actual Score | Required Threshold | Gate Status |",
            "| :--- | :--- | :--- | :--- |",
            f"| **Faithfulness** | `{scores['faithfulness']:.3f}` | $\\ge {thresholds.min_faithfulness:.2f}$ | {f_status} |",
            f"| **Context Precision** | `{scores['context_precision']:.3f}` | $\\ge {thresholds.min_context_precision:.2f}$ | {p_status} |",
            f"| **Answer Relevancy** | `{scores['answer_relevancy']:.3f}` | $\\ge {thresholds.min_answer_relevancy:.2f}$ | {r_status} |",
            f"| **Hallucination Index** | `{scores['hallucination']:.3f}` | $\\le {thresholds.max_hallucination:.2f}$ | {h_status} |",
            "",
        ]

        if violations:
            lines.append("### ⚠️ Gate Violations:")
            for v in violations:
                lines.append(f"- {v}")
            lines.append("")

        lines.append(f"> *Evaluated against golden benchmark dataset at `{timestamp}`*")

        return "\n".join(lines)

    def evaluate_gate(
        self,
        aggregate_scores: AggregateScores,
        thresholds: RegressionGateThresholds | None = None,
    ) -> RegressionGateReport:
        """Evaluate aggregate scores against thresholds and produce a CI gate report."""
        thresh = thresholds or RegressionGateThresholds()
        now_str = datetime.now(UTC).isoformat()

        scores = {
            "faithfulness": aggregate_scores.ragas.faithfulness,
            "context_precision": aggregate_scores.ragas.context_precision,
            "answer_relevancy": aggregate_scores.ragas.answer_relevancy,
            "hallucination": aggregate_scores.deepeval.hallucination,
        }

        violations: list[str] = []

        if scores["faithfulness"] < thresh.min_faithfulness:
            violations.append(
                f"Faithfulness score ({scores['faithfulness']:.3f}) is below required minimum of {thresh.min_faithfulness:.2f}."
            )

        if scores["context_precision"] < thresh.min_context_precision:
            violations.append(
                f"Context Precision ({scores['context_precision']:.3f}) is below required minimum of {thresh.min_context_precision:.2f}."
            )

        if scores["answer_relevancy"] < thresh.min_answer_relevancy:
            violations.append(
                f"Answer Relevancy ({scores['answer_relevancy']:.3f}) is below required minimum of {thresh.min_answer_relevancy:.2f}."
            )

        if scores["hallucination"] > thresh.max_hallucination:
            violations.append(
                f"Hallucination Index ({scores['hallucination']:.3f}) exceeds maximum allowable threshold of {thresh.max_hallucination:.2f}."
            )

        passed = len(violations) == 0

        summary_md = self.format_markdown_summary(
            passed=passed,
            scores=scores,
            thresholds=thresh,
            violations=violations,
            timestamp=now_str,
        )

        return RegressionGateReport(
            passed=passed,
            scores=scores,
            thresholds={
                "min_faithfulness": thresh.min_faithfulness,
                "min_context_precision": thresh.min_context_precision,
                "min_answer_relevancy": thresh.min_answer_relevancy,
                "max_hallucination": thresh.max_hallucination,
            },
            violations=violations,
            summary_markdown=summary_md,
            timestamp=now_str,
        )
