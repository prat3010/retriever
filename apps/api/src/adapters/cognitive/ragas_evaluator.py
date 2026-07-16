from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

from src.domain.abstractions.evaluation import RagasScores


async def compute_ragas_scores(
    question: str,
    answer: str,
    contexts: list[str],
    ground_truth: str,
) -> RagasScores:
    if not answer:
        return RagasScores()

    data = {
        "question": [question],
        "answer": [answer],
        "contexts": [contexts],
        "ground_truth": [ground_truth],
    }
    dataset = Dataset.from_dict(data)

    try:
        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        )

        scores = result.to_pandas().iloc[0].to_dict() if hasattr(result, "to_pandas") else {}
        return RagasScores(
            faithfulness=float(scores.get("faithfulness", 0.0)),
            answer_relevancy=float(scores.get("answer_relevancy", 0.0)),
            context_precision=float(scores.get("context_precision", 0.0)),
            context_recall=float(scores.get("context_recall", 0.0)),
        )
    except Exception:
        return RagasScores()
