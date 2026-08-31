import json
import logging

from src.config import settings
from src.domain.abstractions.config import ConfigCache, TenantConfiguration

logger = logging.getLogger(__name__)

redis_client = None

try:
    import redis.asyncio as redis
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception as exc:
    logger.debug(f"Redis cache initialization skipped/failed: {exc}")


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
        except Exception as err:
            logger.debug(f"Redis get_cached_config miss/error for tenant {tenant_id}: {err}")
            return None

    async def set_cached_config(self, tenant_id: str, config: TenantConfiguration) -> None:
        try:
            if redis_client is None:
                return
            await redis_client.setex(self._get_key(tenant_id), 3600, json.dumps(config.model_dump()))
        except Exception as err:
            logger.warning(f"Redis set_cached_config failed for tenant {tenant_id}: {err}")

    async def get_cached_global_config(self) -> TenantConfiguration | None:
        try:
            if redis_client is None:
                return None
            cached_data = await redis_client.get(self._get_global_key())
            if not cached_data:
                return None
            return TenantConfiguration(**json.loads(cached_data))
        except Exception as err:
            logger.debug(f"Redis get_cached_global_config miss/error: {err}")
            return None

    async def set_cached_global_config(self, config: TenantConfiguration) -> None:
        try:
            if redis_client is None:
                return
            await redis_client.setex(self._get_global_key(), 3600, json.dumps(config.model_dump()))
        except Exception as err:
            logger.warning(f"Redis set_cached_global_config failed: {err}")

    async def invalidate_config(self, tenant_id: str) -> None:
        try:
            if redis_client is None:
                return
            await redis_client.delete(self._get_key(tenant_id))
        except Exception as err:
            logger.warning(f"Redis invalidate_config failed for tenant {tenant_id}: {err}")

    async def invalidate_global_config(self) -> None:
        try:
            if redis_client is None:
                return
            await redis_client.delete(self._get_global_key())
        except Exception as err:
            logger.warning(f"Redis invalidate_global_config failed: {err}")


class RerankerCandidateCache:
    """Redis cache for top reranked search candidate tuples."""

    @staticmethod
    def _get_key(tenant_id: str, query_hash: str) -> str:
        return f"reranker:cache:{tenant_id}:{query_hash}"

    async def get_cached_candidates(self, tenant_id: str, query_text: str) -> list[dict] | None:
        try:
            if redis_client is None:
                return None
            import hashlib
            q_hash = hashlib.sha256(query_text.encode()).hexdigest()[:16]
            raw = await redis_client.get(self._get_key(tenant_id, q_hash))
            if not raw:
                return None
            return json.loads(raw)
        except Exception as err:
            logger.debug(f"Redis get_cached_candidates miss/error for tenant {tenant_id}: {err}")
            return None

    async def set_cached_candidates(self, tenant_id: str, query_text: str, candidates: list[dict], ttl: int = 1800) -> None:
        try:
            if redis_client is None:
                return
            import hashlib
            q_hash = hashlib.sha256(query_text.encode()).hexdigest()[:16]
            await redis_client.setex(self._get_key(tenant_id, q_hash), ttl, json.dumps(candidates))
        except Exception as err:
            logger.warning(f"Redis set_cached_candidates failed for tenant {tenant_id}: {err}")

