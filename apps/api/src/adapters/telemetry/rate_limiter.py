"""Redis-backed rate limiter.

Implements a sliding-window counter algorithm for per-tenant rate limiting.
"""

import time
from typing import Any

from src.domain.abstractions.telemetry import RateLimiter, RateLimitResult


_SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local max_reqs = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])
local cutoff = now - window

redis.call('ZREMRANGEBYSCORE', key, 0, cutoff)

local count = redis.call('ZCARD', key)

local allowed = 1
if count + cost > max_reqs then
    allowed = 0
else
    redis.call('ZADD', key, now, now .. ':' .. tostring(math.random()))
    redis.call('EXPIRE', key, window + 1)
    count = count + cost
end

local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
local reset_after = 0
if #oldest > 0 then
    local oldest_time = tonumber(oldest[2])
    reset_after = math.max(0, math.ceil(oldest_time + window - now))
else
    reset_after = window
end

return {allowed, max_reqs, max_reqs - count, reset_after}
"""


def _parse_rate_limit_result(res: Any, max_requests: int) -> RateLimitResult:
    if res and len(res) == 4:
        return RateLimitResult(
            allowed=bool(res[0]),
            limit=int(res[1]),
            remaining=int(res[2]),
            reset_after=int(res[3]),
        )
    return RateLimitResult(
        allowed=True,
        limit=max_requests,
        remaining=max_requests,
        reset_after=0,
    )


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

    async def acquire(self, key: str, cost: float = 1.0) -> RateLimitResult:
        """Attempt to consume *cost* tokens for *key*.

        Uses a Lua script for atomic sliding-window check-and-add.
        """
        now = time.time()
        try:
            res = await self._redis.eval(
                _SLIDING_WINDOW_SCRIPT,
                1,
                key,
                now,
                self._window,
                self._max_requests,
                cost,
            )
            return _parse_rate_limit_result(res, self._max_requests)
        except Exception:
            # Fail open on Redis errors — allow the request
            return RateLimitResult(
                allowed=True,
                limit=self._max_requests,
                remaining=self._max_requests,
                reset_after=0,
            )
