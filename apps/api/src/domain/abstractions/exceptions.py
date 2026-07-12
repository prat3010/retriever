class DomainError(Exception):
    """Base domain exception for all Retriever errors."""

    pass


class AuthenticationError(DomainError):
    """Exception raised if authorization credentials fail validation."""

    pass


class TenantNotFoundError(DomainError):
    """Exception raised if requested tenant is not registered."""

    pass


class ApiKeyNotFoundError(DomainError):
    """Exception raised if requested api key does not exist."""

    pass


class TenantIsolationViolationError(DomainError):
    """Exception raised if a tenant context breach is detected."""

    pass
