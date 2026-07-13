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
from src.domain.abstractions.inference import (
    ChatMessage,
    ChatSessionInfo,
    ChatSessionRepository,
    InferenceLog,
    InferenceLogWriter,
    PromptTemplate,
    PromptTemplateRegistry,
)


class SqlPromptTemplateRegistry(PromptTemplateRegistry):
    """SQLAlchemy-backed prompt template registry."""

    async def get_template(
        self, tenant_id: str, name: str
    ) -> PromptTemplate | None:
        async with tenant_session(tenant_id=tenant_id) as session:
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
        self, tenant_id: str, template: PromptTemplate
    ) -> None:
        async with tenant_session(tenant_id=tenant_id) as session:
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


class SqlChatSessionRepository(ChatSessionRepository):
    """SQLAlchemy-backed chat session and message repository."""

    async def create_session(
        self, tenant_id: str
    ) -> ChatSessionInfo:
        session_id = uuid.uuid4()
        async with tenant_session(tenant_id=tenant_id) as session:
            db_session = ChatSessionDb(
                session_id=session_id,
                tenant_id=uuid.UUID(tenant_id),
            )
            session.add(db_session)
            await session.flush()
            return ChatSessionInfo(
                session_id=str(db_session.session_id),
                tenant_id=str(db_session.tenant_id),
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
                created_at=row.created_at.isoformat(),
            )

    async def add_message(
        self, tenant_id: str, session_id: str, message: ChatMessage
    ) -> None:
        async with tenant_session(tenant_id=tenant_id) as session:
            session.add(
                ChatMessageDb(
                    session_id=uuid.UUID(session_id),
                    tenant_id=uuid.UUID(tenant_id),
                    role=message.role,
                    content=message.content,
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
                )
                for row in rows
            ]


class SqlInferenceLogWriter(InferenceLogWriter):
    """SQLAlchemy-backed inference log persister."""

    async def write_log(self, log: InferenceLog) -> None:
        async with tenant_session(tenant_id=log.tenant_id) as session:
            session.add(
                InferenceLogDb(
                    tenant_id=uuid.UUID(log.tenant_id),
                    session_id=uuid.UUID(log.session_id) if log.session_id else None,
                    model_used=log.model_used,
                    input_tokens=log.input_tokens,
                    output_tokens=log.output_tokens,
                    latency_ms=log.latency_ms,
                )
            )
            await session.flush()
