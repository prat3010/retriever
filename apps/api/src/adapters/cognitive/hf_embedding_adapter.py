import asyncio
import random

import httpx

from src.domain.abstractions.retrieval import EmbeddingProvider

DEFAULT_MODEL = "sentence-transformers/all-mpnet-base-v2"
DEFAULT_DIMENSION = 768
HF_INFERENCE_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction"


class HFEmbeddingAdapter(EmbeddingProvider):
    def __init__(
        self,
        api_key: str = "",
        model: str = DEFAULT_MODEL,
        dimension: int = DEFAULT_DIMENSION,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._dimension = dimension
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
            self._client = httpx.AsyncClient(headers=headers, timeout=60.0)
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        result = await self._embed_with_retry([text])
        return result[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return await self._embed_with_retry(texts)

    async def _embed_with_retry(self, texts: list[str], max_retries: int = 3) -> list[list[float]]:
        url = f"{HF_INFERENCE_URL}/{self._model}"
        for attempt in range(max_retries + 1):
            try:
                response = await self.client.post(url, json={"inputs": texts, "options": {"wait_for_model": True}})
                if response.status_code == 503:
                    raise httpx.HTTPStatusError("Model loading", request=response.request, response=response)
                response.raise_for_status()
                data = response.json()
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                    return data
                if isinstance(data, dict) and "error" in data:
                    raise ValueError(data["error"])
                return [data]
            except (httpx.HTTPStatusError, httpx.TimeoutException, ValueError):
                if attempt == max_retries:
                    raise
                sleep_seconds = (2 ** attempt) + random.uniform(0, 1)
                await asyncio.sleep(sleep_seconds)
        return []
