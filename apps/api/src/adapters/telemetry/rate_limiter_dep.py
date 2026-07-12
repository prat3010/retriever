"""FastAPI dependency for rate-limit enforcement.

Usage::

    @app.post("/v1/tenants/{tenantId}/search")
    async def search(
        tenantId: str,
        _: None = Depends(rate_limit(scope="search", max_requests=60)),
    ):
        ...
"""

from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from src.adapters.telemetry.setup import get_rate_limiter


def rate_limit(scope: str = "default", max_requests: Optional[int] = None) -> callable:
    """Return a FastAPI dependency that enforces per-tenant rate limits.

    Args:
        scope: Logical scope name (e.g. 'search', 'chat', 'ingest').
        max_requests: Override the default max requests for this scope.
    """
    async def dependency(request: Request, tenantId: Optional[str] = None) -> None:
        limiter = get_rate_limiter()
        if limiter is None:
            return  # Rate limiting disabled

        key = f"rate_limit:{tenantId or 'anonymous'}:{scope}"
        allowed = await limiter.acquire(key)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "rate_limit_exceeded",
                    "scope": scope,
                    "retry_after_seconds": 60,
                },
            )

    return dependency
