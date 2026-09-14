"""Retriever Python SDK Exception Hierarchy."""


class RetrieverError(Exception):
    """Base exception for all Retriever SDK errors."""
    pass


class AuthenticationError(RetrieverError):
    """Raised when an API key is missing, invalid, or revoked (HTTP 401)."""
    pass


class PermissionDeniedError(RetrieverError):
    """Raised when an operation violates tenant boundary isolation or permissions (HTTP 403)."""
    pass


class NotFoundError(RetrieverError):
    """Raised when a requested resource (document, session, tenant) does not exist (HTTP 404)."""
    pass


class RateLimitExceededError(RetrieverError):
    """Raised when the client exceeds sliding-window rate or token quotas (HTTP 429)."""
    pass


class ApiRequestError(RetrieverError):
    """Raised when the API returns an unexpected error status code."""

    def __init__(self, status_code: int, message: str, body: str | None = None) -> None:
        super().__init__(f"Retriever API Error {status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.body = body
