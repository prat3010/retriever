import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, Request, Response

from src.adapters.database.identity_repository import SqlIdentityProvider
from src.adapters.database.semantic_cache import PgSemanticCacheAdapter
from src.adapters.telemetry.rate_limiter import RedisSlidingWindowRateLimiter
from src.domain.abstractions.exceptions import AuthenticationError
from src.domain.abstractions.identity import UserContext
from src.domain.abstractions.inference import ChatSessionInfo
from src.adapters.telemetry.rate_limiter_dep import rate_limit
from processing_core.chunker import chunk_semantic


@pytest.mark.asyncio
@patch("src.adapters.database.identity_repository.tenant_session", autospec=True)
async def test_validate_token_suspended_tenant(mock_session_ctx) -> None:
    # Setup mock session to simulate db query returning None (tenant suspended/inactive)
    mock_db_session = MagicMock()
    mock_db_session.execute = AsyncMock()
    mock_session_ctx.return_value.__aenter__.return_value = mock_db_session

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    provider = SqlIdentityProvider()
    with pytest.raises(AuthenticationError) as exc_info:
        await provider.validate_token("ret_live_testkey.secret")

    assert "suspended" in str(exc_info.value)


@pytest.mark.asyncio
@patch("src.adapters.database.semantic_cache.engine")
async def test_semantic_cache_get_cached_search_transaction(mock_engine) -> None:
    mock_conn = AsyncMock()
    mock_engine.begin.return_value.__aenter__.return_value = mock_conn

    # Mock execute results
    mock_res = MagicMock()
    mock_res.fetchone.return_value = None
    mock_conn.execute.return_value = mock_res

    adapter = PgSemanticCacheAdapter()
    await adapter.get_cached_search("tenant-123", [0.1, 0.2])

    mock_engine.begin.assert_called_once()
    mock_conn.execute.assert_called()


@pytest.mark.asyncio
async def test_list_session_messages_ownership_checks() -> None:
    from src.main import list_session_messages

    # User A accesses User B's session
    mock_session = ChatSessionInfo(
        session_id="session-123",
        tenant_id="tenant-123",
        user_id="user-B",
        created_at="2026-07-15T00:00:00Z"
    )

    with patch("src.main.inference_orchestrator.get_session", new_callable=AsyncMock) as mock_get_session:
        mock_get_session.return_value = mock_session

        with pytest.raises(HTTPException) as exc_info:
            await list_session_messages(
                tenantId="tenant-123",
                sessionId="session-123",
                user_id="user-A"
            )

        assert exc_info.value.status_code == 403
        assert "do not own this chat session" in exc_info.value.detail


@pytest.mark.asyncio
async def test_rate_limit_dep_resolves_tenant_from_auth() -> None:
    mock_limiter = AsyncMock()
    mock_limiter.acquire.return_value = MagicMock(allowed=True, limit=100, remaining=99, reset_after=10)

    # Mock request and response
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {"Authorization": "Bearer token-123"}
    mock_response = MagicMock(spec=Response)
    mock_response.headers = {}

    with patch("src.adapters.telemetry.rate_limiter_dep.get_rate_limiter") as mock_get_limiter, \
         patch("src.adapters.api.security.get_current_user", new_callable=AsyncMock) as mock_get_user:

        mock_get_limiter.return_value = mock_limiter
        mock_get_user.return_value = UserContext(
            user_id="user-123",
            tenant_id="tenant-resolved",
            roles=["client"],
            scopes=["document:read"]
        )

        dep = rate_limit(scope="search")
        await dep(request=mock_request, response=mock_response, tenantId=None)

        # Limiter should use tenant resolved from Authorization token instead of default anonymous
        mock_limiter.acquire.assert_called_once_with("rate_limit:tenant-resolved:search")


@pytest.mark.asyncio
async def test_rate_limiter_lua_deterministic() -> None:
    mock_redis = AsyncMock()
    limiter = RedisSlidingWindowRateLimiter(redis_client=mock_redis, window_seconds=60, max_requests=100)

    await limiter.acquire("rate_limit:tenant-1:search")

    mock_redis.eval.assert_called_once()
    args = mock_redis.eval.call_args.args
    # Arguments: script, numkeys, key, now, window, max_requests, cost, suffix
    assert len(args) == 8
    assert args[2] == "rate_limit:tenant-1:search"
    # Suffix should be a random string (e.g. uuid hex)
    assert isinstance(args[7], str)
    assert len(args[7]) == 32


@pytest.mark.asyncio
@patch("processing_core.chunker.embed_with_retry", new_callable=AsyncMock)
async def test_chunk_semantic_recursive_fallback(mock_embed) -> None:
    # Sentence under chunk_size is 500. Create a sentence of 2000 words
    giant_text = "word " * 2000

    # Mock embed response (returns a list of list floats)
    mock_embed.return_value = [[0.1] * 768] * 10

    mock_client = MagicMock()
    chunks = await chunk_semantic(
        text=giant_text,
        embed_client=mock_client,
        embed_model="nomic-embed-text",
        chunk_size=500,
        chunk_overlap=100
    )

    # The giant sentence should be recursively split under the 500 token limit
    assert len(chunks) > 1
    for c in chunks:
        assert c["token_count"] <= 500
