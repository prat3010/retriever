"""Document metadata repository implementation."""

import uuid

from sqlalchemy import delete, select

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import DocumentChunkDb, DocumentDb
from src.domain.abstractions.ingestion import Document, DocumentRepository


class SqlDocumentRepository(DocumentRepository):
    """SQLAlchemy-backed document metadata repository."""

    def _to_domain(self, row: DocumentDb) -> Document:
        return Document(
            document_id=str(row.document_id),
            tenant_id=str(row.tenant_id),
            filename=row.filename,
            file_hash=row.file_hash or "",
            storage_path=row.storage_path or "",
            file_size=row.file_size,
            mime_type=row.mime_type,
            status=row.status,
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat(),
        )

    async def list_documents(self, tenant_id: str, bypass_rls: bool = False) -> list[Document]:
        async with tenant_session(tenant_id=tenant_id, bypass_rls=bypass_rls) as session:
            stmt = (
                select(DocumentDb)
                .where(DocumentDb.tenant_id == uuid.UUID(tenant_id), DocumentDb.is_deleted == False)
                .order_by(DocumentDb.created_at.desc())
            )
            return [self._to_domain(r) for r in (await session.execute(stmt)).scalars().all()]

    async def get_document(self, tenant_id: str, document_id: str, bypass_rls: bool = False) -> Document | None:
        async with tenant_session(tenant_id=tenant_id, bypass_rls=bypass_rls) as session:
            stmt = select(DocumentDb).where(
                DocumentDb.tenant_id == uuid.UUID(tenant_id),
                DocumentDb.document_id == uuid.UUID(document_id),
                DocumentDb.is_deleted == False,
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            return self._to_domain(row) if row else None

    async def find_by_hash(self, tenant_id: str, file_hash: str) -> Document | None:
        async with tenant_session(tenant_id=tenant_id) as session:
            stmt = select(DocumentDb).where(
                DocumentDb.tenant_id == uuid.UUID(tenant_id),
                DocumentDb.file_hash == file_hash,
                DocumentDb.is_deleted == False,
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            return self._to_domain(row) if row else None

    async def create_document(self, tenant_id: str, doc: Document) -> None:
        async with tenant_session(tenant_id=tenant_id) as session:
            session.add(
                DocumentDb(
                    document_id=uuid.UUID(doc.document_id),
                    tenant_id=uuid.UUID(tenant_id),
                    filename=doc.filename,
                    file_hash=doc.file_hash,
                    storage_path=doc.storage_path,
                    file_size=doc.file_size,
                    mime_type=doc.mime_type,
                    status=doc.status,
                )
            )
            await session.flush()

    async def soft_delete(self, tenant_id: str, document_id: str) -> str | None:
        async with tenant_session(tenant_id=tenant_id) as session:
            stmt = select(DocumentDb).where(
                DocumentDb.tenant_id == uuid.UUID(tenant_id),
                DocumentDb.document_id == uuid.UUID(document_id),
                DocumentDb.is_deleted == False,
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            if not row:
                return None
            storage_path = row.storage_path or ""
            row.is_deleted = True
            await session.execute(
                delete(DocumentChunkDb).where(DocumentChunkDb.document_id == uuid.UUID(document_id))
            )
            await session.flush()
            return storage_path
