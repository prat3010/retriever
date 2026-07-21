import os
import shutil
import uuid

from sqlalchemy import func, select

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import (
    ApiKeyDb,
    AuditLogDb,
    ChatMessageDb,
    ChatMessageFeedbackDb,
    ChatSessionDb,
    ConfigurationDb,
    DocumentChunkDb,
    DocumentDb,
    EvalDatasetDb,
    EvalRunDb,
    InferenceLogDb,
    PromptTemplateDb,
    SemanticCacheDb,
    TenantDb,
    UserDb,
    VectorRecordDb,
)
from src.domain.abstractions.admin import AdminRepository

SYSTEM_TENANT_UUID = uuid.UUID("00000000-0000-0000-0000-000000000000")


class SqlAdminRepository(AdminRepository):

    async def get_platform_stats(self) -> dict[str, int]:
        async with tenant_session(bypass_rls=True) as session:
            tenants_total = (
                await session.execute(
                    select(func.count(TenantDb.tenant_id))
                )
            ).scalar() or 0
            tenants_active = (
                await session.execute(
                    select(func.count(TenantDb.tenant_id)).where(
                        TenantDb.status == "active"
                    )
                )
            ).scalar() or 0
            tenants_suspended = (
                await session.execute(
                    select(func.count(TenantDb.tenant_id)).where(
                        TenantDb.status == "suspended"
                    )
                )
            ).scalar() or 0

            docs_total = (
                await session.execute(
                    select(func.count(DocumentDb.document_id)).where(
                        DocumentDb.is_deleted == False
                    )
                )
            ).scalar() or 0

            chunks_total = (
                await session.execute(
                    select(func.count(DocumentChunkDb.chunk_id))
                )
            ).scalar() or 0
            vectors_total = (
                await session.execute(
                    select(func.count(VectorRecordDb.chunk_id))
                )
            ).scalar() or 0

            keys_total = (
                await session.execute(
                    select(func.count(ApiKeyDb.key_id))
                )
            ).scalar() or 0
            users_total = (
                await session.execute(
                    select(func.count(UserDb.user_id))
                )
            ).scalar() or 0
            sessions_total = (
                await session.execute(
                    select(func.count(ChatSessionDb.session_id))
                )
            ).scalar() or 0
            messages_total = (
                await session.execute(
                    select(func.count(ChatMessageDb.message_id))
                )
            ).scalar() or 0

            audit_logs_total = (
                await session.execute(
                    select(func.count(AuditLogDb.log_id))
                )
            ).scalar() or 0
            eval_runs_total = (
                await session.execute(
                    select(func.count(EvalRunDb.run_id))
                )
            ).scalar() or 0

        return {
            "tenants": {
                "total": tenants_total,
                "active": tenants_active,
                "suspended": tenants_suspended,
            },
            "documents": {"total": docs_total},
            "chunks": {"total": chunks_total},
            "vectors": {"total": vectors_total},
            "apiKeys": {"total": keys_total},
            "users": {"total": users_total},
            "chat": {
                "sessions": sessions_total,
                "messages": messages_total,
            },
            "auditLogs": {"total": audit_logs_total},
            "evaluations": {"runs": eval_runs_total},
        }

    async def reset_platform(
        self, include_system_tenant: bool = False
    ) -> int:
        async with tenant_session(bypass_rls=True) as session:
            result = await session.execute(
                select(TenantDb).where(
                    TenantDb.tenant_id != SYSTEM_TENANT_UUID
                )
            )
            tenants = result.scalars().all()

            for t in tenants:
                tenant_id_str = str(t.tenant_id)
                for base_dir in ["./storage", "apps/api/storage"]:
                    tenant_dir = os.path.join(base_dir, tenant_id_str)
                    if os.path.exists(tenant_dir):
                        try:
                            shutil.rmtree(tenant_dir)
                        except Exception:
                            pass
                await session.delete(t)

            if include_system_tenant:
                for base_dir in ["./storage", "apps/api/storage"]:
                    tenant_dir = os.path.join(
                        base_dir, str(SYSTEM_TENANT_UUID)
                    )
                    if os.path.exists(tenant_dir):
                        try:
                            shutil.rmtree(tenant_dir)
                        except Exception:
                            pass

                tables = [
                    (
                        VectorRecordDb.__table__.delete(),
                        VectorRecordDb.tenant_id,
                    ),
                    (
                        DocumentChunkDb.__table__.delete(),
                        DocumentChunkDb.tenant_id,
                    ),
                    (
                        DocumentDb.__table__.delete(),
                        DocumentDb.tenant_id,
                    ),
                    (
                        ChatMessageFeedbackDb.__table__.delete(),
                        ChatMessageFeedbackDb.tenant_id,
                    ),
                    (
                        InferenceLogDb.__table__.delete(),
                        InferenceLogDb.tenant_id,
                    ),
                    (
                        ChatMessageDb.__table__.delete(),
                        ChatMessageDb.tenant_id,
                    ),
                    (
                        ChatSessionDb.__table__.delete(),
                        ChatSessionDb.tenant_id,
                    ),
                    (
                        EvalRunDb.__table__.delete(),
                        EvalRunDb.tenant_id,
                    ),
                    (
                        EvalDatasetDb.__table__.delete(),
                        EvalDatasetDb.tenant_id,
                    ),
                    (
                        SemanticCacheDb.__table__.delete(),
                        SemanticCacheDb.tenant_id,
                    ),
                    (
                        PromptTemplateDb.__table__.delete(),
                        PromptTemplateDb.tenant_id,
                    ),
                    (
                        ApiKeyDb.__table__.delete(),
                        ApiKeyDb.tenant_id,
                    ),
                    (
                        UserDb.__table__.delete(),
                        UserDb.tenant_id,
                    ),
                ]
                for stmt, col in tables:
                    await session.execute(
                        stmt.where(col == SYSTEM_TENANT_UUID)
                    )
                await session.execute(
                    ConfigurationDb.__table__.delete().where(
                        (ConfigurationDb.tenant_id == SYSTEM_TENANT_UUID)
                        | (ConfigurationDb.tenant_id.is_(None))
                    )
                )

            await session.flush()

        return len(tenants)
