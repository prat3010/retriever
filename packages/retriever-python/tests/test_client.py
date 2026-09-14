"""Unit tests for Retriever Python Client SDK."""

import pytest
import httpx
from retriever import (
    AsyncRetrieverClient,
    AuthenticationError,
    RetrieverClient,
    SearchResponse,
)


def test_client_init_and_headers():
    client = RetrieverClient(
        api_key="test_api_key_123",
        base_url="http://localhost:8000/",
        tenant_id="tenant-uuid-1",
        user_id="user-uuid-1",
    )
    assert client.base_url == "http://localhost:8000"
    assert client._client.headers["X-API-Key"] == "test_api_key_123"
    assert client._client.headers["Authorization"] == "Bearer test_api_key_123"
    assert client._client.headers["X-User-ID"] == "user-uuid-1"
    client.close()


def test_search_request_formatting(monkeypatch):
    captured_request = {}

    def mock_post(url, json=None, headers=None, **kwargs):
        captured_request["url"] = str(url)
        captured_request["json"] = json
        return httpx.Response(
            status_code=200,
            json={
                "results": [
                    {
                        "chunkId": "c-100",
                        "documentId": "d-200",
                        "content": "ColBERT token-level late interaction",
                        "score": 0.985,
                        "metadata": {"title": "ColBERT Overview"},
                    }
                ],
                "total": 1,
                "latency_ms": 14.5,
                "strategy_used": "hybrid_colbert",
                "cached": False,
            },
        )

    client = RetrieverClient(
        api_key="ret_live_test_key",
        base_url="http://localhost:8000",
        tenant_id="00000000-0000-0000-0000-000000000001",
    )
    monkeypatch.setattr(client._client, "post", mock_post)

    response = client.search("How does ColBERT work?", limit=5, enable_colbert_rerank=True)

    assert isinstance(response, SearchResponse)
    assert response.total == 1
    assert response.results[0].chunk_id == "c-100"
    assert response.results[0].score == 0.985
    assert "ColBERT" in response.results[0].content
    assert captured_request["json"]["query"] == "How does ColBERT work?"
    assert captured_request["json"]["reranker_engine"] == "colbert"
    assert captured_request["json"]["limit"] == 5
    client.close()


def test_auth_error_handling(monkeypatch):
    def mock_post_401(*args, **kwargs):
        return httpx.Response(status_code=401, json={"detail": "Unauthorized"})

    client = RetrieverClient(
        api_key="invalid_key",
        base_url="http://localhost:8000",
        tenant_id="00000000-0000-0000-0000-000000000001",
    )
    monkeypatch.setattr(client._client, "post", mock_post_401)

    with pytest.raises(AuthenticationError):
        client.search("test")
    client.close()


@pytest.mark.asyncio
async def test_async_client_lifecycle():
    async with AsyncRetrieverClient(
        api_key="ret_live_test",
        base_url="http://localhost:8000",
        tenant_id="00000000-0000-0000-0000-000000000001",
    ) as client:
        assert client.base_url == "http://localhost:8000"
    assert client._client.is_closed


def test_connector_manifests_sdk(monkeypatch):
    def mock_get(url, **kwargs):
        return httpx.Response(
            status_code=200,
            json={
                "manifests": [
                    {
                        "connector_type": "database_cdc",
                        "name": "Relational Database CDC",
                        "description": "High-watermark CDC",
                        "icon": "database",
                        "supports_incremental": True,
                        "required_parameters": ["host", "database", "user", "tables"],
                        "optional_parameters": {},
                    }
                ],
                "total": 1,
            },
        )

    client = RetrieverClient(
        api_key="ret_live_test_key",
        base_url="http://localhost:8000",
        tenant_id="00000000-0000-0000-0000-000000000001",
    )
    monkeypatch.setattr(client._client, "get", mock_get)

    manifests = client.list_connector_manifests()
    assert len(manifests) == 1
    assert manifests[0].connector_type == "database_cdc"
    assert manifests[0].supports_incremental is True
    client.close()
