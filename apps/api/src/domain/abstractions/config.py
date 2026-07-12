from abc import ABC, abstractmethod
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class FeatureFlags(BaseModel):
    enable_hybrid_search: bool = True
    enable_reranking: bool = True
    enable_sse_streaming: bool = True


class AIProviderConfig(BaseModel):
    provider_name: str = "openai"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_model: str = "gpt-4o"


class EmbeddingProviderConfig(BaseModel):
    provider_name: str = "openai"
    api_key: Optional[str] = None
    model_name: str = "text-embedding-3-small"
    dimension: int = 1536


class StorageProviderConfig(BaseModel):
    provider_type: str = "local"
    bucket_name: Optional[str] = None
    local_path: str = "./storage"


class RetrievalSettings(BaseModel):
    top_k: int = 10
    rrf_k: int = 60
    reranking_threshold: float = 0.7


class SecuritySettings(BaseModel):
    enable_rls: bool = True
    api_key_expiration_days: int = 90


class RateLimits(BaseModel):
    requests_per_minute: int = 60
    tokens_per_minute: int = 100000


class TenantConfiguration(BaseModel):
    tenant_id: Optional[str] = None
    feature_flags: FeatureFlags = Field(default_factory=FeatureFlags)
    ai_provider: AIProviderConfig = Field(default_factory=AIProviderConfig)
    embedding_provider: EmbeddingProviderConfig = Field(default_factory=EmbeddingProviderConfig)
    storage_provider: StorageProviderConfig = Field(default_factory=StorageProviderConfig)
    retrieval_settings: RetrievalSettings = Field(default_factory=RetrievalSettings)
    security_settings: SecuritySettings = Field(default_factory=SecuritySettings)
    rate_limits: RateLimits = Field(default_factory=RateLimits)

    model_config = ConfigDict(populate_by_name=True)

    def redact_secrets(self) -> "TenantConfiguration":
        """Return a copy of the configuration with sensitive credentials masked."""
        copied = self.model_copy(deep=True)
        if copied.ai_provider.api_key:
            copied.ai_provider.api_key = "********"
        if copied.embedding_provider.api_key:
            copied.embedding_provider.api_key = "********"
        return copied


class ConfigRegistry(ABC):
    @abstractmethod
    async def get_raw_config(self, tenant_id: Optional[str]) -> Optional[dict[str, Any]]:
        """Retrieve raw configuration dictionary from database."""
        pass

    @abstractmethod
    async def save_raw_config(self, tenant_id: Optional[str], config_data: dict[str, Any]) -> None:
        """Persist raw configuration dictionary to database."""
        pass


class ConfigCache(ABC):
    @abstractmethod
    async def get_cached_config(self, tenant_id: str) -> Optional[TenantConfiguration]:
        """Fetch cached tenant configurations, returning None if cache misses."""
        pass

    @abstractmethod
    async def set_cached_config(self, tenant_id: str, config: TenantConfiguration) -> None:
        """Cache configuration parameters with TTL boundary."""
        pass

    @abstractmethod
    async def get_cached_global_config(self) -> Optional[TenantConfiguration]:
        """Fetch cached global configurations, returning None if cache misses."""
        pass

    @abstractmethod
    async def set_cached_global_config(self, config: TenantConfiguration) -> None:
        """Cache global configurations with TTL."""
        pass

    @abstractmethod
    async def invalidate_config(self, tenant_id: str) -> None:
        """Invalidate the cached tenant configuration parameters immediately."""
        pass

    @abstractmethod
    async def invalidate_global_config(self) -> None:
        """Invalidate the cached global configuration parameters immediately."""
        pass
