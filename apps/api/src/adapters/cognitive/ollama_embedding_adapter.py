import httpx

from src.domain.abstractions.retrieval import EmbeddingProvider

DEFAULT_MODEL = "nomic-embed-text"
DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaEmbeddingAdapter(EmbeddingProvider):
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self._timeout, connect=5.0))
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        try:
            response = await self.client.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self._model, "prompt": text},
            )
            response.raise_for_status()
            return response.json()["embedding"]
        except httpx.ConnectError as e:
            raise RuntimeError(
                f"Ollama server is not reachable at {self._base_url}. "
                "Ensure 'ollama serve' is running and model is pulled: 'ollama pull nomic-embed-text'."
            ) from e
        except httpx.TimeoutException as e:
            raise TimeoutError(
                f"Ollama embedding request timed out after {self._timeout}s at {self._base_url}. "
                "Ensure Ollama is responsive and has sufficient compute resources."
            ) from e

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        batch_size = 20
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await self.client.post(
                f"{self._base_url}/api/embed",
                json={"model": self._model, "input": batch},
                timeout=300.0,
            )
            response.raise_for_status()
            results.extend(response.json()["embeddings"])
        return results
