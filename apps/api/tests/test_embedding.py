"""Embedding Adapter Tests.

Verifies:
- OpenAIEmbeddingAdapter lazily creates the async client
- embed_text returns correct dimension vector
- embed_batch returns results in order
- Exponential backoff with jitter on API errors
- Retry exhaustion raises the original exception
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_embedding_adapter_lazy_init() -> None:
    """Verify adapter does not fail at init — async client created lazily."""
    from src.adapters.cognitive.embedding_adapter import OpenAIEmbeddingAdapter

    adapter = OpenAIEmbeddingAdapter(api_key="test-key")
    assert adapter.client is not None  # property creates client


@pytest.mark.asyncio
async def test_embed_text_returns_correct_dimension() -> None:
    """Verify embed_text returns a vector of the expected dimension."""
    from src.adapters.cognitive.embedding_adapter import OpenAIEmbeddingAdapter

    mock_response = MagicMock()
    mock_response.data = [MagicMock(index=0, embedding=[0.1] * 768)]

    adapter = OpenAIEmbeddingAdapter(api_key="test-key")
    adapter._client = AsyncMock()
    adapter._client.embeddings.create = AsyncMock(return_value=mock_response)

    embedding = await adapter.embed_text("test query")
    assert len(embedding) == 768
    assert embedding[0] == 0.1


@pytest.mark.asyncio
async def test_embed_batch_returns_ordered_results() -> None:
    """Verify embed_batch returns embeddings in the order of input texts."""
    from src.adapters.cognitive.embedding_adapter import OpenAIEmbeddingAdapter

    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(index=1, embedding=[0.2] * 768),
        MagicMock(index=0, embedding=[0.1] * 768),
    ]

    adapter = OpenAIEmbeddingAdapter(api_key="test-key")
    adapter._client = AsyncMock()
    adapter._client.embeddings.create = AsyncMock(return_value=mock_response)

    embeddings = await adapter.embed_batch(["first", "second"])
    assert len(embeddings) == 2
    assert embeddings[0][0] == 0.1
    assert embeddings[1][0] == 0.2


@pytest.mark.asyncio
async def test_embed_retry_on_api_error() -> None:
    """Verify retry logic on transient API error."""
    import openai

    from src.adapters.cognitive.embedding_adapter import OpenAIEmbeddingAdapter

    mock_http_request = MagicMock()
    mock_http_response = MagicMock(spec=["status_code", "headers", "request"])
    mock_http_response.status_code = 429
    mock_http_response.headers = {}
    mock_http_response.request = mock_http_request
    mock_success_response = MagicMock()
    mock_success_response.data = [MagicMock(index=0, embedding=[0.5] * 768)]

    adapter = OpenAIEmbeddingAdapter(api_key="test-key")
    adapter._client = AsyncMock()
    adapter._client.embeddings.create = AsyncMock(
        side_effect=[
            openai.RateLimitError("Rate limited", response=mock_http_response, body=None),
            openai.APITimeoutError(mock_http_request),
            mock_success_response,
        ]
    )

    embedding = await adapter.embed_text("test")
    assert len(embedding) == 768
    assert embedding[0] == 0.5
    assert adapter._client.embeddings.create.call_count == 3


@pytest.mark.asyncio
async def test_embed_retry_exhaustion() -> None:
    """Verify retry exhaustion raises the original exception."""
    import openai

    from src.adapters.cognitive.embedding_adapter import OpenAIEmbeddingAdapter

    mock_http_request = MagicMock()
    mock_http_response = MagicMock(spec=["status_code", "headers", "request"])
    mock_http_response.status_code = 429
    mock_http_response.headers = {}
    mock_http_response.request = mock_http_request
    adapter = OpenAIEmbeddingAdapter(api_key="test-key")
    adapter._client = AsyncMock()
    adapter._client.embeddings.create = AsyncMock(
        side_effect=openai.RateLimitError("Persistent failure", response=mock_http_response, body=None)
    )

    with pytest.raises(openai.RateLimitError, match="Persistent failure"):
        await adapter.embed_text("test")
    assert adapter._client.embeddings.create.call_count >= 2


@pytest.mark.asyncio
async def test_embed_batch_with_config_model() -> None:
    """Verify adapter uses the configured model name."""
    from src.adapters.cognitive.embedding_adapter import OpenAIEmbeddingAdapter

    mock_response = MagicMock()
    mock_response.data = [MagicMock(index=0, embedding=[0.3] * 768)]

    adapter = OpenAIEmbeddingAdapter(api_key="test-key", model="text-embedding-3-large")
    adapter._client = AsyncMock()
    adapter._client.embeddings.create = AsyncMock(return_value=mock_response)

    await adapter.embed_text("test")
    adapter._client.embeddings.create.assert_called_once_with(
        input=["test"],
        model="text-embedding-3-large",
        timeout=30,
        dimensions=768,
    )
