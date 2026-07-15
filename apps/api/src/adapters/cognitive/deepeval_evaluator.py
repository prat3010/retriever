from deepeval.metrics import BiasMetric, HallucinationMetric, ToxicityMetric
from deepeval.test_case import LLMTestCase

from src.domain.abstractions.evaluation import DeepEvalScores


async def compute_deepeval_scores(
    question: str,
    answer: str,
    contexts: list[str],
) -> DeepEvalScores:
    if not answer:
        return DeepEvalScores()

    test_case = LLMTestCase(
        input=question,
        actual_output=answer,
        context=contexts,
    )

    scores = DeepEvalScores()

    try:
        hallucination = HallucinationMetric()
        await hallucination.a_measure(test_case)
        scores.hallucination = hallucination.score
    except Exception:
        pass

    try:
        toxicity = ToxicityMetric()
        await toxicity.a_measure(test_case)
        scores.toxicity = toxicity.score
    except Exception:
        pass

    try:
        bias = BiasMetric()
        await bias.a_measure(test_case)
        scores.bias = bias.score
    except Exception:
        pass

    return scores
