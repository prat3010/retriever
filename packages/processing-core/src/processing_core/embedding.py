import asyncio
import random
import openai


async def embed_with_retry(
    client,
    texts: list[str],
    model: str,
    max_retries: int = 5,
) -> list[list[float]]:
    for attempt in range(max_retries + 1):
        try:
            kwargs = {
                "input": texts,
                "model": model,
                "timeout": 30,
            }
            if model.startswith("text-embedding-3-"):
                kwargs["dimensions"] = 768
            response = await client.embeddings.create(**kwargs)
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [item.embedding for item in sorted_data]
        except (
            openai.APIError,
            openai.APITimeoutError,
            openai.RateLimitError,
        ):
            if attempt == max_retries:
                raise
            sleep_seconds = (2**attempt) + random.uniform(0, 1)
            await asyncio.sleep(sleep_seconds)
