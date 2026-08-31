#!/usr/bin/env python3
"""CLI Script for CI/CD Cognitive Regression Gate.

Usage:
    python3 scripts/run_eval_regression.py --faithfulness 0.95 --precision 0.90 --hallucination 0.04
"""

import argparse
import json
import sys
from pathlib import Path

# Add apps/api to path if not installed as package
apps_api_dir = Path(__file__).resolve().parent.parent / "apps" / "api"
if str(apps_api_dir) not in sys.path:
    sys.path.insert(0, str(apps_api_dir))

from src.domain.abstractions.evaluation import (  # noqa: E402
    AggregateScores,
    DeepEvalScores,
    RagasScores,
    RegressionGateThresholds,
)
from src.domain.evaluation.regression_gate import RegressionGateEngine  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Retriever CI/CD Cognitive Regression Gate")
    parser.add_argument("--faithfulness", type=float, default=0.95, help="Measured Faithfulness score")
    parser.add_argument("--precision", type=float, default=0.90, help="Measured Context Precision score")
    parser.add_argument("--relevancy", type=float, default=0.90, help="Measured Answer Relevancy score")
    parser.add_argument("--hallucination", type=float, default=0.04, help="Measured Hallucination Index")

    parser.add_argument("--min-faithfulness", type=float, default=0.90, help="Minimum acceptable faithfulness")
    parser.add_argument("--min-precision", type=float, default=0.85, help="Minimum acceptable context precision")
    parser.add_argument("--min-relevancy", type=float, default=0.85, help="Minimum acceptable answer relevancy")
    parser.add_argument("--max-hallucination", type=float, default=0.10, help="Maximum allowable hallucination index")

    parser.add_argument("--output-json", type=str, default=None, help="Filepath to write JSON report")
    parser.add_argument("--output-md", type=str, default=None, help="Filepath to write Markdown summary")

    args = parser.parse_args()

    engine = RegressionGateEngine()
    agg_scores = AggregateScores(
        ragas=RagasScores(
            faithfulness=args.faithfulness,
            context_precision=args.precision,
            answer_relevancy=args.relevancy,
        ),
        deepeval=DeepEvalScores(
            hallucination=args.hallucination,
        ),
    )

    thresh = RegressionGateThresholds(
        min_faithfulness=args.min_faithfulness,
        min_context_precision=args.min_precision,
        min_answer_relevancy=args.min_relevancy,
        max_hallucination=args.max_hallucination,
    )

    report = engine.evaluate_gate(agg_scores, thresholds=thresh)

    print("\n" + report.summary_markdown + "\n")

    if args.output_json:
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=2)

    if args.output_md:
        with open(args.output_md, "w", encoding="utf-8") as f:
            f.write(report.summary_markdown)

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
