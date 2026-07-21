import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

try:
    from src.adapters.broker.celery_publisher import celery_app
except Exception:
    celery_app = None

try:
    from src.adapters.broker.rabbitmq_event_publisher import (
        RabbitMQEventPublisher,
    )
    _event_publisher_available = True
except Exception:
    _event_publisher_available = False

from src.adapters.broker.noop_event_publisher import NoOpEventPublisher
from src.adapters.cache.config_cache import RedisTenantConfigCache
from src.adapters.cognitive.anthropic_adapter import AnthropicLLMAdapter
from src.adapters.cognitive.brave_adapter import BraveSearchAdapter
from src.adapters.cognitive.corrective_retrieval_adapter import (
    LLMCorrectiveRetrievalAdapter,
)
from src.adapters.cognitive.hf_embedding_adapter import HFEmbeddingAdapter
from src.adapters.cognitive.ollama_embedding_adapter import OllamaEmbeddingAdapter
from src.adapters.cognitive.openai_adapter import OpenAILLMAdapter
from src.adapters.cognitive.query_intent_adapter import LLMQueryIntentAdapter
from src.adapters.cognitive.query_rewriter_adapter import LLMQueryRewriterAdapter
from src.adapters.cognitive.reranker_adapter import CohereRerankerAdapter
from src.adapters.cognitive.routing_provider import RoutingLLMProvider
from src.adapters.cognitive.self_query_adapter import LLMSelfQueryAdapter
from src.adapters.cognitive.tavily_adapter import TavilySearchAdapter
from src.adapters.database.admin_repository import SqlAdminRepository
from src.adapters.database.audit_repository import SqlAuditLogRepository
from src.adapters.database.config_repository import SqlConfigRegistry
from src.adapters.database.document_repository import SqlDocumentRepository
from src.adapters.database.evaluation_repository import (
    SqlEvalDatasetRepository,
    SqlEvalRunRepository,
)
from src.adapters.database.feedback_repository import SqlFeedbackRepository
from src.adapters.database.identity_repository import SqlIdentityProvider
from src.adapters.database.inference_repository import (
    SqlChatSessionRepository,
    SqlInferenceLogWriter,
    SqlPromptTemplateRegistry,
)
from src.adapters.database.semantic_cache import PgSemanticCacheAdapter
from src.adapters.database.tenant_repository import SqlTenantRegistry
from src.adapters.database.user_repository import SqlUserRepository
from src.adapters.ingestion.sync_ingestion_service import (
    ingest_file_sync,  # noqa: F401 — re-exported for routers
)
from src.adapters.notification.logging_adapter import LoggingNotificationAdapter
from src.adapters.storage.local_storage import LocalStorage
from src.adapters.storage.s3_storage import S3Storage
from src.adapters.telemetry.setup import get_metrics
from src.adapters.vector.keyword_repository import PgKeywordSearchAdapter
from src.adapters.vector.vector_repository import PgVectorSearchAdapter
from src.config import settings
from src.domain.config.config_service import ConfigurationService
from src.domain.evaluation.evaluator import EvalRunService
from src.domain.inference.citation_validator import CitationValidator
from src.domain.inference.orchestrator import InferenceOrchestrator
from src.domain.inference.prompt_builder import PromptBuilder
from src.domain.retrieval.corrective_retrieval_service import CorrectiveRetrievalService
from src.domain.retrieval.search_service import HybridSearchService


class Container:
    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}
        self._build()

    def _build(self) -> None:
        # --- Repositories ---
        self._cache["admin_repository"] = SqlAdminRepository()
        self._cache["audit_logger"] = SqlAuditLogRepository()
        self._cache["tenant_registry"] = SqlTenantRegistry()
        self._cache["identity_provider"] = SqlIdentityProvider()
        self._cache["user_repository"] = SqlUserRepository()
        self._cache["document_repository"] = SqlDocumentRepository()
        config_registry = SqlConfigRegistry()
        self._cache["config_service"] = ConfigurationService(
            registry=config_registry,
            cache=RedisTenantConfigCache(),
            env_secrets=dict(os.environ),
        )

        # --- Storage ---
        if settings.STORAGE_PROVIDER == "s3":
            self._cache["local_storage"] = S3Storage(
                bucket_name=settings.STORAGE_BUCKET,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
                endpoint_url=settings.S3_ENDPOINT_URL,
            )
        else:
            self._cache["local_storage"] = LocalStorage(
                fallback_url=settings.REMOTE_STORAGE_FALLBACK_URL,
                internal_key=settings.INTERNAL_API_KEY,
                hmac_key=settings.STORAGE_HMAC_KEY,
            )

        # --- LLM / Embedding ---
        openai_adapter = OpenAILLMAdapter(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        anthropic_adapter = AnthropicLLMAdapter(
            api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        )
        self._cache["llm_provider"] = RoutingLLMProvider(
            openai_adapter=openai_adapter,
            anthropic_adapter=anthropic_adapter,
        )

        self._cache["embedder"] = (
            OllamaEmbeddingAdapter(
                base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            )
            if os.environ.get("EMBEDDING_PROVIDER") == "ollama"
            else HFEmbeddingAdapter(
                api_key=os.environ.get("HF_API_KEY") or os.environ.get("HF_API_TOKEN") or "",
                model=os.environ.get("EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5"),
            )
        )

        llm = self._cache["llm_provider"]
        embedder = self._cache["embedder"]

        # --- Search ---
        self._cache["search_service"] = HybridSearchService(
            vector_search=PgVectorSearchAdapter(),
            keyword_search=PgKeywordSearchAdapter(),
            embedder=embedder,
            reranker=CohereRerankerAdapter(api_key=settings.COHERE_API_KEY),
            cache_provider=PgSemanticCacheAdapter(),
            web_search=TavilySearchAdapter(api_key=settings.TAVILY_API_KEY) if settings.TAVILY_API_KEY else None,
            brave_search=BraveSearchAdapter(api_key=settings.BRAVE_API_KEY) if settings.BRAVE_API_KEY else None,
            self_query=LLMSelfQueryAdapter(llm=llm),
            query_rewriter=LLMQueryRewriterAdapter(llm=llm),
            query_intent_classifier=LLMQueryIntentAdapter(llm=llm),
        )

        # --- Inference ---
        session_repo = SqlChatSessionRepository()
        template_registry = SqlPromptTemplateRegistry()
        log_writer = SqlInferenceLogWriter()

        self._cache["session_repo"] = session_repo
        self._cache["template_registry"] = template_registry
        self._cache["log_writer"] = log_writer
        self._cache["feedback_repo"] = SqlFeedbackRepository()

        self._cache["inference_orchestrator"] = InferenceOrchestrator(
            llm_provider=llm,
            prompt_builder=PromptBuilder(template_registry=template_registry),
            citation_validator=CitationValidator(),
            session_repo=session_repo,
            log_writer=log_writer,
            metrics_registry=get_metrics(),
            notification_provider=LoggingNotificationAdapter(),
        )

        # --- Evaluation ---
        eval_dataset_repo = SqlEvalDatasetRepository()
        eval_run_repo = SqlEvalRunRepository()
        self._cache["eval_dataset_repo"] = eval_dataset_repo
        self._cache["eval_run_repo"] = eval_run_repo
        self._cache["eval_service"] = EvalRunService(
            eval_dataset_repo=eval_dataset_repo,
            eval_run_repo=eval_run_repo,
            search_service=self._cache["search_service"],
            inference_orchestrator=self._cache["inference_orchestrator"],
        )

        # --- Corrective Retrieval ---
        corrective_provider = LLMCorrectiveRetrievalAdapter(llm=llm)
        self._cache["corrective_provider"] = corrective_provider
        self._cache["corrective_service"] = CorrectiveRetrievalService(
            search_service=self._cache["search_service"],
            orchestrator=self._cache["inference_orchestrator"],
            corrective_provider=corrective_provider,
        )

        # --- Event Bus ---
        if _event_publisher_available and settings.RABBITMQ_URL:
            self._cache["event_publisher"] = RabbitMQEventPublisher(
                amqp_url=settings.RABBITMQ_URL,
            )
        else:
            self._cache["event_publisher"] = NoOpEventPublisher()

    def reset(self) -> None:
        self._cache.clear()
        self._build()

    @contextmanager
    def override(self, name: str, instance: Any) -> Iterator[None]:
        old = self._cache.get(name)
        self._cache[name] = instance
        try:
            yield
        finally:
            if old is not None:
                self._cache[name] = old
            else:
                self._cache.pop(name, None)

    def __getattr__(self, name: str) -> Any:
        if name in self._cache:
            return self._cache[name]
        raise AttributeError(f"Container has no attribute {name!r}")


container = Container()

admin_repository = container.admin_repository
audit_logger = container.audit_logger
config_service = container.config_service
document_repository = container.document_repository
embedder = container.embedder
eval_dataset_repo = container.eval_dataset_repo
eval_run_repo = container.eval_run_repo
eval_service = container.eval_service
feedback_repo = container.feedback_repo
identity_provider = container.identity_provider
inference_orchestrator = container.inference_orchestrator
llm_provider = container.llm_provider
local_storage = container.local_storage
log_writer = container.log_writer
search_service = container.search_service
session_repo = container.session_repo
template_registry = container.template_registry
tenant_registry = container.tenant_registry
user_repository = container.user_repository

corrective_provider = container.corrective_provider
corrective_service = container.corrective_service

event_publisher = container.event_publisher
