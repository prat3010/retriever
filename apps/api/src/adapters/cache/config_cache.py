import json

from src.config import settings
from src.domain.abstractions.config import ConfigCache, TenantConfiguration

redis_client = None

try:
    import redis.asyncio as redis
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
    pass


class RedisTenantConfigCache(ConfigCache):
    @staticmethod
    def _get_key(tenant_id: str) -> str:
        return f"config:tenant:{tenant_id}"

    @staticmethod
    def _get_global_key() -> str:
        return "config:global"

    async def get_cached_config(self, tenant_id: str) -> TenantConfiguration | None:
        try:
            if redis_client is None:
                return None
            cached_data = await redis_client.get(self._get_key(tenant_id))
            if not cached_data:
                return None
            return TenantConfiguration(**json.loads(cached_data))
        except Exception:
            return None

    async def set_cached_config(self, tenant_id: str, config: TenantConfiguration) -> None:
        try:
            if redis_client is None:
                return
            await redis_client.setex(self._get_key(tenant_id), 3600, json.dumps(config.model_dump()))
        except Exception:
            pass

    async def get_cached_global_config(self) -> TenantConfiguration | None:
        try:
            if redis_client is None:
                return None
            cached_data = await redis_client.get(self._get_global_key())
            if not cached_data:
                return None
            return TenantConfiguration(**json.loads(cached_data))
        except Exception:
            return None

    async def set_cached_global_config(self, config: TenantConfiguration) -> None:
        try:
            if redis_client is None:
                return
            await redis_client.setex(self._get_global_key(), 3600, json.dumps(config.model_dump()))
        except Exception:
            pass

    async def invalidate_config(self, tenant_id: str) -> None:
        try:
            if redis_client is None:
                return
            await redis_client.delete(self._get_key(tenant_id))
        except Exception:
            pass

    async def invalidate_global_config(self) -> None:
        try:
            if redis_client is None:
                return
            await redis_client.delete(self._get_global_key())
        except Exception:
            pass
