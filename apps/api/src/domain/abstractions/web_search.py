from abc import ABC, abstractmethod

from pydantic import BaseModel


class WebSearchResult(BaseModel):
    title: str = ""
    url: str = ""
    content: str = ""
    score: float = 1.0


class WebSearchProvider(ABC):

    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> list[WebSearchResult]:
        pass
