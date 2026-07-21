import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from workers.src.tasks import process_document_async

from src.container import search_service
from src.domain.abstractions.config import TenantConfiguration
from src.domain.abstractions.identity import UserContext
from src.domain.abstractions.retrieval import SearchResult
from src.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db_cache():
    import workers.src.tasks
    workers.src.tasks._engine = None


@pytest.mark.asyncio
@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.main.config_service.get_tenant_config", new_callable=AsyncMock)
@patch("src.main.search_service.embedder.embed_text", new_callable=AsyncMock)
@patch("src.main.search_service.vector_search.search_similar", new_callable=AsyncMock)
async def test_semantic_cache_hit(
    mock_search_similar, mock_embed, mock_get_config, mock_validate
) -> None:
    tenant_id = "test-tenant"
    user_uuid = str(uuid.uuid4())
    
    mock_validate.return_value = UserContext(
        user_id=user_uuid,
        tenant_id=tenant_id,
        roles=["client"],
        scopes=["document:read"],
    )
    
    config = TenantConfiguration(tenant_id=tenant_id)
    mock_get_config.return_value = config
    mock_embed.return_value = [0.1] * 768
    
    # Mock cache provider hit
    mock_cache_provider = AsyncMock()
    mock_cache_provider.get_cached_search.return_value = [
        SearchResult(
            chunk_id="chunk-111",
            document_id="doc-111",
            content="Cached contract details.",
            score=0.99,
            metadata={"filename": "cached.pdf"}
        )
    ]
    
    # Inject mock cache provider directly
    original_cache = search_service.cache_provider
    search_service.cache_provider = mock_cache_provider
    
    try:
        response = client.post(
            f"/v1/tenants/{tenant_id}/search",
            json={"query": "What is the agreement date?", "limit": 10},
            headers={"Authorization": "Bearer ret_live_validtoken.secret", "X-User-ID": user_uuid}
        )
        
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["searchMeta"]["strategy"] == "semantic_cache_hit"
        assert len(body["results"]) == 1
        assert body["results"][0]["chunkId"] == "chunk-111"
        
        # Underlying search provider should NEVER have been called on cache hit
        mock_search_similar.assert_not_called()
    finally:
        search_service.cache_provider = original_cache


@pytest.mark.asyncio
@patch("src.adapters.api.security.identity_provider.validate_token", new_callable=AsyncMock)
@patch("src.main.config_service.get_tenant_config", new_callable=AsyncMock)
@patch("src.main.search_service.embedder.embed_text", new_callable=AsyncMock)
@patch("src.main.search_service.vector_search.search_similar", new_callable=AsyncMock)
async def test_semantic_cache_miss_and_write(
    mock_search_similar, mock_embed, mock_get_config, mock_validate
) -> None:
    tenant_id = "test-tenant"
    user_uuid = str(uuid.uuid4())
    
    mock_validate.return_value = UserContext(
        user_id=user_uuid,
        tenant_id=tenant_id,
        roles=["client"],
        scopes=["document:read"],
    )
    
    config = TenantConfiguration(tenant_id=tenant_id)
    config.feature_flags.enable_hybrid_search = False
    config.feature_flags.enable_reranking = False
    mock_get_config.return_value = config
    mock_embed.return_value = [0.1] * 768
    
    # Mock cache provider miss
    mock_cache_provider = AsyncMock()
    mock_cache_provider.get_cached_search.return_value = None
    
    # Mock search similar return
    mock_search_similar.return_value = [
        SearchResult(chunk_id="chunk-abc", document_id="doc-abc", content="Actual details.", score=0.85)
    ]
    
    # Inject mock cache provider directly
    original_cache = search_service.cache_provider
    search_service.cache_provider = mock_cache_provider
    
    try:
        response = client.post(
            f"/v1/tenants/{tenant_id}/search",
            json={"query": "What is the agreement date?", "limit": 10},
            headers={"Authorization": "Bearer ret_live_validtoken.secret", "X-User-ID": user_uuid}
        )
        
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["searchMeta"]["strategy"] == "vector_only"
        
        # Underlying search provider must be called on cache miss
        mock_search_similar.assert_called_once()
        
        # Check that cache_search was run on cache miss write
        mock_cache_provider.cache_search.assert_called_once()
        call_args = mock_cache_provider.cache_search.call_args[1]
        assert call_args["query_text"] == "What is the agreement date?"
    finally:
        search_service.cache_provider = original_cache


@pytest.mark.asyncio
@patch("workers.src.tasks._publish_event", autospec=True)
@patch("workers.src.tasks.create_async_engine", autospec=True)
async def test_worker_task_bulk_insert_execution(mock_create_engine, mock_publish_event) -> None:
    tenant_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    
    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    mock_create_engine.return_value = mock_engine
    
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_engine.begin.return_value = mock_ctx
    
    # Mock configuration payload fetch returning 3 small chunks
    config_dict = {
        "chunking_settings": {
            "strategy": "fixed_window",
            "chunk_size": 15,
            "chunk_overlap": 2
        }
    }
    
    mock_result = MagicMock()
    mock_result.fetchone.return_value = [json.dumps(config_dict)]
    mock_conn.execute.return_value = mock_result
    
    test_file = "./sample_bulk_test.txt"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("Line 1 chunk info.\nLine 2 chunk info.\nLine 3 chunk info.")
        
    import os
    try:
        await process_document_async(doc_id, tenant_id, test_file)
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)
            
    # Verify that batched inserts parameter list was run (executes INSERT with parameter list)
    bulk_insert_run = False
    for call in mock_conn.execute.call_args_list:
        arg = call[0][0]
        if hasattr(arg, "text") and "INSERT INTO document_chunks" in arg.text:
            params = call[0][1]
            assert isinstance(params, list)  # Proves batch insert was executed!
            assert len(params) >= 2
            bulk_insert_run = True
            break
            
    assert bulk_insert_run
