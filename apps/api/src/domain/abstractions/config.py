from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FeatureFlags(BaseModel):
    enable_hybrid_search: bool = True
    enable_reranking: bool = True
    enable_sse_streaming: bool = True
    enable_web_search: bool = False


class ModelPricing(BaseModel):
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
    currency: str = "USD"


DEFAULT_PRICING: dict[str, ModelPricing] = {
    "gemini-1.5-flash": ModelPricing(input_cost_per_1k=0.075, output_cost_per_1k=0.30),
    "gemini-1.5-pro": ModelPricing(input_cost_per_1k=1.25, output_cost_per_1k=5.0),
    "gpt-4o": ModelPricing(input_cost_per_1k=2.5, output_cost_per_1k=10.0),
    "gpt-4o-mini": ModelPricing(input_cost_per_1k=0.15, output_cost_per_1k=0.60),
    "claude-3-5-sonnet-20240620": ModelPricing(input_cost_per_1k=3.0, output_cost_per_1k=15.0),
    "claude-3-haiku": ModelPricing(input_cost_per_1k=0.25, output_cost_per_1k=1.25),
}


class AIProviderConfig(BaseModel):
    provider_name: str = "openai"
    api_key: str | None = None
    base_url: str | None = "https://generativelanguage.googleapis.com/v1beta/openai/"
    default_model: str = "gemini-1.5-flash"
    fallback_provider: str = ""
    fallback_model: str = ""
    retry_attempts: int = 2
    retry_delay_ms: int = 500
    pricing: dict[str, ModelPricing] = Field(default_factory=lambda: dict(DEFAULT_PRICING))


class EmbeddingProviderConfig(BaseModel):
    provider_name: str = "openai"
    api_key: str | None = None
    model_name: str = "text-embedding-004"
    dimension: int = 768


class StorageProviderConfig(BaseModel):
    provider_type: str = "local"
    bucket_name: str | None = None
    local_path: str = "./storage"


class RetrievalSettings(BaseModel):
    top_k: int = 10
    rrf_k: int = 60
    reranking_threshold: float = 0.7
    chunk_size: int = 500
    chunk_overlap: int = 100
    citation_template: str = "[{index}]"
    summarize_after_turns: int = 15
    web_search_threshold: float = 0.65
    web_search_provider: str = "tavily"
    web_search_max_results: int = 5


class SecuritySettings(BaseModel):
    enable_rls: bool = True
    api_key_expiration_days: int = 90
    data_retention_ttl_days: int | None = None


class RateLimits(BaseModel):
    requests_per_minute: int = 60
    tokens_per_minute: int = 100000


class ChunkingSettings(BaseModel):
    strategy: Literal["fixed_window", "recursive", "semantic"] = "fixed_window"
    chunk_size: int = 500
    chunk_overlap: int = 100
    semantic_threshold: float = 0.95


class MetadataExtractorConfig(BaseModel):
    name: str
    extractor_type: Literal["regex", "llm"]
    pattern: str | None = None
    schema_definition: dict[str, Any] | None = None


class GuardrailConfig(BaseModel):
    name: str
    guard_type: Literal["pii_regex", "llm_safety"]
    patterns: list[str] | None = None
    llm_prompt_template: str | None = None


class TenantConfiguration(BaseModel):
    tenant_id: str | None = None
    feature_flags: FeatureFlags = Field(default_factory=FeatureFlags)
    ai_provider: AIProviderConfig = Field(default_factory=AIProviderConfig)
    embedding_provider: EmbeddingProviderConfig = Field(default_factory=EmbeddingProviderConfig)
    storage_provider: StorageProviderConfig = Field(default_factory=StorageProviderConfig)
    retrieval_settings: RetrievalSettings = Field(default_factory=RetrievalSettings)
    security_settings: SecuritySettings = Field(default_factory=SecuritySettings)
    rate_limits: RateLimits = Field(default_factory=RateLimits)
    chunking_settings: ChunkingSettings = Field(default_factory=ChunkingSettings)
    metadata_extractors: list[MetadataExtractorConfig] = Field(default_factory=list)
    guardrails: list[GuardrailConfig] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

    def redact_secrets(self) -> "TenantConfiguration":
        """Return a copy of the configuration with sensitive credentials masked."""
        copied = self.model_copy(deep=True)
        if copied.ai_provider.api_key is not None:
            copied.ai_provider.api_key = "********"
        if copied.embedding_provider.api_key is not None:
            copied.embedding_provider.api_key = "********"
        return copied


class ConfigRegistry(ABC):
    @abstractmethod
    async def get_raw_config(self, tenant_id: str | None) -> dict[str, Any] | None:
        """Retrieve raw configuration dictionary from database."""
        pass

    @abstractmethod
    async def save_raw_config(self, tenant_id: str | None, config_data: dict[str, Any]) -> None:
        """Persist raw configuration dictionary to database."""
        pass


class ConfigCache(ABC):
    @abstractmethod
    async def get_cached_config(self, tenant_id: str) -> TenantConfiguration | None:
        """Fetch cached tenant configurations, returning None if cache misses."""
        pass

    @abstractmethod
    async def set_cached_config(self, tenant_id: str, config: TenantConfiguration) -> None:
        """Cache configuration parameters with TTL boundary."""
        pass

    @abstractmethod
    async def get_cached_global_config(self) -> TenantConfiguration | None:
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
