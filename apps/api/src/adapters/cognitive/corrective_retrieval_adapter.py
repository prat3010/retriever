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


class LLMCorrectiveRetrievalAdapter(CorrectiveRetrievalProvider):

    def __init__(self, llm: LlmProvider, judge_model: str = "gemini-1.5-flash") -> None:
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
                needs_re_retrieval=bool(data.get("needs_re_retrieval", False)),
                confidence_score=float(data.get("confidence_score", 0.0)),
                reason=data.get("reason", ""),
                reformulated_query=data.get("reformulated_query") or None,
            )
        except Exception:
            return CorrectiveRetrievalDecision(
                needs_re_retrieval=False,
                confidence_score=1.0,
                reason="evaluation failed, proceeding with original response",
            )
