"""FastAPI dependency for rate-limit enforcement with standardized headers."""

from fastapi import HTTPException, Request, Response, status

from src.adapters.telemetry.setup import get_rate_limiter


def rate_limit(scope: str = "default", max_requests: int | None = None) -> callable:
    """Return a FastAPI dependency that enforces per-tenant rate limits.

    Args:
        scope: Logical scope name (e.g. 'search', 'chat', 'ingest').
        max_requests: Override the default max requests for this scope.
    """
    async def dependency(request: Request, response: Response = None, tenantId: str | None = None) -> None:
        limiter = get_rate_limiter()
        if limiter is None:
            return  # Rate limiting disabled

        t_id = tenantId
        if not t_id:
            auth_header = request.headers.get("Authorization")
            if auth_header:
                try:
                    from src.adapters.api.security import get_current_user
                    user_context = await get_current_user(token=auth_header)
                    t_id = user_context.tenant_id
                except Exception:
                    pass

        key = f"rate_limit:{t_id or 'anonymous'}:{scope}"
        result = await limiter.acquire(key)

        # Set rate limit headers in the response if available
        if response is not None:
            response.headers["X-RateLimit-Limit"] = str(result.limit)
            response.headers["X-RateLimit-Remaining"] = str(result.remaining)
            response.headers["X-RateLimit-Reset"] = str(result.reset_after)

        if not result.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "rate_limit_exceeded",
                    "scope": scope,
                    "retry_after_seconds": result.reset_after,
                },
                headers={
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": str(result.remaining),
                    "X-RateLimit-Reset": str(result.reset_after),
                }
            )

    return dependency
