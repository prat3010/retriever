"""Tests for RedisTenantConfigCache (M14: Semantic Cache Layer)."""

from unittest.mock import AsyncMock, patch

import pytest

from src.adapters.cache.config_cache import RedisTenantConfigCache
from src.domain.abstractions.config import TenantConfiguration


@pytest.fixture
def cache() -> RedisTenantConfigCache:
    return RedisTenantConfigCache()


@pytest.fixture
def sample_config() -> TenantConfiguration:
    return TenantConfiguration(tenant_id="tnt_001")


def _async_mock_redis():
    """Patcher that wraps MagicMock methods with AsyncMock for await support."""
    from unittest.mock import MagicMock
    m = MagicMock()
    m.get = AsyncMock()
    m.setex = AsyncMock()
    m.delete = AsyncMock()
    return m


@pytest.fixture(autouse=True)
def mock_redis():
    with patch("src.adapters.cache.config_cache.redis_client", new_callable=_async_mock_redis) as m:
        yield m


@pytest.mark.asyncio
async def test_get_cached_config_hit(mock_redis, cache, sample_config):
    import json
    mock_redis.get.return_value = json.dumps(sample_config.model_dump())
    result = await cache.get_cached_config("tnt_001")
    assert result is not None
    assert result.tenant_id == "tnt_001"
    mock_redis.get.assert_called_once_with("config:tenant:tnt_001")


@pytest.mark.asyncio
async def test_get_cached_config_miss(mock_redis, cache):
    mock_redis.get.return_value = None
    result = await cache.get_cached_config("tnt_001")
    assert result is None


@pytest.mark.asyncio
async def test_get_cached_config_redis_down(mock_redis, cache):
    mock_redis.get.side_effect = Exception("Redis connection refused")
    result = await cache.get_cached_config("tnt_001")
    assert result is None


@pytest.mark.asyncio
async def test_set_cached_config(mock_redis, cache, sample_config):
    await cache.set_cached_config("tnt_001", sample_config)
    mock_redis.setex.assert_called_once()
    args = mock_redis.setex.call_args[0]
    assert args[0] == "config:tenant:tnt_001"
    assert args[1] == 3600


@pytest.mark.asyncio
async def test_set_cached_config_redis_down(mock_redis, cache, sample_config):
    mock_redis.setex.side_effect = Exception("Redis connection refused")
    await cache.set_cached_config("tnt_001", sample_config)


@pytest.mark.asyncio
async def test_get_global_config_hit(mock_redis, cache, sample_config):
    import json
    mock_redis.get.return_value = json.dumps(sample_config.model_dump())
    result = await cache.get_cached_global_config()
    assert result is not None
    mock_redis.get.assert_called_once_with("config:global")


@pytest.mark.asyncio
async def test_get_global_config_miss(mock_redis, cache):
    mock_redis.get.return_value = None
    result = await cache.get_cached_global_config()
    assert result is None


@pytest.mark.asyncio
async def test_set_global_config(mock_redis, cache, sample_config):
    await cache.set_cached_global_config(sample_config)
    mock_redis.setex.assert_called_once()
    assert mock_redis.setex.call_args[0][0] == "config:global"


@pytest.mark.asyncio
async def test_invalidate_config(mock_redis, cache):
    await cache.invalidate_config("tnt_001")
    mock_redis.delete.assert_called_once_with("config:tenant:tnt_001")


@pytest.mark.asyncio
async def test_invalidate_config_redis_down(mock_redis, cache):
    mock_redis.delete.side_effect = Exception("Redis connection refused")
    await cache.invalidate_config("tnt_001")


@pytest.mark.asyncio
async def test_invalidate_global_config(mock_redis, cache):
    await cache.invalidate_global_config()
    mock_redis.delete.assert_called_once_with("config:global")
