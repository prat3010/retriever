import asyncio
import json

from src.domain.abstractions.inference import ChatMessage, InferenceRequest, LlmProvider
from src.domain.abstractions.retrieval import QueryIntent, QueryIntentClassifier

CLASSIFY_SYSTEM_PROMPT = (
    "You are a search query classifier. Given a user query, decide how many chunks to retrieve "
    "and which search features to enable. Return ONLY a JSON object with these fields:\n"
    "- top_k: integer (3 for simple factoids, 7 for medium questions, 15 for complex/exploratory)\n"
    "- enable_hybrid: boolean (false for simple factoid lookups, true otherwise)\n"
    "- enable_reranking: boolean (false for simple queries, true otherwise)\n"
    "- enable_web_search: boolean (true if the query likely needs live/recent info)\n\n"
    "Examples:\n"
    'Query: "what is 2+2"\n'
    '{"top_k": 3, "enable_hybrid": false, "enable_reranking": false, "enable_web_search": false}\n\n'
    'Query: "explain quantum computing"\n'
    '{"top_k": 7, "enable_hybrid": true, "enable_reranking": true, "enable_web_search": false}\n\n'
    'Query: "what are the latest AI regulations in the EU"\n'
    '{"top_k": 15, "enable_hybrid": true, "enable_reranking": true, "enable_web_search": true}'
)


class LLMQueryIntentAdapter(QueryIntentClassifier):

    def __init__(self, llm: LlmProvider, model: str = "gemini-1.5-flash") -> None:
        self.llm = llm
        self.model = model

    async def classify(self, query: str) -> QueryIntent:
        request = InferenceRequest(
            messages=[
                ChatMessage(role="system", content=CLASSIFY_SYSTEM_PROMPT),
                ChatMessage(role="user", content=f"Query: {query}"),
            ],
            temperature=0.0,
            max_tokens=150,
        )
        try:
            response = await asyncio.wait_for(
                self.llm.generate(request, {"model": self.model}), timeout=1.5
            )
            raw = response.content.strip()
            raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```")
            parsed = json.loads(raw)
            return QueryIntent(**parsed)
        except Exception:
            return QueryIntent()
