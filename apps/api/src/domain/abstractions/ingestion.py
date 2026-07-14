from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class Document(BaseModel):
    document_id: str
    tenant_id: str
    filename: str
    file_hash: str
    storage_path: str
    file_size: int
    mime_type: str
    status: str
    created_at: str
    updated_at: str


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    tenant_id: str
    content: str
    token_count: int
    chunk_index: int
    parent_chunk_id: str | None = None
    meta_data: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class DocumentRepository(ABC):
    """Port for document metadata CRUD."""

    @abstractmethod
    async def list_documents(self, tenant_id: str, bypass_rls: bool = False) -> list[Document]:
        """List non-deleted documents for a tenant, newest first."""
        pass

    @abstractmethod
    async def list_documents_cursor(
        self, tenant_id: str, limit: int = 50, cursor: str | None = None, bypass_rls: bool = False
    ) -> tuple[list[Document], str | None, bool]:
        """List documents using cursor-based pagination. Returns (items, next_cursor, has_more)."""
        pass

    @abstractmethod
    async def get_document(self, tenant_id: str, document_id: str, bypass_rls: bool = False) -> Document | None:
        """Get a single document by ID, scoped to tenant."""
        pass

    @abstractmethod
    async def find_by_hash(self, tenant_id: str, file_hash: str) -> Document | None:
        """Find an active document by file hash (dedup check)."""
        pass

    @abstractmethod
    async def create_document(self, tenant_id: str, doc: Document) -> None:
        """Persist a new document record."""
        pass

    @abstractmethod
    async def soft_delete(self, tenant_id: str, document_id: str) -> str | None:
        """Mark a document as deleted, remove chunks. Returns storage_path for cleanup, or None if not found."""
        pass


class DocumentStorage(ABC):
    @abstractmethod
    async def save_file(self, tenant_id: str, filename: str, content: bytes) -> str:
        """Persist file to storage medium, returning the physical storage path location."""
        pass

    @abstractmethod
    async def delete_file(self, storage_path: str) -> None:
        """Remove file from storage medium."""
        pass


class DocumentParser(ABC):
    @abstractmethod
    def parse_file(self, file_path: str, mime_type: str) -> str:
        """Extract unstructured text contents from target document file."""
        pass


class TextChunker(ABC):
    @abstractmethod
    def split_text(self, text: str, chunk_size: int, chunk_overlap: int) -> list[dict[str, Any]]:
        """Split text contents into size-bounded chunks using sliding window boundaries."""
        pass
