import httpx

from src.domain.abstractions.web_search import WebSearchProvider, WebSearchResult


class TavilySearchAdapter(WebSearchProvider):

    def __init__(self, api_key: str, base_url: str = "https://api.tavily.com") -> None:
        self.api_key = api_key
        self.base_url = base_url

    async def search(self, query: str, max_results: int = 5) -> list[WebSearchResult]:
        if not self.api_key:
            return []
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self.base_url}/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": max_results,
                    "include_answer": False,
                    "include_raw_content": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        return [
            WebSearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
                score=1.0 - i * 0.01,
            )
            for i, r in enumerate(data.get("results", []))
        ]
