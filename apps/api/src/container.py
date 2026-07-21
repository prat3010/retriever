import os

from src.adapters.cache.config_cache import RedisTenantConfigCache
from src.adapters.cognitive.anthropic_adapter import AnthropicLLMAdapter
from src.adapters.cognitive.brave_adapter import BraveSearchAdapter
from src.adapters.cognitive.hf_embedding_adapter import HFEmbeddingAdapter
from src.adapters.cognitive.ollama_embedding_adapter import OllamaEmbeddingAdapter
from src.adapters.cognitive.openai_adapter import OpenAILLMAdapter
from src.adapters.cognitive.query_intent_adapter import LLMQueryIntentAdapter
from src.adapters.cognitive.query_rewriter_adapter import LLMQueryRewriterAdapter
from src.adapters.cognitive.reranker_adapter import CohereRerankerAdapter
from src.adapters.cognitive.routing_provider import RoutingLLMProvider
from src.adapters.cognitive.self_query_adapter import LLMSelfQueryAdapter
from src.adapters.cognitive.tavily_adapter import TavilySearchAdapter
from src.adapters.cognitive.corrective_retrieval_adapter import LLMCorrectiveRetrievalAdapter
from src.adapters.database.audit_repository import SqlAuditLogRepository
from src.adapters.database.config_repository import SqlConfigRegistry
from src.adapters.database.document_repository import SqlDocumentRepository
from src.adapters.database.evaluation_repository import SqlEvalDatasetRepository, SqlEvalRunRepository
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
from src.domain.retrieval.experiment_service import apply_overrides, assign_variant
from src.domain.retrieval.search_service import HybridSearchService

# --- Repositories ---
audit_logger = SqlAuditLogRepository()
tenant_registry = SqlTenantRegistry()
identity_provider = SqlIdentityProvider()
user_repository = SqlUserRepository()
document_repository = SqlDocumentRepository()
config_service = ConfigurationService(
    registry=SqlConfigRegistry(),
    cache=RedisTenantConfigCache(),
    env_secrets=dict(os.environ),
)

# --- Storage ---
if settings.STORAGE_PROVIDER == "s3":
    local_storage = S3Storage(
        bucket_name=settings.STORAGE_BUCKET,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
        endpoint_url=settings.S3_ENDPOINT_URL,
    )
else:
    local_storage = LocalStorage(
        fallback_url=settings.REMOTE_STORAGE_FALLBACK_URL,
        internal_key=settings.INTERNAL_API_KEY,
        hmac_key=settings.STORAGE_HMAC_KEY,
    )

# --- LLM / Embedding ---
llm_provider = RoutingLLMProvider(
    openai_adapter=OpenAILLMAdapter(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    ),
    anthropic_adapter=AnthropicLLMAdapter(
        api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    ),
)

embedder = (
    OllamaEmbeddingAdapter(
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
    )
    if os.environ.get("EMBEDDING_PROVIDER") == "ollama"
    else HFEmbeddingAdapter(
        api_key=os.environ.get("HF_API_KEY") or os.environ.get("HF_API_TOKEN") or "",
        model=os.environ.get("EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5"),
    )
)

# --- Search ---
search_service = HybridSearchService(
    vector_search=PgVectorSearchAdapter(),
    keyword_search=PgKeywordSearchAdapter(),
    embedder=embedder,
    reranker=CohereRerankerAdapter(api_key=settings.COHERE_API_KEY),
    cache_provider=PgSemanticCacheAdapter(),
    web_search=TavilySearchAdapter(api_key=settings.TAVILY_API_KEY) if settings.TAVILY_API_KEY else None,
    brave_search=BraveSearchAdapter(api_key=settings.BRAVE_API_KEY) if settings.BRAVE_API_KEY else None,
    self_query=LLMSelfQueryAdapter(llm=llm_provider),
    query_rewriter=LLMQueryRewriterAdapter(llm=llm_provider),
    query_intent_classifier=LLMQueryIntentAdapter(llm=llm_provider),
)

# --- Inference ---
session_repo = SqlChatSessionRepository()
template_registry = SqlPromptTemplateRegistry()
log_writer = SqlInferenceLogWriter()
feedback_repo = SqlFeedbackRepository()

inference_orchestrator = InferenceOrchestrator(
    llm_provider=llm_provider,
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
eval_service = EvalRunService(
    eval_dataset_repo=eval_dataset_repo,
    eval_run_repo=eval_run_repo,
    search_service=search_service,
    inference_orchestrator=inference_orchestrator,
)

# --- Corrective Retrieval ---
corrective_provider = LLMCorrectiveRetrievalAdapter(llm=llm_provider)
corrective_service = CorrectiveRetrievalService(
    search_service=search_service,
    orchestrator=inference_orchestrator,
    corrective_provider=corrective_provider,
)
