import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship
from pgvector.sqlalchemy import Vector


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TenantDb(Base):
    __tablename__ = "tenants"

    tenant_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="active")
    tier = Column(String(50), nullable=False, default="standard")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    config = relationship("TenantConfigDb", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    api_keys = relationship("ApiKeyDb", back_populates="tenant", cascade="all, delete")


class TenantConfigDb(Base):
    __tablename__ = "tenant_configs"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        primary_key=True,
    )
    active_model = Column(String(255), nullable=False, default="claude-3-5-sonnet")
    temperature = Column(Float, nullable=False, default=0.2)
    chunk_size = Column(Integer, nullable=False, default=500)
    chunk_overlap = Column(Integer, nullable=False, default=100)
    system_prompt_template = Column(Text, nullable=False, default="You are a helpful grounding assistant.")

    # Relationships
    tenant = relationship("TenantDb", back_populates="config")


class ApiKeyDb(Base):
    __tablename__ = "api_keys"

    key_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    prefix = Column(String(50), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("TenantDb", back_populates="api_keys")


class AuditLogDb(Base):
    __tablename__ = "audit_logs"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    action = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    details = Column(Text, nullable=True)


class ConfigurationDb(Base):
    __tablename__ = "configurations"

    config_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    key = Column(String(255), nullable=False, index=True)
    value = Column(JSONB, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    is_deleted = Column(Boolean, nullable=False, default=False)


class DocumentDb(Base):
    __tablename__ = "documents"

    document_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)
    storage_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default="uploaded")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    is_deleted = Column(Boolean, nullable=False, default=False)

    # Relationships
    chunks = relationship("DocumentChunkDb", back_populates="document", cascade="all, delete-orphan")


class DocumentChunkDb(Base):
    __tablename__ = "document_chunks"

    chunk_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    parent_chunk_id = Column(UUID(as_uuid=True), ForeignKey("document_chunks.chunk_id", ondelete="SET NULL"), nullable=True)
    meta_data = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    document = relationship("DocumentDb", back_populates="chunks")


class VectorRecordDb(Base):
    __tablename__ = "vector_records"

    chunk_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.chunk_id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    embedding = Column(Vector(1536), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
