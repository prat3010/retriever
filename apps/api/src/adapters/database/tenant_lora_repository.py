"""SQLAlchemy Implementation of TenantLoraRegistryProtocol (M96).

Provides tenant-scoped persistence, lookup, and atomic hot-activation for
fine-tuned generative LoRA adapters with PostgreSQL RLS isolation and in-memory fallback.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select, update

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import TenantLoraAdapterDb
from src.domain.abstractions.exceptions import TenantIsolationViolationError
from src.domain.abstractions.serverless_gpu import (
    LoraAdapterMetadata,
    TenantLoraRegistryProtocol,
)

logger = logging.getLogger("api")


class SqlTenantLoraRepository(TenantLoraRegistryProtocol):
    """PostgreSQL repository for tenant-scoped LoRA adapters."""

    def __init__(self, enable_db: bool = True) -> None:
        self.enable_db = enable_db
        # Fast in-memory cache / testing fallback: tenant_id -> {adapter_id: LoraAdapterMetadata}
        self._memory_store: dict[str, dict[str, LoraAdapterMetadata]] = {}

    def _validate_tenant_uuid(self, tenant_id: str) -> uuid.UUID:
        try:
            return uuid.UUID(tenant_id)
        except (ValueError, AttributeError) as err:
            raise TenantIsolationViolationError(
                f"Invalid tenant UUID format: {tenant_id}"
            ) from err

    def _to_domain(self, row: TenantLoraAdapterDb) -> LoraAdapterMetadata:
        return LoraAdapterMetadata(
            adapter_id=str(row.adapter_id),
            tenant_id=str(row.tenant_id),
            name=row.name,
            base_model=row.base_model or "meta-llama/Meta-Llama-3.1-8B-Instruct",
            artifact_uri=row.artifact_uri or "",
            rank=row.rank,
            alpha=row.alpha if row.alpha is not None else 32.0,
            target_modules=row.target_modules if isinstance(row.target_modules, list) else [],
            is_active=bool(row.is_active),
            adapter_type=row.adapter_type or "llm",
            created_at=row.created_at.isoformat() if row.created_at else "",
            description=row.domain_tag or "",
        )

    async def register_adapter(
        self, tenant_id: str, adapter: LoraAdapterMetadata
    ) -> LoraAdapterMetadata:
        tenant_uuid = self._validate_tenant_uuid(tenant_id)
        t_id = str(tenant_uuid)

        # Update in-memory fallback store
        if t_id not in self._memory_store:
            self._memory_store[t_id] = {}
        stored_adapter = adapter.model_copy()
        stored_adapter.tenant_id = t_id
        if not stored_adapter.created_at:
            stored_adapter.created_at = datetime.now(UTC).isoformat()
        self._memory_store[t_id][stored_adapter.adapter_id] = stored_adapter

        if not self.enable_db:
            return stored_adapter

        try:
            adapter_uuid = uuid.UUID(stored_adapter.adapter_id)
        except ValueError:
            adapter_uuid = uuid.uuid4()
            stored_adapter.adapter_id = str(adapter_uuid)
            self._memory_store[t_id][stored_adapter.adapter_id] = stored_adapter

        try:
            async with tenant_session(tenant_id=t_id) as session:
                db_item = TenantLoraAdapterDb(
                    adapter_id=adapter_uuid,
                    tenant_id=tenant_uuid,
                    name=stored_adapter.name,
                    domain_tag=stored_adapter.description or "general",
                    rank=stored_adapter.rank,
                    alpha=stored_adapter.alpha,
                    base_model=stored_adapter.base_model,
                    artifact_uri=stored_adapter.artifact_uri,
                    target_modules=stored_adapter.target_modules,
                    adapter_type=stored_adapter.adapter_type,
                    is_active=stored_adapter.is_active,
                )
                session.add(db_item)
                await session.commit()
                await session.refresh(db_item)
                return self._to_domain(db_item)
        except Exception as e:
            logger.debug(f"SqlTenantLoraRepository: DB write skipped (fallback active): {e}")
            return stored_adapter

    async def get_adapter(
        self, tenant_id: str, adapter_id: str
    ) -> LoraAdapterMetadata | None:
        tenant_uuid = self._validate_tenant_uuid(tenant_id)
        t_id = str(tenant_uuid)

        if not self.enable_db:
            return self._memory_store.get(t_id, {}).get(adapter_id)

        try:
            adapter_uuid = uuid.UUID(adapter_id)
            async with tenant_session(tenant_id=t_id) as session:
                stmt = select(TenantLoraAdapterDb).where(
                    TenantLoraAdapterDb.adapter_id == adapter_uuid,
                    TenantLoraAdapterDb.tenant_id == tenant_uuid,
                )
                res = await session.execute(stmt)
                row = res.scalar_one_or_none()
                if row:
                    return self._to_domain(row)
        except Exception:
            pass

        return self._memory_store.get(t_id, {}).get(adapter_id)

    async def list_adapters(
        self, tenant_id: str, adapter_type: str | None = None
    ) -> list[LoraAdapterMetadata]:
        tenant_uuid = self._validate_tenant_uuid(tenant_id)
        t_id = str(tenant_uuid)

        if not self.enable_db:
            adapters = list(self._memory_store.get(t_id, {}).values())
            if adapter_type:
                adapters = [a for a in adapters if a.adapter_type == adapter_type]
            return adapters

        try:
            async with tenant_session(tenant_id=t_id) as session:
                stmt = select(TenantLoraAdapterDb).where(
                    TenantLoraAdapterDb.tenant_id == tenant_uuid
                )
                if adapter_type:
                    stmt = stmt.where(TenantLoraAdapterDb.adapter_type == adapter_type)
                res = await session.execute(stmt)
                rows = res.scalars().all()
                db_items = [self._to_domain(r) for r in rows]
                if db_items:
                    return db_items
        except Exception:
            pass

        adapters = list(self._memory_store.get(t_id, {}).values())
        if adapter_type:
            adapters = [a for a in adapters if a.adapter_type == adapter_type]
        return adapters

    async def activate_adapter(
        self, tenant_id: str, adapter_id: str
    ) -> LoraAdapterMetadata:
        tenant_uuid = self._validate_tenant_uuid(tenant_id)
        t_id = str(tenant_uuid)

        target = await self.get_adapter(tenant_id, adapter_id)
        if not target:
            raise KeyError(f"LoRA adapter {adapter_id} not found for tenant {tenant_id}")

        ad_type = target.adapter_type
        if t_id in self._memory_store:
            for k, v in self._memory_store[t_id].items():
                if v.adapter_type == ad_type:
                    v.is_active = (k == adapter_id)

        target.is_active = True

        if not self.enable_db:
            return target

        try:
            adapter_uuid = uuid.UUID(adapter_id)
            async with tenant_session(tenant_id=t_id) as session:
                await session.execute(
                    update(TenantLoraAdapterDb)
                    .where(
                        TenantLoraAdapterDb.tenant_id == tenant_uuid,
                        TenantLoraAdapterDb.adapter_type == ad_type,
                    )
                    .values(is_active=False)
                )
                await session.execute(
                    update(TenantLoraAdapterDb)
                    .where(
                        TenantLoraAdapterDb.adapter_id == adapter_uuid,
                        TenantLoraAdapterDb.tenant_id == tenant_uuid,
                    )
                    .values(is_active=True)
                )
                await session.commit()
        except Exception as e:
            logger.debug(f"SqlTenantLoraRepository: DB activation skipped (fallback active): {e}")

        return target

    async def deactivate_adapter(
        self, tenant_id: str, adapter_id: str
    ) -> bool:
        tenant_uuid = self._validate_tenant_uuid(tenant_id)
        t_id = str(tenant_uuid)

        if t_id in self._memory_store and adapter_id in self._memory_store[t_id]:
            self._memory_store[t_id][adapter_id].is_active = False

        if not self.enable_db:
            return True

        try:
            adapter_uuid = uuid.UUID(adapter_id)
            async with tenant_session(tenant_id=t_id) as session:
                await session.execute(
                    update(TenantLoraAdapterDb)
                    .where(
                        TenantLoraAdapterDb.adapter_id == adapter_uuid,
                        TenantLoraAdapterDb.tenant_id == tenant_uuid,
                    )
                    .values(is_active=False)
                )
                await session.commit()
                return True
        except Exception:
            return True

    async def delete_adapter(
        self, tenant_id: str, adapter_id: str
    ) -> bool:
        tenant_uuid = self._validate_tenant_uuid(tenant_id)
        t_id = str(tenant_uuid)

        found = False
        if t_id in self._memory_store and adapter_id in self._memory_store[t_id]:
            del self._memory_store[t_id][adapter_id]
            found = True

        if not self.enable_db:
            return found

        try:
            adapter_uuid = uuid.UUID(adapter_id)
            async with tenant_session(tenant_id=t_id) as session:
                res = await session.execute(
                    delete(TenantLoraAdapterDb).where(
                        TenantLoraAdapterDb.adapter_id == adapter_uuid,
                        TenantLoraAdapterDb.tenant_id == tenant_uuid,
                    )
                )
                await session.commit()
                if res.rowcount and res.rowcount > 0:
                    found = True
        except Exception:
            pass

        return found

    async def get_active_adapter(
        self, tenant_id: str, adapter_type: str = "llm"
    ) -> LoraAdapterMetadata | None:
        tenant_uuid = self._validate_tenant_uuid(tenant_id)
        t_id = str(tenant_uuid)

        if not self.enable_db:
            adapters = self._memory_store.get(t_id, {})
            for a in adapters.values():
                if a.adapter_type == adapter_type and a.is_active:
                    return a
            return None

        try:
            async with tenant_session(tenant_id=t_id) as session:
                stmt = select(TenantLoraAdapterDb).where(
                    TenantLoraAdapterDb.tenant_id == tenant_uuid,
                    TenantLoraAdapterDb.adapter_type == adapter_type,
                    TenantLoraAdapterDb.is_active == True,
                )
                res = await session.execute(stmt)
                row = res.scalar_one_or_none()
                if row:
                    return self._to_domain(row)
        except Exception:
            pass

        adapters = self._memory_store.get(t_id, {})
        for a in adapters.values():
            if a.adapter_type == adapter_type and a.is_active:
                return a
        return None
