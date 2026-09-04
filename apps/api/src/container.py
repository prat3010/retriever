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

from src.adapters.backup.cloud_backup_adapter import CloudBackupAdapter
from src.adapters.backup.cloud_restore_adapter import CloudRestoreAdapter
from src.adapters.broker.noop_event_publisher import NoOpEventPublisher
from src.adapters.cache.config_cache import RedisTenantConfigCache
from src.adapters.cognitive.anthropic_adapter import AnthropicLLMAdapter
from src.adapters.cognitive.brave_adapter import BraveSearchAdapter
from src.adapters.cognitive.context_compressor_adapter import (
    IntelligentContextCompressor,
)
from src.adapters.cognitive.corrective_retrieval_adapter import (
    LLMCorrectiveRetrievalAdapter,
)
from src.adapters.cognitive.dspy_compiler_adapter import DSPyCompilerAdapter
from src.adapters.cognitive.gateway_router import GatewayRouterAdapter
from src.adapters.cognitive.hf_embedding_adapter import HFEmbeddingAdapter
from src.adapters.cognitive.langgraph_orchestrator import LangGraphOrchestrator
from src.adapters.cognitive.local_reranker_adapter import LocalRerankerAdapter
from src.adapters.cognitive.ollama_embedding_adapter import OllamaEmbeddingAdapter
from src.adapters.cognitive.openai_adapter import OpenAILLMAdapter
from src.adapters.cognitive.query_intent_adapter import LLMQueryIntentAdapter
from src.adapters.cognitive.query_rewriter_adapter import LLMQueryRewriterAdapter
from src.adapters.cognitive.reranker_adapter import CohereRerankerAdapter
from src.adapters.cognitive.self_query_adapter import LLMSelfQueryAdapter
from src.adapters.cognitive.tavily_adapter import TavilySearchAdapter
from src.adapters.cognitive.tei_reranker_adapter import TeiRerankerAdapter
from src.adapters.cognitive.topic_clustering_adapter import TopicClusteringAdapter
from src.adapters.database.admin_repository import SqlAdminRepository
from src.adapters.database.agent_checkpoint_repository import (
    SqlAgentCheckpointRepository,
)
from src.adapters.database.audit_repository import SqlAuditLogRepository
from src.adapters.database.budget_repository import SqlBudgetRepository
from src.adapters.database.compiled_prompt_repository import (
    SqlCompiledPromptRepository,
)
from src.adapters.database.config_repository import SqlConfigRegistry
from src.adapters.database.document_repository import SqlDocumentRepository
from src.adapters.database.evaluation_repository import (
    SqlEvalDatasetRepository,
    SqlEvalRunRepository,
    SqlOnlineEvaluationRepository,
)
from src.adapters.database.feedback_repository import SqlFeedbackRepository
from src.adapters.database.graph_repository import PgGraphRepository
from src.adapters.database.identity_repository import SqlIdentityProvider
from src.adapters.database.inference_repository import (
    SqlChatSessionRepository,
    SqlInferenceLogWriter,
    SqlPromptTemplateRegistry,
)
from src.adapters.database.quota_repository import SqlQuotaRepository
from src.adapters.database.semantic_cache import PgSemanticCacheAdapter
from src.adapters.database.tenant_repository import SqlTenantRegistry
from src.adapters.database.user_repository import SqlUserRepository
from src.adapters.database.workflow_repository import SqlWorkflowRepository
from src.adapters.graph.neo4j_repository import Neo4jGraphRepository
from src.adapters.guardrails.llm_safety_guard import apply_llm_safety_guard
from src.adapters.guardrails.nemo_guardrails_adapter import NeMoGuardrailsAdapter
from src.adapters.ingestion.sync_ingestion_service import (
    ingest_file_sync,  # noqa: F401 — re-exported for routers
)
from src.adapters.ml.scikit_effort_regressor import ScikitEffortRegressor
from src.adapters.ml.scikit_persona_classifier import (
    ScikitLeadPropensityScorer,
    ScikitPersonaClusterer,
)
from src.adapters.notification.logging_adapter import LoggingNotificationAdapter
from src.adapters.sandbox.python_sandbox_adapter import (
    RestrictedPythonSandboxAdapter,
)
from src.adapters.security.encryption_adapter import Aes256FieldEncryptor
from src.adapters.storage.local_storage import LocalStorage
from src.adapters.storage.s3_storage import S3Storage
from src.adapters.telemetry.setup import get_metrics
from src.adapters.vector.keyword_repository import PgKeywordSearchAdapter
from src.adapters.vector.splade_sparse_adapter import SpladeSparseSearchAdapter
from src.adapters.vector.vector_repository import PgVectorSearchAdapter
from src.adapters.workflow.durable_workflow_adapter import DurableWorkflowAdapter
from src.config import InfraCapabilities, settings
from src.domain.abstractions.batteries import BatteryStatus
from src.domain.agentic.execution_engine import AgenticExecutionEngine
from src.domain.agentic.tool_registry import ToolRegistry
from src.domain.backup.backup_service import BackupService
from src.domain.batteries.battery_service import BatteryService
from src.domain.clustering.persona_service import PersonaIntelligenceService
from src.domain.config.config_service import ConfigurationService
from src.domain.consensus.reflection_loop import MultiAgentConsensusEngine
from src.domain.estimation.effort_estimation_service import EffortEstimationService
from src.domain.evaluation.evaluator import EvalRunService
from src.domain.guardrails.nemo_guardrail_service import NeMoGuardrailService
from src.domain.inference.citation_validator import CitationValidator
from src.domain.inference.orchestrator import InferenceOrchestrator
from src.domain.inference.prompt_builder import PromptBuilder
from src.domain.integrations.slack_service import SlackService
from src.domain.quota.quota_service import QuotaService
from src.domain.retrieval.corrective_retrieval_service import CorrectiveRetrievalService
from src.domain.retrieval.search_service import HybridSearchService
from src.domain.rlm.engine import RlmExecutionEngine
from src.domain.workflow.durable_engine import DurableWorkflowEngine


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
        self._cache["quota_service"] = QuotaService(repository=SqlQuotaRepository())
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
        gateway_router = GatewayRouterAdapter(
            openai_adapter=openai_adapter,
            anthropic_adapter=anthropic_adapter,
        )
        self._cache["gateway_router"] = gateway_router
        self._cache["llm_provider"] = gateway_router

        self._cache["embedder"] = (
            HFEmbeddingAdapter(
                api_key=os.environ.get("HF_API_KEY") or os.environ.get("HF_API_TOKEN") or "",
                model=os.environ.get("EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5"),
            )
            if os.environ.get("EMBEDDING_PROVIDER") == "hf"
            else OllamaEmbeddingAdapter(
                base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
                model=os.environ.get("EMBEDDING_MODEL", "nomic-embed-text"),
            )
        )

        llm = self._cache["llm_provider"]
        embedder = self._cache["embedder"]

        # --- Graph Repository ---
        pg_graph = PgGraphRepository()
        infra = InfraCapabilities.detect()
        if infra.neo4j_viable or getattr(settings, "GRAPH_ENGINE", "postgres") == "neo4j":
            self._cache["graph_repository"] = Neo4jGraphRepository(
                uri=getattr(settings, "NEO4J_URI", "bolt://localhost:7687"),
                user=getattr(settings, "NEO4J_USER", "neo4j"),
                password=getattr(settings, "NEO4J_PASSWORD", "password"),
                fallback_repo=pg_graph,
            )
        else:
            self._cache["graph_repository"] = pg_graph

        # --- Search ---
        if settings.COHERE_API_KEY:
            reranker_instance = CohereRerankerAdapter(api_key=settings.COHERE_API_KEY)
        elif getattr(settings, "TEI_RERANK_URL", None):
            reranker_instance = TeiRerankerAdapter(endpoint_url=settings.TEI_RERANK_URL)
        else:
            reranker_instance = LocalRerankerAdapter()

        keyword_search_instance = (
            SpladeSparseSearchAdapter()
            if getattr(settings, "SPARSE_SEARCH_PROVIDER", "bm25") == "splade"
            else PgKeywordSearchAdapter()
        )

        def web_search_factory(name: str, key: str) -> Any:
            if name == "brave":
                return BraveSearchAdapter(api_key=key)
            return TavilySearchAdapter(api_key=key)

        self._cache["search_service"] = HybridSearchService(
            vector_search=PgVectorSearchAdapter(),
            keyword_search=keyword_search_instance,
            embedder=embedder,
            reranker=reranker_instance,
            cache_provider=PgSemanticCacheAdapter(),
            web_search=TavilySearchAdapter(api_key=settings.TAVILY_API_KEY) if settings.TAVILY_API_KEY else None,
            brave_search=BraveSearchAdapter(api_key=settings.BRAVE_API_KEY) if settings.BRAVE_API_KEY else None,
            self_query=LLMSelfQueryAdapter(llm=llm),
            query_rewriter=LLMQueryRewriterAdapter(llm=llm),
            query_intent_classifier=LLMQueryIntentAdapter(llm=llm),
            web_search_factory=web_search_factory,
            graph_repository=self._cache["graph_repository"],
        )

        # --- Inference ---
        session_repo = SqlChatSessionRepository()
        template_registry = SqlPromptTemplateRegistry()
        compiled_prompt_repo = SqlCompiledPromptRepository()
        dspy_compiler = DSPyCompilerAdapter(llm_provider=llm)
        log_writer = SqlInferenceLogWriter()
        budget_repo = SqlBudgetRepository()

        self._cache["session_repo"] = session_repo
        self._cache["template_registry"] = template_registry
        self._cache["compiled_prompt_repo"] = compiled_prompt_repo
        self._cache["dspy_compiler"] = dspy_compiler
        self._cache["log_writer"] = log_writer
        self._cache["budget_repo"] = budget_repo
        self._cache["feedback_repo"] = SqlFeedbackRepository()

        self._cache["inference_orchestrator"] = InferenceOrchestrator(
            llm_provider=llm,
            prompt_builder=PromptBuilder(
                template_registry=template_registry,
                compiled_prompt_repo=compiled_prompt_repo,
            ),
            citation_validator=CitationValidator(),
            session_repo=session_repo,
            log_writer=log_writer,
            metrics_registry=get_metrics(),
            notification_provider=LoggingNotificationAdapter(),
            document_repository=self._cache["document_repository"],
            budget_repository=budget_repo,
        )

        self._cache["llm_safety_guard"] = apply_llm_safety_guard

        # --- Evaluation ---
        eval_dataset_repo = SqlEvalDatasetRepository()
        eval_run_repo = SqlEvalRunRepository()
        online_eval_repo = SqlOnlineEvaluationRepository()
        from src.domain.evaluation.online_evaluator import OnlineHallucinationEvaluator

        self._cache["eval_dataset_repo"] = eval_dataset_repo
        self._cache["eval_run_repo"] = eval_run_repo
        self._cache["online_eval_repo"] = online_eval_repo
        self._cache["online_evaluator"] = OnlineHallucinationEvaluator(repository=online_eval_repo)

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

        # --- Agentic Engine (Milestone 91 LangGraph & HITL) ---
        tool_reg = ToolRegistry()
        checkpointer = SqlAgentCheckpointRepository()
        orchestrator = LangGraphOrchestrator(
            llm_provider=llm,
            tool_registry=tool_reg,
            checkpointer=checkpointer,
        )
        self._cache["tool_registry"] = tool_reg
        self._cache["agent_checkpointer"] = checkpointer
        self._cache["agent_orchestrator"] = orchestrator
        self._cache["agentic_engine"] = AgenticExecutionEngine(
            graph_orchestrator=orchestrator,
            checkpointer=checkpointer,
            tool_registry=tool_reg,
        )

        # --- RLM Engine ---
        sandbox = RestrictedPythonSandboxAdapter()
        self._cache["python_sandbox"] = sandbox
        self._cache["rlm_engine"] = RlmExecutionEngine(
            llm_provider=llm,
            sandbox_provider=sandbox,
            search_service=self._cache["search_service"],
        )

        # --- Consensus Engine ---
        self._cache["consensus_engine"] = MultiAgentConsensusEngine(
            default_llm=llm,
            search_service=self._cache["search_service"],
        )

        # --- Security & Compression ---
        self._cache["context_compressor"] = IntelligentContextCompressor()
        self._cache["field_encryptor"] = Aes256FieldEncryptor(master_key=settings.KEY_ENCRYPTION_KEY)

        from src.adapters.database.compliance_repository import SqlComplianceRepository
        from src.domain.compliance.certificate_service import (
            ComplianceCertificateService,
        )
        from src.domain.compliance.pii_anonymizer import PiiAnonymizer
        from src.domain.compliance.purge_service import HardPurgeService
        from src.domain.compliance.retention_worker import RetentionWorker

        compliance_repo = SqlComplianceRepository()
        certificate_service = ComplianceCertificateService(signing_key=settings.SECRET_KEY)
        pii_anonymizer = PiiAnonymizer()
        hard_purge_service = HardPurgeService(
            compliance_repo=compliance_repo,
            graph_repository=self._cache["graph_repository"],
            storage_provider=self._cache["local_storage"],
            certificate_service=certificate_service,
        )
        retention_worker = RetentionWorker(
            purge_service=hard_purge_service,
            compliance_repo=compliance_repo,
        )

        self._cache["compliance_repo"] = compliance_repo
        self._cache["compliance_certificate_service"] = certificate_service
        self._cache["pii_anonymizer"] = pii_anonymizer
        self._cache["hard_purge_service"] = hard_purge_service
        self._cache["retention_worker"] = retention_worker

        # --- Commercial Payments & Billing ---
        from src.adapters.database.payment_repository import SqlPaymentRepository
        from src.domain.billing.payment_service import PaymentService

        payment_repo = SqlPaymentRepository()
        payment_service = PaymentService(
            payment_repository=payment_repo,
            tenant_registry=self._cache["tenant_registry"],
        )
        self._cache["payment_repo"] = payment_repo
        self._cache["payment_service"] = payment_service

        # --- Enterprise n8n & Workflow Automation ---
        from src.domain.workflow.n8n_dispatcher import N8nWebhookDispatcher

        n8n_dispatcher = N8nWebhookDispatcher()
        self._cache["n8n_dispatcher"] = n8n_dispatcher

        # --- Milestone 69: Contextual Header Generator ---
        from src.adapters.cognitive.contextual_header_adapter import (
            ContextualHeaderGeneratorAdapter,
        )

        contextual_header_generator = ContextualHeaderGeneratorAdapter(
            api_key=settings.OPENAI_API_KEY if hasattr(settings, "OPENAI_API_KEY") else "",
            base_url=settings.OPENAI_BASE_URL if hasattr(settings, "OPENAI_BASE_URL") else "",
        )
        self._cache["contextual_header_generator"] = contextual_header_generator

        # --- Milestone 70: ColBERT MaxSim Late-Interaction Reranker ---
        from src.adapters.cognitive.local_reranker_adapter import (
            ColBertMaxSimRerankerAdapter,
        )

        colbert_reranker = ColBertMaxSimRerankerAdapter()
        self._cache["colbert_reranker"] = colbert_reranker

        # --- Milestone 81: HDBSCAN Topic Clustering & Knowledge Gap Detection ---
        self._cache["topic_clusterer"] = TopicClusteringAdapter()

        # --- Milestone 82: 2D/3D Embedding Space Projection ---
        from src.adapters.cognitive.embedding_projection_adapter import (
            EmbeddingProjectionAdapter,
        )

        self._cache["embedding_projector"] = EmbeddingProjectionAdapter()

        # --- Milestone 83: Telemetry Anomaly Sentinel & Quota Abuse Guard ---
        from src.adapters.cognitive.anomaly_detector_adapter import (
            AnomalyDetectorAdapter,
        )
        from src.adapters.database.anomaly_repository import SqlAnomalyRepository
        from src.domain.telemetry.alert_service import AlertService
        from src.domain.telemetry.anomaly_sentinel_service import AnomalySentinelService

        anomaly_detector = AnomalyDetectorAdapter()
        anomaly_repo = SqlAnomalyRepository()
        alert_svc = AlertService()
        self._cache["anomaly_detector"] = anomaly_detector
        self._cache["anomaly_repository"] = anomaly_repo
        self._cache["alert_service"] = alert_svc
        self._cache["anomaly_sentinel_service"] = AnomalySentinelService(
            detector=anomaly_detector,
            repository=anomaly_repo,
            alert_service=alert_svc,
            inference_repo=log_writer,
        )

        effort_regressor = ScikitEffortRegressor()
        self._cache["effort_regressor"] = effort_regressor
        self._cache["effort_estimation_service"] = EffortEstimationService(effort_regressor)

        persona_clusterer = ScikitPersonaClusterer()
        lead_scorer = ScikitLeadPropensityScorer()
        self._cache["persona_clusterer"] = persona_clusterer
        self._cache["lead_scorer"] = lead_scorer
        self._cache["persona_intelligence_service"] = PersonaIntelligenceService(
            persona_classifier=persona_clusterer,
            lead_scorer=lead_scorer,
        )

        def _resolve_battery_statuses() -> dict[str, BatteryStatus]:
            statuses: dict[str, BatteryStatus] = {}
            infra_cap = InfraCapabilities.detect()
            if not infra_cap.neo4j_viable:
                statuses["neo4j_cypher_graph"] = BatteryStatus.STANDBY
            else:
                repo = self._cache.get("graph_repository")
                if repo and hasattr(repo, "_driver") and repo._driver is not None:
                    statuses["neo4j_cypher_graph"] = BatteryStatus.ACTIVE
                elif getattr(settings, "GRAPH_ENGINE", "postgres") == "neo4j":
                    statuses["neo4j_cypher_graph"] = BatteryStatus.ACTIVE
                else:
                    statuses["neo4j_cypher_graph"] = BatteryStatus.STANDBY
            return statuses

        self._cache["battery_service"] = BatteryService(status_resolver=_resolve_battery_statuses)

        cloud_backup = CloudBackupAdapter(storage=self._cache.get("s3_storage"))
        cloud_restore = CloudRestoreAdapter(storage=self._cache.get("s3_storage"))
        self._cache["backup_service"] = BackupService(
            backup_adapter=cloud_backup,
            restore_adapter=cloud_restore,
        )

        # --- Milestone 89: Geo-Distributed Edge Router & Read-Replicas ---
        from src.adapters.database.read_replica_adapter import ReadReplicaAdapter
        from src.domain.abstractions.edge_router import RegionCode
        from src.domain.routing.edge_router_service import EdgeRouterService

        configured_regions = {RegionCode(settings.PRIMARY_REGION)}
        if settings.REPLICA_US_EAST_DATABASE_URL:
            configured_regions.add(RegionCode.US_EAST)
        if settings.REPLICA_EU_CENTRAL_DATABASE_URL:
            configured_regions.add(RegionCode.EU_CENTRAL)
        if settings.REPLICA_AP_SOUTH_DATABASE_URL:
            configured_regions.add(RegionCode.AP_SOUTH)

        edge_router = EdgeRouterService(
            configured_regions=configured_regions,
            primary_region=RegionCode(settings.PRIMARY_REGION),
        )
        replica_adapter = ReadReplicaAdapter(
            router_service=edge_router,
        )
        self._cache["edge_router_service"] = edge_router
        self._cache["read_replica_adapter"] = replica_adapter
        self._cache["slack_service"] = SlackService()

        nemo_adapter = NeMoGuardrailsAdapter()
        self._cache["nemo_guardrails_adapter"] = nemo_adapter
        self._cache["nemo_guardrail_service"] = NeMoGuardrailService(adapter=nemo_adapter)

        # --- Milestone 95: Durable Asynchronous Execution & Background AI Workflow Engine ---
        wf_repo = SqlWorkflowRepository()
        dur_engine = DurableWorkflowEngine()
        dur_adapter = DurableWorkflowAdapter(
            repository=wf_repo,
            engine=dur_engine,
        )
        self._cache["workflow_repository"] = wf_repo
        self._cache["durable_engine"] = dur_engine
        self._cache["durable_workflow_adapter"] = dur_adapter



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
llm_safety_guard = container.llm_safety_guard
graph_repository = container.graph_repository

online_eval_repo = container.online_eval_repo
online_evaluator = container.online_evaluator
quota_service = container.quota_service
pii_anonymizer = container.pii_anonymizer
hard_purge_service = container.hard_purge_service
retention_worker = container.retention_worker
payment_repo = container.payment_repo
payment_service = container.payment_service
n8n_dispatcher = container.n8n_dispatcher
contextual_header_generator = container.contextual_header_generator
colbert_reranker = container.colbert_reranker
topic_clusterer = container.topic_clusterer
embedding_projector = container.embedding_projector
anomaly_detector = container.anomaly_detector
anomaly_repository = container.anomaly_repository
alert_service = container.alert_service
anomaly_sentinel_service = container.anomaly_sentinel_service
effort_estimation_service = container.effort_estimation_service
persona_intelligence_service = container.persona_intelligence_service
battery_service = container.battery_service
backup_service = container.backup_service
compliance_certificate_service = container.compliance_certificate_service
edge_router_service = container.edge_router_service
read_replica_adapter = container.read_replica_adapter
slack_service = container.slack_service
compiled_prompt_repo = container.compiled_prompt_repo
dspy_compiler = container.dspy_compiler
gateway_router = container.gateway_router
budget_repo = container.budget_repo
nemo_guardrails_adapter = container.nemo_guardrails_adapter
nemo_guardrail_service = container.nemo_guardrail_service
workflow_repository = container.workflow_repository
durable_engine = container.durable_engine
durable_workflow_adapter = container.durable_workflow_adapter

