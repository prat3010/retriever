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
from sqlalchemy.orm import DeclarativeBase, relationship, synonym


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
    config = relationship(
        "TenantConfigDb",
        back_populates="tenant",
        uselist=False,
        cascade="all, delete-orphan",
    )
    api_keys = relationship("ApiKeyDb", back_populates="tenant", cascade="all, delete")
    sessions = relationship(
        "ChatSessionDb", back_populates="tenant", cascade="all, delete"
    )
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
    hybrid_alpha = Column(Float, nullable=False, default=0.7)
    active_lora_adapter = Column(String(255), nullable=True)
    reranker_engine = Column(String(50), nullable=False, default="cohere")

    # Relationships
    tenant = relationship("TenantDb", back_populates="config")


class TenantLoraAdapterDb(Base):
    __tablename__ = "tenant_lora_adapters"

    adapter_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    domain_tag = Column(String(100), nullable=False, default="general")
    rank = Column(Integer, nullable=False, default=8)
    loss_score = Column(Float, nullable=True)
    weights_json = Column(JSONB, nullable=False, default=dict)
    adapter_type = Column(String(50), nullable=False, default="embedding")
    base_model = Column(String(255), nullable=True)
    artifact_uri = Column(String(500), nullable=True)
    alpha = Column(Float, nullable=True, default=16.0)
    target_modules = Column(JSONB, nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        Index("ix_tenant_lora_adapters_tenant_tag", "tenant_id", "domain_tag"),
    )


class CustomPluginDb(Base):
    __tablename__ = "custom_plugins"

    plugin_id = Column(String(100), primary_key=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(32), nullable=False, default="1.0.0")
    persona = Column(String(32), nullable=False, default="fde_engineer")
    manifest = Column(JSONB, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


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
    sessions = relationship(
        "ChatSessionDb", back_populates="user", cascade="all, delete"
    )


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
    collection_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)
    storage_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")
    tags = Column(ARRAY(String), nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    is_deleted = Column(Boolean, nullable=False, default=False)

    # Relationships
    chunks = relationship(
        "DocumentChunkDb", back_populates="document", cascade="all, delete-orphan"
    )


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
    collection_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    parent_chunk_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.chunk_id", ondelete="SET NULL"),
        nullable=True,
    )
    meta_data = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        Index("ix_document_chunks_meta_data", meta_data, postgresql_using="gin"),
        Index(
            "idx_document_chunks_tenant_doc_idx", tenant_id, document_id, chunk_index
        ),
        Index("idx_document_chunks_tenant_coll", tenant_id, collection_id),
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
    collection_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    embedding = Column(Vector(768), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class VectorRecord1024Db(Base):
    __tablename__ = "vector_records_1024"

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
    collection_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    embedding = Column(Vector(1024), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class VectorRecord1536Db(Base):
    __tablename__ = "vector_records_1536"

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
    collection_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    embedding = Column(Vector(1536), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class VectorRecord3072Db(Base):
    __tablename__ = "vector_records_3072"

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
    collection_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    embedding = Column(Vector(3072), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


def get_vector_table_name(dimension: int) -> str:
    """Return matching vector partition table name based on embedding dimension."""
    if dimension == 1024:
        return "vector_records_1024"
    if dimension == 1536:
        return "vector_records_1536"
    if dimension == 3072:
        return "vector_records_3072"
    return "vector_records"


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
        UniqueConstraint(
            "session_id", "tenant_id", name="uq_chat_sessions_session_tenant"
        ),
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
        "ChatMessageDb",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessageDb.created_at",
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
    role = Column(String(50), nullable=True)
    key_id = Column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.key_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Column synonyms for query backward compatibility
    prompt_tokens = synonym("input_tokens")
    completion_tokens = synonym("output_tokens")


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

    questions = relationship(
        "EvalQuestionDb", back_populates="dataset", cascade="all, delete-orphan"
    )


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

    results = relationship(
        "EvalRunResultDb", back_populates="run", cascade="all, delete-orphan"
    )


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


class GraphTripleDb(Base):
    __tablename__ = "graph_triples"

    triple_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject = Column(String(255), nullable=False, index=True)
    predicate = Column(String(255), nullable=False, index=True)
    object = Column(String(255), nullable=False, index=True)
    chunk_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.chunk_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    confidence = Column(Float, nullable=False, default=1.0)
    meta_data = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class OnlineEvaluationDb(Base):
    __tablename__ = "online_evaluations"

    eval_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id = Column(String(255), nullable=True)
    message_id = Column(String(255), nullable=True)
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    faithfulness = Column(Float, nullable=False, default=1.0)
    context_precision = Column(Float, nullable=False, default=1.0)
    hallucination_index = Column(Float, nullable=False, default=0.0)
    is_alert = Column(Boolean, nullable=False, default=False)
    claims = Column(JSONB, nullable=True, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class PaymentTransactionDb(Base):
    __tablename__ = "payment_transactions"

    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = Column(String(50), nullable=False)
    event_type = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False, default=0.0)
    currency = Column(String(10), nullable=False, default="INR")
    status = Column(String(50), nullable=False, default="completed")
    external_reference = Column(String(255), nullable=True)
    meta_data = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        Index(
            "uq_payment_transactions_provider_external_reference",
            provider,
            external_reference,
            unique=True,
            postgresql_where=external_reference.is_not(None),
        ),
    )


class TelemetryAnomalyDb(Base):
    __tablename__ = "telemetry_anomalies"

    anomaly_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_id = Column(String(255), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, default="api_key")
    key_id = Column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.key_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    risk_level = Column(String(50), nullable=False, default="LOW")
    anomaly_score = Column(Float, nullable=False, default=0.0)
    algorithm_used = Column(String(100), nullable=False, default="isolation_forest")
    features = Column(JSONB, nullable=False, default=dict)
    contributing_factors = Column(JSONB, nullable=False, default=list)
    is_quarantined = Column(Boolean, nullable=False, default=False)
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_telemetry_anomalies_tenant_created", "tenant_id", "created_at"),
        Index("ix_telemetry_anomalies_risk_status", "risk_level", "status"),
    )


class AgentCheckpointDb(Base):
    """Persisted checkpoint for stateful LangGraph agentic threads."""

    __tablename__ = "agent_checkpoints"

    checkpoint_id = Column(String(128), primary_key=True)
    thread_id = Column(String(128), nullable=False, index=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_name = Column(String(64), nullable=False)
    step_index = Column(Integer, nullable=False, default=0)
    state_snapshot = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        Index("ix_agent_checkpoints_tenant_thread", "tenant_id", "thread_id"),
        Index("ix_agent_checkpoints_thread_step", "thread_id", "step_index"),
    )


class CompiledPromptProgramDb(Base):
    """Persisted compiled DSPy prompt programs with metric evaluation scores and few-shot exemplars."""

    __tablename__ = "compiled_prompt_programs"

    program_id = Column(String(128), primary_key=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(128), nullable=False, default="rag_cot_optimized")
    signature_name = Column(String(128), nullable=False, default="RAGAnswerSignature")
    optimizer = Column(String(64), nullable=False, default="BootstrapFewShot")
    dataset_id = Column(String(128), nullable=True)
    baseline_score = Column(Float, nullable=False, default=0.0)
    compiled_score = Column(Float, nullable=False, default=0.0)
    improvement_pct = Column(Float, nullable=False, default=0.0)
    metric_name = Column(String(64), nullable=False, default="faithfulness_and_relevancy")
    compiled_instruction = Column(Text, nullable=False, default="")
    few_shot_demos = Column(JSONB, nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        Index("ix_compiled_prompts_tenant", "tenant_id"),
        Index("ix_compiled_prompts_tenant_active", "tenant_id", "is_active"),
    )


class WorkflowExecutionDb(Base):
    """Persisted state, status, and metadata for durable asynchronous workflow executions."""

    __tablename__ = "workflow_executions"

    execution_id = Column(String(128), primary_key=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workflow_name = Column(String(128), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="queued", index=True)
    trigger_event = Column(String(128), nullable=True)
    idempotency_key = Column(String(128), nullable=True, index=True)
    input_payload = Column(JSONB, nullable=False, default=dict)
    output_payload = Column(JSONB, nullable=False, default=dict)
    total_steps = Column(Integer, nullable=False, default=0)
    completed_steps = Column(Integer, nullable=False, default=0)
    current_step_name = Column(String(128), nullable=True)
    error_message = Column(Text, nullable=True)
    webhook_url = Column(String(512), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        Index("ix_workflow_executions_tenant_status", "tenant_id", "status"),
        Index("ix_workflow_executions_tenant_name", "tenant_id", "workflow_name"),
        Index("ix_workflow_executions_tenant_idemp", "tenant_id", "idempotency_key"),
    )


class WorkflowStepCheckpointDb(Base):
    """Persisted step-level checkpoint and memoized output for zero-loss recovery."""

    __tablename__ = "workflow_step_checkpoints"

    step_id = Column(String(256), primary_key=True)  # {execution_id}:{step_name}
    execution_id = Column(
        String(128),
        ForeignKey("workflow_executions.execution_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_name = Column(String(128), nullable=False)
    step_index = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="pending")
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    memoized_output = Column(JSONB, nullable=False, default=dict)
    error_details = Column(Text, nullable=True)
    execution_time_ms = Column(Float, nullable=False, default=0.0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_workflow_steps_exec_step", "execution_id", "step_name"),
        Index("ix_workflow_steps_tenant_status", "tenant_id", "status"),
    )


class EdgeNodeDb(Base):
    """Registered edge node device metadata for Sovereign Edge distribution (M98)."""

    __tablename__ = "edge_nodes"

    node_id = Column(String(128), primary_key=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_name = Column(String(255), nullable=False)
    platform = Column(String(64), nullable=False, default="darwin_arm64")
    last_synced_seq = Column(Integer, nullable=False, default=0)
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    status = Column(String(32), nullable=False, default="online")
    meta_data = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        Index("ix_edge_nodes_tenant_status", "tenant_id", "status"),
    )


class EdgeSyncCheckpointDb(Base):
    """Persisted synchronization checkpoint sequence and integrity manifest (M98)."""

    __tablename__ = "edge_sync_checkpoints"

    checkpoint_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_id = Column(String(128), nullable=False, index=True)
    sequence_num = Column(Integer, nullable=False, default=0)
    checksum_sha256 = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        Index("ix_edge_sync_checkpoints_tenant_seq", "tenant_id", "sequence_num"),
    )


class MultiCloudClusterNodeDb(Base):
    """Registered multi-cloud cluster region nodes and health telemetry (M99)."""

    __tablename__ = "multicloud_cluster_nodes"

    node_id = Column(String(128), primary_key=True)
    cloud_provider = Column(String(64), nullable=False, default="oracle")
    region = Column(String(64), nullable=False, index=True)
    endpoint_url = Column(String(512), nullable=False)
    role = Column(String(32), nullable=False, default="standby_replica")
    is_voting_member = Column(Boolean, nullable=False, default=True)
    priority_weight = Column(Integer, nullable=False, default=100)
    latency_ms = Column(Float, nullable=False, default=12.0)
    consecutive_failures = Column(Integer, nullable=False, default=0)
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    meta_data = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        Index("ix_multicloud_nodes_region_role", "region", "role"),
    )


class MultiCloudFailoverEventDb(Base):
    """Immutable audit ledger of multi-cloud quorum leader transitions (M99)."""

    __tablename__ = "multicloud_failover_events"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    old_leader = Column(String(64), nullable=False)
    new_leader = Column(String(64), nullable=False)
    generation_term = Column(Integer, nullable=False)
    trigger_type = Column(String(64), nullable=False, default="manual_operator_override")
    reason = Column(Text, nullable=False)
    quorum_votes_acquired = Column(Integer, nullable=False)
    total_voting_nodes = Column(Integer, nullable=False)
    duration_ms = Column(Float, nullable=False, default=0.0)
    operator_id = Column(String(128), nullable=False, default="admin")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        Index("ix_multicloud_events_term", "generation_term", "created_at"),
    )


class VoiceSessionDb(Base):
    """Sovereign edge WebRTC voice session entity (M100)."""

    __tablename__ = "voice_sessions"

    session_id = Column(String(128), primary_key=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(128), nullable=False, default="usr_anonymous")
    state = Column(String(32), nullable=False, default="initializing")
    sample_rate_hz = Column(Integer, nullable=False, default=16000)
    channels = Column(Integer, nullable=False, default=1)
    vad_sensitivity = Column(Float, nullable=False, default=0.65)
    selected_voice = Column(String(64), nullable=False, default="neural_natural")
    audio_codec = Column(String(32), nullable=False, default="pcm16")
    total_turns = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    connected_at = Column(DateTime(timezone=True), nullable=True)
    last_ping_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    meta_data = Column(JSONB, nullable=False, default=dict)

    tenant = relationship("TenantDb")

    __table_args__ = (
        Index("ix_voice_sessions_tenant_state", "tenant_id", "state"),
    )


class VoiceTurnDb(Base):
    """Conversational voice turn with latency telemetry (M100)."""

    __tablename__ = "voice_turns"

    turn_id = Column(String(128), primary_key=True)
    session_id = Column(
        String(128),
        ForeignKey("voice_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_transcript = Column(Text, nullable=False)
    agent_response_text = Column(Text, nullable=False)
    time_to_transcribe_ms = Column(Float, nullable=False, default=0.0)
    time_to_first_audio_byte_ms = Column(Float, nullable=False, default=0.0)
    total_turn_duration_ms = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    session = relationship("VoiceSessionDb")
    tenant = relationship("TenantDb")

    __table_args__ = (
        Index("ix_voice_turns_session_created", "session_id", "created_at"),
    )







