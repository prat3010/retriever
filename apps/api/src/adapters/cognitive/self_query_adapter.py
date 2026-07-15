import asyncio
import json

from src.domain.abstractions.inference import ChatMessage, InferenceRequest, LlmProvider
from src.domain.abstractions.retrieval import MetadataFilter, SelfQueryProvider


SELF_QUERY_SYSTEM_PROMPT = (
    "You are a query analyzer. Extract structured metadata filters from the search query. "
    "Return ONLY a JSON array of filter objects. Use these operators: "
    "eq, neq, in, gt, gte, lt, lte, exists, contains, regex. "
    "If no filters apply, return [].\n\n"
    'Examples:\n'
    'Query: "invoices from 2025"\n'
    '[{"field": "doc_type", "operator": "eq", "value": "invoice"}, '
    '{"field": "date_reference", "operator": "eq", "value": "2025"}]\n\n'
    'Query: "documents about finance"\n'
    '[{"field": "topics", "operator": "contains", "value": "finance"}]\n\n'
    'Query: "recent emails from john"\n'
    '[{"field": "doc_type", "operator": "eq", "value": "email"}, '
    '{"field": "author_reference", "operator": "regex", "value": "john"}]\n\n'
    'Query: "what is the budget?"\n'
    '[]'
)


class LLMSelfQueryAdapter(SelfQueryProvider):

    def __init__(self, llm: LlmProvider, model: str = "gemini-1.5-flash") -> None:
        self.llm = llm
        self.model = model

    async def parse_query(self, query: str) -> list[MetadataFilter]:
        request = InferenceRequest(
            messages=[
                ChatMessage(role="system", content=SELF_QUERY_SYSTEM_PROMPT),
                ChatMessage(role="user", content=f"Query: {query}"),
            ],
            temperature=0.0,
            max_tokens=200,
        )
        try:
            response = await asyncio.wait_for(self.llm.generate(request, {"model": self.model}), timeout=2.0)
            raw = response.content.strip()
            raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```")
            parsed = json.loads(raw)
            if not isinstance(parsed, list):
                return []
            return [MetadataFilter(**f) for f in parsed if isinstance(f, dict)]
        except Exception:
            return []
