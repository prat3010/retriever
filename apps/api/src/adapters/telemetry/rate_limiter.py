"""Redis-backed rate limiter.

Implements a sliding-window counter algorithm for per-tenant rate limiting.
"""

import time
from typing import Any

from src.domain.abstractions.telemetry import RateLimiter


class RedisSlidingWindowRateLimiter(RateLimiter):
    """Sliding-window rate limiter using Redis sorted sets.

    Each *key* (e.g. ``rate_limit:{tenant_id}:{scope}``) tracks request
    timestamps in a sorted set.  The window slides by removing entries
    older than *window_seconds*.

    Args:
        redis_client: An async Redis client instance.
        window_seconds: Duration of the sliding window (default 60).
        max_requests: Maximum number of requests allowed per window.
    """

    def __init__(
        self,
        redis_client: Any,
        window_seconds: int = 60,
        max_requests: int = 100,
    ) -> None:
        self._redis = redis_client
        self._window = window_seconds
        self._max_requests = max_requests

    async def acquire(self, key: str, cost: float = 1.0) -> bool:
        """Attempt to consume *cost* tokens for *key*.

        Uses a Lua script for atomic sliding-window check-and-add.
        """
        now = time.time()

        script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local max_reqs = tonumber(ARGV[3])
        local cost = tonumber(ARGV[4])
        local cutoff = now - window

        -- Remove expired entries
        redis.call('ZREMRANGEBYSCORE', key, 0, cutoff)

        -- Count remaining entries
        local count = redis.call('ZCARD', key)

        if count + cost > max_reqs then
            return 0
        end

        -- Add current request and set TTL
        redis.call('ZADD', key, now, now .. ':' .. tostring(math.random()))
        redis.call('EXPIRE', key, window + 1)
        return 1
        """

        try:
            result = await self._redis.eval(
                script,
                1,
                key,
                now,
                self._window,
                self._max_requests,
                cost,
            )
            return bool(result)
        except Exception:
            # Fail open on Redis errors — allow the request
            return True
