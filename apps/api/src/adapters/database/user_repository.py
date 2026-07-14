import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import UserDb
from src.domain.abstractions.identity import UserInfo, UserRepository


class SqlUserRepository(UserRepository):
    async def create_user(
        self, tenant_id: str, external_id: str, display_name: str | None = None
    ) -> UserInfo:
        user_id = uuid.uuid4()
        async with tenant_session(tenant_id=tenant_id) as session:
            db_user = UserDb(
                user_id=user_id,
                tenant_id=uuid.UUID(tenant_id),
                external_id=external_id,
                display_name=display_name,
            )
            session.add(db_user)
            try:
                await session.flush()
            except IntegrityError:
                raise ValueError(
                    f"User with external_id '{external_id}' already exists in tenant {tenant_id}."
                ) from None
            return UserInfo(
                user_id=str(db_user.user_id),
                tenant_id=str(db_user.tenant_id),
                external_id=db_user.external_id,
                display_name=db_user.display_name,
                is_active=db_user.is_active,
                created_at=db_user.created_at.isoformat(),
            )

    async def get_user(self, tenant_id: str, user_id: str) -> UserInfo | None:
        async with tenant_session(tenant_id=tenant_id) as session:
            stmt = select(UserDb).where(
                UserDb.user_id == uuid.UUID(user_id),
                UserDb.tenant_id == uuid.UUID(tenant_id),
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if not row:
                return None
            return UserInfo(
                user_id=str(row.user_id),
                tenant_id=str(row.tenant_id),
                external_id=row.external_id,
                display_name=row.display_name,
                is_active=row.is_active,
                created_at=row.created_at.isoformat(),
            )

    async def list_users(self, tenant_id: str) -> list[UserInfo]:
        async with tenant_session(tenant_id=tenant_id) as session:
            stmt = select(UserDb).where(
                UserDb.tenant_id == uuid.UUID(tenant_id),
                UserDb.is_active == True,
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                UserInfo(
                    user_id=str(r.user_id),
                    tenant_id=str(r.tenant_id),
                    external_id=r.external_id,
                    display_name=r.display_name,
                    is_active=r.is_active,
                    created_at=r.created_at.isoformat(),
                )
                for r in rows
            ]

    async def deactivate_user(self, tenant_id: str, user_id: str) -> None:
        async with tenant_session(tenant_id=tenant_id) as session:
            stmt = select(UserDb).where(
                UserDb.user_id == uuid.UUID(user_id),
                UserDb.tenant_id == uuid.UUID(tenant_id),
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row:
                row.is_active = False
                await session.flush()
