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


class PromptTemplateNotFoundError(DomainError):
    """Exception raised when no prompt template is found in the DB for a tenant."""

    def __init__(self, tenant_id: str, name: str) -> None:
        super().__init__(
            f"No prompt template '{name}' found for tenant {tenant_id}. "
            "Seed the `prompt_templates` table or configure one via the API."
        )


class ProviderUnavailableError(ConnectionError):
    """Exception raised when an LLM provider returns a retryable error (timeout, 5xx, rate limit)."""
    pass
