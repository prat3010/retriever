import time
from collections import defaultdict

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class TenantRateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Sliding window in-memory rate limiter per tenant_id / client IP.
    Protects multi-tenant inference, vector search, and ingestion against noisy neighbor starvation.
    """

    def __init__(self, app, default_limit: int = 120, window_seconds: int = 60):
        super().__init__(app)
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        # In-memory sliding log: key -> list of timestamps
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_key(self, request: Request) -> str:
        # Check tenant_id from header or state
        tenant_id = request.headers.get("x-tenant-id") or request.headers.get("X-Tenant-Id")
        if tenant_id:
            return f"tenant:{tenant_id}"

        # Fallback to client host IP
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    def _is_rate_limited(self, key: str, limit: int) -> tuple[bool, int, int]:
        now = time.time()
        window_start = now - self.window_seconds
        timestamps = self._requests[key]

        # Prune timestamps outside window
        valid_timestamps = [t for t in timestamps if t > window_start]
        self._requests[key] = valid_timestamps

        count = len(valid_timestamps)
        remaining = max(0, limit - count)
        reset_in = int(self.window_seconds - (now - valid_timestamps[0])) if valid_timestamps else self.window_seconds

        if count >= limit:
            return True, remaining, max(1, reset_in)

        # Record this request
        self._requests[key].append(now)
        return False, remaining - 1, reset_in

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip health check & options preflight
        if request.url.path in ["/health", "/v1/health", "/docs", "/openapi.json"] or request.method == "OPTIONS":
            return await call_next(request)

        key = self._get_key(request)
        is_limited, remaining, reset_in = self._is_rate_limited(key, self.default_limit)

        if is_limited:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Tenant request rate limit exceeded. Please throttle requests.",
                    "retry_after_seconds": reset_in,
                },
                headers={
                    "Retry-After": str(reset_in),
                    "X-RateLimit-Limit": str(self.default_limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_in),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.default_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
