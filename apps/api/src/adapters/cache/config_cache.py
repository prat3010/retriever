import json
from typing import Optional
import redis.asyncio as redis
from src.config import settings
from src.domain.abstractions.config import TenantConfiguration, ConfigCache

# Initialize async Redis client pool
redis_client: redis.Redis = redis.from_url(settings.REDIS_URL, decode_responses=True)


class RedisTenantConfigCache(ConfigCache):
    @staticmethod
    def _get_key(tenant_id: str) -> str:
        return f"config:tenant:{tenant_id}"

    @staticmethod
    def _get_global_key() -> str:
        return "config:global"

    async def get_cached_config(self, tenant_id: str) -> Optional[TenantConfiguration]:
        """Fetch cached tenant configurations, returning None if cache misses."""
        try:
            key = self._get_key(tenant_id)
            cached_data = await redis_client.get(key)
            if not cached_data:
                return None
            data = json.loads(cached_data)
            return TenantConfiguration(**data)
        except Exception:
            return None

    async def set_cached_config(self, tenant_id: str, config: TenantConfiguration) -> None:
        """Cache configuration parameters with a 1-hour TTL boundary."""
        try:
            key = self._get_key(tenant_id)
            serialized = json.dumps(config.model_dump())
            await redis_client.setex(key, 3600, serialized)
        except Exception:
            pass

    async def get_cached_global_config(self) -> Optional[TenantConfiguration]:
        """Fetch cached global configurations, returning None if cache misses."""
        try:
            key = self._get_global_key()
            cached_data = await redis_client.get(key)
            if not cached_data:
                return None
            data = json.loads(cached_data)
            return TenantConfiguration(**data)
        except Exception:
            return None

    async def set_cached_global_config(self, config: TenantConfiguration) -> None:
        """Cache global configurations with a 1-hour TTL."""
        try:
            key = self._get_global_key()
            serialized = json.dumps(config.model_dump())
            await redis_client.setex(key, 3600, serialized)
        except Exception:
            pass

    async def invalidate_config(self, tenant_id: str) -> None:
        """Invalidate the cached tenant configuration parameters immediately."""
        try:
            key = self._get_key(tenant_id)
            await redis_client.delete(key)
        except Exception:
            pass

    async def invalidate_global_config(self) -> None:
        """Invalidate the cached global configuration parameters immediately."""
        try:
            key = self._get_global_key()
            await redis_client.delete(key)
        except Exception:
            pass

