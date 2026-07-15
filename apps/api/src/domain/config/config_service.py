from src.domain.abstractions.config import (
    ConfigCache,
    ConfigRegistry,
    TenantConfiguration,
)


class ConfigurationService:
    def __init__(self, registry: ConfigRegistry, cache: ConfigCache, env_secrets: dict[str, str] | None = None) -> None:
        self.registry = registry
        self.cache = cache
        self.env_secrets = env_secrets or {}

    async def get_global_config(self) -> TenantConfiguration:
        """Fetch global configuration, integrating caching and environment defaults."""
        # 1. Check L1 Cache
        cached = await self.cache.get_cached_global_config()
        if cached:
            return self._resolve_env_variables(cached)

        # 2. Check Database
        raw = await self.registry.get_raw_config(tenant_id=None)
        if raw:
            config = TenantConfiguration(**raw)
        else:
            config = TenantConfiguration()
            # Save defaults back to DB for parity
            await self.registry.save_raw_config(tenant_id=None, config_data=config.model_dump())

        # 3. Store to Cache
        await self.cache.set_cached_global_config(config)
        return self._resolve_env_variables(config)

    async def get_tenant_config(self, tenant_id: str) -> TenantConfiguration:
        """Resolve full tenant configuration, inheriting and overlaying from global configs."""
        # 1. Check L1 Cache
        cached = await self.cache.get_cached_config(tenant_id)
        if cached:
            return self._resolve_env_variables(cached)

        # 2. Fetch Global config as baseline
        global_config = await self.get_global_config()

        # 3. Fetch Tenant override config from DB
        raw = await self.registry.get_raw_config(tenant_id=tenant_id)
        if raw:
            tenant_override = TenantConfiguration(**raw)
            config = self._merge_configurations(global_config, tenant_override)
            config.tenant_id = tenant_id
        else:
            config = global_config.model_copy(deep=True)
            config.tenant_id = tenant_id

        # 4. Store to Cache
        await self.cache.set_cached_config(tenant_id, config)
        return self._resolve_env_variables(config)

    async def update_global_config(self, config: TenantConfiguration) -> None:
        """Update global configuration in DB and invalidate cache (hot reload)."""
        await self.registry.save_raw_config(tenant_id=None, config_data=config.model_dump())
        await self.cache.invalidate_global_config()

    async def update_tenant_config(self, tenant_id: str, config: TenantConfiguration) -> None:
        """Update tenant configuration in DB and invalidate cache (hot reload)."""
        config.tenant_id = tenant_id
        await self.registry.save_raw_config(tenant_id=tenant_id, config_data=config.model_dump())
        await self.cache.invalidate_config(tenant_id)

    async def warm_up_cache(self, tenant_ids: list[str]) -> None:
        """Warm up Redis configs cache at startup."""
        try:
            await self.get_global_config()
            for tid in tenant_ids:
                await self.get_tenant_config(tid)
        except Exception:
            pass

    def _resolve_env_variables(self, config: TenantConfiguration) -> TenantConfiguration:
        """Resolve secret placeholder strings from dynamic environment variables."""
        resolved = config.model_copy(deep=True)

        # AI provider credentials resolution
        if resolved.ai_provider.api_key is None or resolved.ai_provider.api_key == "********":
            if resolved.feature_flags.allow_platform_key or resolved.tenant_id == "00000000-0000-0000-0000-000000000000":
                provider = resolved.ai_provider.provider_name.upper()
                env_key = f"{provider}_API_KEY"
                resolved.ai_provider.api_key = self.env_secrets.get(env_key, resolved.ai_provider.api_key)

        # Embedding provider credentials resolution
        if resolved.embedding_provider.api_key is None or resolved.embedding_provider.api_key == "********":
            if resolved.feature_flags.allow_platform_key or resolved.tenant_id == "00000000-0000-0000-0000-000000000000":
                provider = resolved.embedding_provider.provider_name.upper()
                env_key = f"{provider}_API_KEY"
                resolved.embedding_provider.api_key = self.env_secrets.get(env_key, resolved.embedding_provider.api_key)

        # Web search API key resolution — fall back to env var for the configured provider
        if resolved.retrieval_settings.web_search_api_key is None or resolved.retrieval_settings.web_search_api_key == "********":
            if resolved.feature_flags.allow_platform_key or resolved.tenant_id == "00000000-0000-0000-0000-000000000000":
                provider = resolved.retrieval_settings.web_search_provider.upper()
                env_key = f"{provider}_API_KEY"
                resolved.retrieval_settings.web_search_api_key = self.env_secrets.get(env_key, resolved.retrieval_settings.web_search_api_key)

        return resolved

    def _merge_configurations(
        self, base: TenantConfiguration, override: TenantConfiguration
    ) -> TenantConfiguration:
        """Layer override configuration fields over the base configuration."""
        merged_data = base.model_dump()
        override_data = override.model_dump(exclude_unset=True)

        for key, value in override_data.items():
            if isinstance(value, dict) and key in merged_data and isinstance(merged_data[key], dict):
                for sub_key, sub_val in value.items():
                    if sub_val is not None:
                        merged_data[key][sub_key] = sub_val
            elif value is not None:
                merged_data[key] = value

        return TenantConfiguration(**merged_data)
