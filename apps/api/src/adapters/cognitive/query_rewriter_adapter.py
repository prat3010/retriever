import asyncio

from src.domain.abstractions.inference import ChatMessage, InferenceRequest, LlmProvider
from src.domain.abstractions.retrieval import QueryRewriterProvider

HYDE_PROMPT = (
    "Given a search query, write a short factual passage that would be "
    "a perfect answer. Be specific and detailed.\n\n"
    "Query: {query}\nPassage:"
)


class LLMQueryRewriterAdapter(QueryRewriterProvider):

    def __init__(self, llm: LlmProvider, model: str = "gemini-1.5-flash") -> None:
        self.llm = llm
        self.model = model

    async def rewrite(self, query: str) -> list[str]:
        if not query.strip():
            return [query]

        request = InferenceRequest(
            messages=[
                ChatMessage(role="system", content=HYDE_PROMPT.format(query=query)),
                ChatMessage(role="user", content=f"Query: {query}"),
            ],
            temperature=0.3,
            max_tokens=256,
        )
        try:
            response = await asyncio.wait_for(
                self.llm.generate(request, {"model": self.model}), timeout=3.0
            )
            rewritten = response.content.strip()
            return [rewritten] if rewritten else [query]
        except Exception:
            return [query]
