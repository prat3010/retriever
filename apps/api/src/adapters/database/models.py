import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


def utc_now() -> datetime:
    return datetime.now(UTC)


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
    sessions = relationship("ChatSessionDb", back_populates="tenant", cascade="all, delete")
    users = relationship("UserDb", back_populates="tenant", cascade="all, delete")


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
    system_prompt_template = Column(Text, nullable=False, default="")
    llm_api_key_encrypted = Column(Text, nullable=True)

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
    role = Column(String(50), nullable=False, default="client")
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("TenantDb", back_populates="api_keys")


class UserDb(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_id = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        UniqueConstraint("tenant_id", "external_id", name="uq_users_tenant_external"),
    )

    # Relationships
    tenant = relationship("TenantDb", back_populates="users")
    sessions = relationship("ChatSessionDb", back_populates="user", cascade="all, delete")


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
    entry_hash = Column(String(64), nullable=True)
    previous_hash = Column(String(64), nullable=True)


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
    status = Column(String(50), nullable=False, default="PENDING")
    tags = Column(ARRAY(String), nullable=False, default=list)
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

    __table_args__ = (
        Index("ix_document_chunks_meta_data", meta_data, postgresql_using="gin"),
        Index("idx_document_chunks_tenant_doc_idx", tenant_id, document_id, chunk_index),
    )

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
    embedding = Column(Vector(768), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class PromptTemplateDb(Base):
    __tablename__ = "prompt_templates"

    prompt_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    is_system_prompt = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class ChatSessionDb(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        UniqueConstraint("session_id", "tenant_id", name="uq_chat_sessions_session_tenant"),
        Index("ix_chat_sessions_user_id", "user_id"),
    )

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    messages = relationship(
        "ChatMessageDb", back_populates="session",
        cascade="all, delete-orphan", order_by="ChatMessageDb.created_at"
    )
    user = relationship("UserDb", back_populates="sessions")
    tenant = relationship("TenantDb", back_populates="sessions")


class ChatMessageDb(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["session_id", "tenant_id"],
            ["chat_sessions.session_id", "chat_sessions.tenant_id"],
            name="fk_chat_messages_session_tenant",
            ondelete="CASCADE",
        ),
        Index("ix_chat_messages_user_id", "user_id"),
    )

    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    name = Column(String(255), nullable=True)
    tool_calls = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    session = relationship("ChatSessionDb", back_populates="messages")


class InferenceLogDb(Base):
    __tablename__ = "inference_logs"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.session_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    model_used = Column(String(255), nullable=False)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    latency_ms = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class SemanticCacheDb(Base):
    __tablename__ = "semantic_cache"

    cache_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query_text = Column(Text, nullable=False)
    embedding = Column(Vector(768), nullable=False)
    search_results = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class ChatMessageFeedbackDb(Base):
    __tablename__ = "chat_message_feedback"

    feedback_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.message_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rating = Column(Integer, nullable=False, default=0)  # +1 / -1
    feedback_text = Column(Text, nullable=True)
    scores = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    tenant = relationship("TenantDb")
    message = relationship("ChatMessageDb")
    user = relationship("UserDb")


class EvalDatasetDb(Base):
    __tablename__ = "eval_datasets"

    dataset_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    questions = relationship("EvalQuestionDb", back_populates="dataset", cascade="all, delete-orphan")


class EvalQuestionDb(Base):
    __tablename__ = "eval_questions"

    question_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("eval_datasets.dataset_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question = Column(Text, nullable=False)
    ground_truth_answer = Column(Text, nullable=False)
    relevant_chunk_ids = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    dataset = relationship("EvalDatasetDb", back_populates="questions")


class EvalRunDb(Base):
    __tablename__ = "eval_runs"

    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("eval_datasets.dataset_id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(String(20), nullable=False, default="pending")
    trigger = Column(String(20), nullable=False, default="manual")
    aggregate_scores = Column(JSONB, nullable=True)
    question_count = Column(Integer, nullable=False, default=0)
    completed_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    results = relationship("EvalRunResultDb", back_populates="run", cascade="all, delete-orphan")


class EvalRunResultDb(Base):
    __tablename__ = "eval_run_results"

    result_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("eval_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("eval_questions.question_id", ondelete="CASCADE"),
        nullable=False,
    )
    generated_answer = Column(Text, nullable=True)
    retrieved_chunk_ids = Column(JSONB, nullable=False, default=list)
    scores = Column(JSONB, nullable=False, default=dict)
    latency_ms = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    run = relationship("EvalRunDb", back_populates="results")
