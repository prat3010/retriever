import uuid
from typing import Any

from sqlalchemy import select

from processing_core import ConfigEncrypter
from src.adapters.database.connection import tenant_session
from src.adapters.database.models import ConfigurationDb
from src.config import settings
from src.domain.abstractions.config import ConfigRegistry


class SqlConfigRegistry(ConfigRegistry):
    def __init__(self, key_encryption_key: str | None = None) -> None:
        kek = key_encryption_key or settings.KEY_ENCRYPTION_KEY
        self.encrypter = ConfigEncrypter(kek)

    def _encrypt_payload(self, config_data: dict[str, Any]) -> dict[str, Any]:
        copied = dict(config_data)
        if "ai_provider" in copied and isinstance(copied["ai_provider"], dict):
            provider = dict(copied["ai_provider"])
            if provider.get("api_key"):
                provider["api_key"] = self.encrypter.encrypt(provider["api_key"])
            copied["ai_provider"] = provider
        if "embedding_provider" in copied and isinstance(copied["embedding_provider"], dict):
            provider = dict(copied["embedding_provider"])
            if provider.get("api_key"):
                provider["api_key"] = self.encrypter.encrypt(provider["api_key"])
            copied["embedding_provider"] = provider
        return copied

    def _decrypt_payload(self, config_data: dict[str, Any]) -> dict[str, Any]:
        copied = dict(config_data)
        if "ai_provider" in copied and isinstance(copied["ai_provider"], dict):
            provider = dict(copied["ai_provider"])
            if provider.get("api_key"):
                provider["api_key"] = self.encrypter.decrypt(provider["api_key"])
            copied["ai_provider"] = provider
        if "embedding_provider" in copied and isinstance(copied["embedding_provider"], dict):
            provider = dict(copied["embedding_provider"])
            if provider.get("api_key"):
                provider["api_key"] = self.encrypter.decrypt(provider["api_key"])
            copied["embedding_provider"] = provider
        return copied

    async def get_raw_config(self, tenant_id: str | None) -> dict[str, Any] | None:
        """Retrieve raw configuration dictionary from database."""
        ctx_tenant = tenant_id if tenant_id else None
        bypass = True if tenant_id is None else False

        async with tenant_session(tenant_id=ctx_tenant, bypass_rls=bypass) as session:
            if tenant_id:
                stmt = select(ConfigurationDb).where(
                    ConfigurationDb.tenant_id == uuid.UUID(tenant_id),
                    ConfigurationDb.key == "config_payload",
                    ConfigurationDb.is_deleted == False,
                )
            else:
                stmt = select(ConfigurationDb).where(
                    ConfigurationDb.tenant_id.is_(None),
                    ConfigurationDb.key == "config_payload",
                    ConfigurationDb.is_deleted == False,
                )
            result = await session.execute(stmt)
            db_config = result.scalar_one_or_none()
            if not db_config:
                return None
            return self._decrypt_payload(db_config.value)

    async def save_raw_config(self, tenant_id: str | None, config_data: dict[str, Any]) -> None:
        """Persist raw configuration dictionary to database, versioning changes."""
        ctx_tenant = tenant_id if tenant_id else None
        bypass = True if tenant_id is None else False

        encrypted_data = self._encrypt_payload(config_data)

        async with tenant_session(tenant_id=ctx_tenant, bypass_rls=bypass) as session:
            if tenant_id:
                stmt = select(ConfigurationDb).where(
                    ConfigurationDb.tenant_id == uuid.UUID(tenant_id),
                    ConfigurationDb.key == "config_payload",
                    ConfigurationDb.is_deleted == False,
                )
            else:
                stmt = select(ConfigurationDb).where(
                    ConfigurationDb.tenant_id.is_(None),
                    ConfigurationDb.key == "config_payload",
                    ConfigurationDb.is_deleted == False,
                )
            result = await session.execute(stmt)
            db_config = result.scalar_one_or_none()

            if db_config:
                db_config.value = encrypted_data
                db_config.version += 1
            else:
                db_config = ConfigurationDb(
                    tenant_id=uuid.UUID(tenant_id) if tenant_id else None,
                    key="config_payload",
                    value=encrypted_data,
                    version=1,
                )
                session.add(db_config)
            await session.flush()
