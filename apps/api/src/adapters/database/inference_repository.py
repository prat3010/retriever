"""Inference Database Repositories.

Implements ChatSessionRepository, PromptTemplateRegistry, and
InferenceLogWriter ports using SQLAlchemy ORM with RLS enforcement.
"""

import uuid

from sqlalchemy import select

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import (
    ChatMessageDb,
    ChatSessionDb,
    InferenceLogDb,
    PromptTemplateDb,
)
from src.adapters.database.pagination import encode_cursor, decode_cursor
from src.domain.abstractions.inference import (
    ChatMessage,
    ChatMessageInfo,
    ChatSessionInfo,
    ChatSessionRepository,
    InferenceLog,
    InferenceLogWriter,
    PromptTemplate,
    PromptTemplateRegistry,
    ToolCall,
)


class SqlPromptTemplateRegistry(PromptTemplateRegistry):
    """SQLAlchemy-backed prompt template registry."""

    async def get_template(
        self, tenant_id: str, name: str, bypass_rls: bool = False
    ) -> PromptTemplate | None:
        async with tenant_session(tenant_id=tenant_id, bypass_rls=bypass_rls) as session:
            stmt = select(PromptTemplateDb).where(
                PromptTemplateDb.tenant_id == uuid.UUID(tenant_id),
                PromptTemplateDb.name == name,
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if not row:
                return None
            return PromptTemplate(
                prompt_id=str(row.prompt_id),
                tenant_id=str(row.tenant_id),
                name=row.name,
                content=row.content,
                is_system_prompt=row.is_system_prompt,
            )

    async def save_template(
        self, tenant_id: str, template: PromptTemplate, bypass_rls: bool = False
    ) -> None:
        async with tenant_session(tenant_id=tenant_id, bypass_rls=bypass_rls) as session:
            stmt = select(PromptTemplateDb).where(
                PromptTemplateDb.tenant_id == uuid.UUID(tenant_id),
                PromptTemplateDb.name == template.name,
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row:
                row.content = template.content
                row.is_system_prompt = template.is_system_prompt
            else:
                session.add(
                    PromptTemplateDb(
                        tenant_id=uuid.UUID(tenant_id),
                        name=template.name,
                        content=template.content,
                        is_system_prompt=template.is_system_prompt,
                    )
                )
            await session.flush()

    async def list_templates(self, tenant_id: str, bypass_rls: bool = False) -> list[PromptTemplate]:
        async with tenant_session(tenant_id=tenant_id, bypass_rls=bypass_rls) as session:
            stmt = select(PromptTemplateDb).where(
                PromptTemplateDb.tenant_id == uuid.UUID(tenant_id),
            ).order_by(PromptTemplateDb.name)
            result = await session.execute(stmt)
            return [
                PromptTemplate(
                    prompt_id=str(row.prompt_id),
                    tenant_id=str(row.tenant_id),
                    name=row.name,
                    content=row.content,
                    is_system_prompt=row.is_system_prompt,
                )
                for row in result.scalars().all()
            ]

    async def delete_template(self, tenant_id: str, name: str, bypass_rls: bool = False) -> bool:
        async with tenant_session(tenant_id=tenant_id, bypass_rls=bypass_rls) as session:
            stmt = select(PromptTemplateDb).where(
                PromptTemplateDb.tenant_id == uuid.UUID(tenant_id),
                PromptTemplateDb.name == name,
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            await session.flush()
            return True


class SqlChatSessionRepository(ChatSessionRepository):
    """SQLAlchemy-backed chat session and message repository."""

    async def create_session(
        self, tenant_id: str, user_id: str | None = None
    ) -> ChatSessionInfo:
        session_id = uuid.uuid4()
        user_uuid = uuid.UUID(user_id) if user_id else None
        async with tenant_session(tenant_id=tenant_id) as session:
            db_session = ChatSessionDb(
                session_id=session_id,
                tenant_id=uuid.UUID(tenant_id),
                user_id=user_uuid,
            )
            session.add(db_session)
            await session.flush()
            return ChatSessionInfo(
                session_id=str(db_session.session_id),
                tenant_id=str(db_session.tenant_id),
                user_id=str(db_session.user_id) if db_session.user_id else None,
                created_at=db_session.created_at.isoformat(),
            )

    async def get_session(
        self, session_id: str, tenant_id: str
    ) -> ChatSessionInfo | None:
        async with tenant_session(tenant_id=tenant_id) as session:
            stmt = select(ChatSessionDb).where(
                ChatSessionDb.session_id == uuid.UUID(session_id),
                ChatSessionDb.tenant_id == uuid.UUID(tenant_id),
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if not row:
                return None
            return ChatSessionInfo(
                session_id=str(row.session_id),
                tenant_id=str(row.tenant_id),
                user_id=str(row.user_id) if row.user_id else None,
                created_at=row.created_at.isoformat(),
            )

    async def add_message(
        self, tenant_id: str, session_id: str, message: ChatMessage, user_id: str | None = None
    ) -> None:
        user_uuid = uuid.UUID(user_id) if user_id else None
        async with tenant_session(tenant_id=tenant_id) as session:
            session.add(
                ChatMessageDb(
                    session_id=uuid.UUID(session_id),
                    tenant_id=uuid.UUID(tenant_id),
                    user_id=user_uuid,
                    role=message.role,
                    content=message.content,
                    name=message.name,
                    tool_calls=(
                        [tc.model_dump() for tc in message.tool_calls]
                        if message.tool_calls else None
                    ),
                )
            )
            await session.flush()

    async def get_messages(
        self, tenant_id: str, session_id: str
    ) -> list[ChatMessage]:
        async with tenant_session(tenant_id=tenant_id) as session:
            stmt = (
                select(ChatMessageDb)
                .where(
                    ChatMessageDb.session_id == uuid.UUID(session_id),
                    ChatMessageDb.tenant_id == uuid.UUID(tenant_id),
                )
                .order_by(ChatMessageDb.created_at)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                ChatMessage(
                    role=row.role,
                    content=row.content,
                    name=row.name,
                    tool_calls=[
                        ToolCall(**tc) for tc in row.tool_calls
                    ] if row.tool_calls else [],
                )
                for row in rows
            ]

    async def get_messages_cursor(
        self, tenant_id: str, session_id: str, limit: int = 50, cursor: str | None = None
    ) -> tuple[list[ChatMessageInfo], str | None, bool]:
        """Retrieve messages for a session using cursor-based pagination."""
        async with tenant_session(tenant_id=tenant_id) as session:
            stmt = select(ChatMessageDb).where(
                ChatMessageDb.session_id == uuid.UUID(session_id),
                ChatMessageDb.tenant_id == uuid.UUID(tenant_id),
            )

            if cursor:
                try:
                    cursor_time, cursor_id = decode_cursor(cursor)
                    stmt = stmt.where(
                        (ChatMessageDb.created_at < cursor_time) |
                        ((ChatMessageDb.created_at == cursor_time) & (ChatMessageDb.message_id < cursor_id))
                    )
                except ValueError:
                    pass

            stmt = stmt.order_by(ChatMessageDb.created_at.desc(), ChatMessageDb.message_id.desc()).limit(limit + 1)
            result = await session.execute(stmt)
            rows = result.scalars().all()

            has_more = len(rows) > limit
            if has_more:
                rows = rows[:limit]

            rows_chrono = list(reversed(rows))

            items = [
                ChatMessageInfo(
                    message_id=str(row.message_id),
                    session_id=str(row.session_id),
                    tenant_id=str(row.tenant_id),
                    role=row.role,
                    content=row.content,
                    name=row.name,
                    created_at=row.created_at.isoformat() if row.created_at else "",
                )
                for row in rows_chrono
            ]

            next_cursor = None
            if has_more and rows:
                last_fetched = rows[-1]
                next_cursor = encode_cursor(last_fetched.created_at, last_fetched.message_id)

            return items, next_cursor, has_more


class SqlInferenceLogWriter(InferenceLogWriter):
    """SQLAlchemy-backed inference log persister."""

    async def write_log(self, log: InferenceLog) -> None:
        async with tenant_session(tenant_id=log.tenant_id) as session:
            session.add(
                InferenceLogDb(
                    tenant_id=uuid.UUID(log.tenant_id),
                    session_id=uuid.UUID(log.session_id) if log.session_id else None,
                    user_id=uuid.UUID(log.user_id) if log.user_id else None,
                    model_used=log.model_used,
                    input_tokens=log.input_tokens,
                    output_tokens=log.output_tokens,
                    latency_ms=log.latency_ms,
                    cost_usd=log.cost_usd,
                    notes=log.notes,
                )
            )
            await session.flush()
