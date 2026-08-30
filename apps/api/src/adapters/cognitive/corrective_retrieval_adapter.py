import json

from src.domain.abstractions.inference import ChatMessage, InferenceRequest, LlmProvider
from src.domain.abstractions.retrieval import (
    CorrectiveRetrievalDecision,
    CorrectiveRetrievalProvider,
    SearchResult,
)

JUDGE_PROMPT = """You evaluate RAG quality. Given:
QUERY: {query}
ANSWER: {response}
CONTEXT: {context}

Does the answer directly address the query and is it well-supported by the context?
Output JSON: {{"needs_re_retrieval": bool, "confidence_score": 0.0-1.0, "reason": "...", "reformulated_query": str or null}}
Set needs_re_retrieval=true if uncertain, off-topic, or unsupported by context. Set reformulated_query to an improved search query if re-retrieval is needed."""

CRAG_CANDIDATE_JUDGE_PROMPT = """You are a Corrective RAG (CRAG) retrieval confidence evaluator. Given:
USER QUERY: {query}
RETRIEVED CONTEXT CHUNKS:
{context}

Evaluate whether the retrieved context chunks contain sufficient, relevant information to accurately answer the user query.
Determine the confidence status:
- "CORRECT": The context contains direct, sufficient, and highly relevant information to answer the query accurately.
- "AMBIGUOUS": The context is partially relevant or incomplete; additional information or web search would improve the answer.
- "INCORRECT": The context is irrelevant, off-topic, or fails to address the core subject of the query.

Output JSON: {{"status": "CORRECT"|"AMBIGUOUS"|"INCORRECT", "confidence_score": 0.0-1.0, "reason": "...", "reformulated_query": str or null}}"""


class LLMCorrectiveRetrievalAdapter(CorrectiveRetrievalProvider):

    def __init__(self, llm: LlmProvider, judge_model: str = "meta-llama/llama-3.3-70b-instruct") -> None:
        self.llm = llm
        self.judge_model = judge_model

    async def evaluate_response(
        self,
        query: str,
        response: str,
        context_chunks: list[SearchResult],
    ) -> CorrectiveRetrievalDecision:
        context_snippet = "\n".join(
            f"[{i}] {c.content[:500]}" for i, c in enumerate(context_chunks[:5])
        )
        prompt = JUDGE_PROMPT.format(
            query=query,
            response=response[:2000],
            context=context_snippet or "(no context)",
        )
        try:
            llm_response = await self.llm.generate(
                InferenceRequest(
                    messages=[ChatMessage(role="user", content=prompt)],
                    temperature=0.0,
                    json_schema={
                        "type": "object",
                        "properties": {
                            "needs_re_retrieval": {"type": "boolean"},
                            "confidence_score": {"type": "number"},
                            "reason": {"type": "string"},
                            "reformulated_query": {"type": "string"},
                        },
                        "required": ["needs_re_retrieval", "confidence_score", "reason"],
                    },
                ),
                {"model": self.judge_model},
            )
            data = json.loads(llm_response.content)
            return CorrectiveRetrievalDecision(
                status="CORRECT" if not data.get("needs_re_retrieval") else "AMBIGUOUS",
                needs_re_retrieval=bool(data.get("needs_re_retrieval", False)),
                needs_web_search=bool(data.get("needs_re_retrieval", False)),
                confidence_score=float(data.get("confidence_score", 0.0)),
                reason=data.get("reason", ""),
                reformulated_query=data.get("reformulated_query") or None,
            )
        except Exception:
            return CorrectiveRetrievalDecision(
                status="CORRECT",
                needs_re_retrieval=False,
                needs_web_search=False,
                confidence_score=1.0,
                reason="evaluation failed, proceeding with original response",
            )

    async def evaluate_candidates(
        self,
        query: str,
        candidates: list[SearchResult],
        upper_threshold: float = 0.75,
        lower_threshold: float = 0.40,
    ) -> CorrectiveRetrievalDecision:
        """Evaluate candidate retrieval confidence and determine CRAG action state."""
        if not candidates:
            return CorrectiveRetrievalDecision(
                status="INCORRECT",
                needs_re_retrieval=True,
                needs_web_search=True,
                confidence_score=0.0,
                reason="No candidate documents retrieved.",
                reformulated_query=query,
            )

        context_snippet = "\n".join(
            f"[{i}] {c.content[:400]}" for i, c in enumerate(candidates[:5])
        )
        prompt = CRAG_CANDIDATE_JUDGE_PROMPT.format(
            query=query,
            context=context_snippet or "(no context)",
        )

        try:
            llm_response = await self.llm.generate(
                InferenceRequest(
                    messages=[ChatMessage(role="user", content=prompt)],
                    temperature=0.0,
                    json_schema={
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "enum": ["CORRECT", "AMBIGUOUS", "INCORRECT"]},
                            "confidence_score": {"type": "number"},
                            "reason": {"type": "string"},
                            "reformulated_query": {"type": "string"},
                        },
                        "required": ["status", "confidence_score", "reason"],
                    },
                ),
                {"model": self.judge_model},
            )
            data = json.loads(llm_response.content)
            status_val = data.get("status", "CORRECT").upper()
            if status_val not in ("CORRECT", "AMBIGUOUS", "INCORRECT"):
                status_val = "CORRECT"

            conf = float(data.get("confidence_score", 0.8))
            needs_web = status_val in ("AMBIGUOUS", "INCORRECT")
            needs_re = status_val in ("AMBIGUOUS", "INCORRECT")

            return CorrectiveRetrievalDecision(
                status=status_val,
                needs_re_retrieval=needs_re,
                needs_web_search=needs_web,
                confidence_score=conf,
                reason=data.get("reason", f"CRAG evaluated as {status_val}"),
                reformulated_query=data.get("reformulated_query") or None,
            )
        except Exception:
            # Heuristic fallback based on candidate scores
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
            else:
                return CorrectiveRetrievalDecision(
                    status="INCORRECT",
                    needs_re_retrieval=True,
                    needs_web_search=True,
                    confidence_score=avg_score,
                    reason="Heuristic evaluation: low retrieval candidate scores.",
                    reformulated_query=query,
                )
