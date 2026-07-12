import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


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
