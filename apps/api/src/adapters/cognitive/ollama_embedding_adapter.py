import httpx

from src.domain.abstractions.retrieval import EmbeddingProvider

DEFAULT_MODEL = "nomic-embed-text"
DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaEmbeddingAdapter(EmbeddingProvider):
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        response = await self.client.post(f"{self._base_url}/api/embeddings", json={"model": self._model, "prompt": text})
        response.raise_for_status()
        return response.json()["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = await self.client.post(f"{self._base_url}/api/embeddings", json={"model": self._model, "prompts": texts})
        response.raise_for_status()
        return response.json()["embeddings"]
