import httpx

from src.domain.abstractions.web_search import WebSearchProvider, WebSearchResult


class BraveSearchAdapter(WebSearchProvider):

    def __init__(self, api_key: str, base_url: str = "https://api.search.brave.com/res/v1") -> None:
        self.api_key = api_key
        self.base_url = base_url

    async def search(self, query: str, max_results: int = 5) -> list[WebSearchResult]:
        if not self.api_key:
            return []
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self.base_url}/web/search",
                params={"q": query, "count": max_results},
                headers={"Accept": "application/json", "X-Subscription-Token": self.api_key},
            )
            resp.raise_for_status()
            data = resp.json()
        web_results = data.get("web", {})
        return [
            WebSearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("description", ""),
                score=1.0 - i * 0.01,
            )
            for i, r in enumerate(web_results.get("results", []))
        ]
