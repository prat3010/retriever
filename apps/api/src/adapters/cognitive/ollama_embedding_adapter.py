import math
import os

import httpx

from src.domain.abstractions.retrieval import EmbeddingProvider

DEFAULT_MODEL = "nomic-embed-text"
DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_BATCH_SIZE = int(os.environ.get("OLLAMA_EMBED_BATCH_SIZE", "32"))


def _normalize_vector(vec: list[float]) -> list[float]:
    """L2 unit-length vector normalization."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]


def _format_nomic_prompt(text: str, task_prefix: str) -> str:
    """Inject task prefix for nomic-embed-text models if not present."""
    if text.startswith("search_query:") or text.startswith("search_document:"):
        return text
    return f"{task_prefix} {text}".strip()


class OllamaEmbeddingAdapter(EmbeddingProvider):
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout: float = 300.0,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._batch_size = batch_size
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout, connect=10.0, read=self._timeout)
            )
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        is_nomic = "nomic" in self._model.lower()
        prompt_text = (
            _format_nomic_prompt(text, "search_query:") if is_nomic else text
        )
        try:
            response = await self.client.post(
                f"{self._base_url}/api/embed",
                json={"model": self._model, "input": prompt_text},
            )
            response.raise_for_status()
            data = response.json()
            if data.get("embeddings"):
                return _normalize_vector(data["embeddings"][0])
            if "embedding" in data:
                return _normalize_vector(data["embedding"])
            raise ValueError(f"Unexpected response format from Ollama /api/embed: {data}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                legacy_resp = await self.client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._model, "prompt": prompt_text},
                )
                legacy_resp.raise_for_status()
                return _normalize_vector(legacy_resp.json()["embedding"])
            raise
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
        if not texts:
            return []
        is_nomic = "nomic" in self._model.lower()
        formatted_texts = [
            _format_nomic_prompt(t, "search_document:") if is_nomic else t
            for t in texts
        ]
        results: list[list[float]] = []
        batch_size = max(1, self._batch_size)
        for i in range(0, len(formatted_texts), batch_size):
            batch = formatted_texts[i : i + batch_size]
            response = await self.client.post(
                f"{self._base_url}/api/embed",
                json={"model": self._model, "input": batch},
                timeout=httpx.Timeout(self._timeout, connect=10.0, read=self._timeout),
            )
            response.raise_for_status()
            raw_embeddings = response.json().get("embeddings", [])
            results.extend([_normalize_vector(v) for v in raw_embeddings])
        return results
