import json
from typing import Optional
import redis.asyncio as redis
from src.config import settings
from src.domain.abstractions.tenant import TenantConfig

# Initialize async Redis client pool
redis_client: redis.Redis = redis.from_url(settings.REDIS_URL, decode_responses=True)


class RedisTenantConfigCache:
    @staticmethod
    def _get_key(tenant_id: str) -> str:
        return f"tenant:config:{tenant_id}"

    async def get_cached_config(self, tenant_id: str) -> Optional[TenantConfig]:
        """Fetch cached tenant configurations, returning None if cache misses."""
        try:
            key = self._get_key(tenant_id)
            cached_data = await redis_client.get(key)
            if not cached_data:
                return None
            data = json.loads(cached_data)
            return TenantConfig(**data)
        except Exception:
            # Degrade gracefully (fail silently on cache issues to prevent service outage)
            return None

    async def set_cached_config(self, tenant_id: str, config: TenantConfig) -> None:
        """Cache configuration parameters with a 1-hour TTL boundary."""
        try:
            key = self._get_key(tenant_id)
            # Serialize model to JSON format
            serialized = json.dumps(config.model_dump())
            # Set key with 3600 seconds (1 hour) TTL
            await redis_client.setex(key, 3600, serialized)
        except Exception:
            pass

    async def invalidate_config(self, tenant_id: str) -> None:
        """Invalidate the cached configuration parameters immediately."""
        try:
            key = self._get_key(tenant_id)
            await redis_client.delete(key)
        except Exception:
            pass
