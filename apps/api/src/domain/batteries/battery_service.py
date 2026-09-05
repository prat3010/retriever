from collections.abc import Callable

from src.domain.abstractions.batteries import (
    BatteryCategory,
    BatteryStatus,
    PlatformBatteriesResponse,
    PlatformBatteryDTO,
)


class BatteryService:
    """Pure domain service managing the platform batteries inventory."""

    def __init__(
        self,
        status_resolver: Callable[[], dict[str, BatteryStatus]] | None = None,
        custom_batteries_provider: Callable[[], list[PlatformBatteryDTO]] | None = None,
    ) -> None:
        self._status_resolver = status_resolver
        self._custom_batteries_provider = custom_batteries_provider
        self._batteries = self._build_catalog()

    def _build_catalog(self) -> list[PlatformBatteryDTO]:
        return [
            PlatformBatteryDTO(
                id="bm25_sparse_retrieval",
                name="Sublinear BM25 Keyword Search",
                category=BatteryCategory.RETRIEVAL,
                status=BatteryStatus.ACTIVE,
                algorithm_foundation="Okapi BM25 with Inverted Term Index (k1=1.5, b=0.75)",
                milestone="M12 (v0.12.0)",
                latency_profile="~3ms",
                description="Sublinear term frequency keyword index for high-precision exact code, error message, and identifier retrieval.",
                active_parameters={"k1": 1.5, "b": 0.75, "min_term_length": 2},
                health_check_endpoint="/v1/search/bm25",
            ),
            PlatformBatteryDTO(
                id="pgvector_hnsw_dense",
                name="pgvector HNSW Dense Embeddings",
                category=BatteryCategory.RETRIEVAL,
                status=BatteryStatus.ACTIVE,
                algorithm_foundation="Hierarchical Navigable Small World (HNSW) Graphs on PostgreSQL 16",
                milestone="M1 (v0.1.0)",
                latency_profile="~8ms",
                description="High-dimensional cosine distance approximate nearest neighbor vector search with strict PostgreSQL RLS tenant isolation.",
                active_parameters={"distance_metric": "cosine", "m": 16, "ef_construction": 64, "embedding_dim": 768},
                health_check_endpoint="/v1/search/dense",
            ),
            PlatformBatteryDTO(
                id="colbert_maxsim_reranker",
                name="ColBERT MaxSim Late-Interaction Reranker",
                category=BatteryCategory.RETRIEVAL,
                status=BatteryStatus.ACTIVE,
                algorithm_foundation="Token-Level Multi-Vector Late Interaction (Hardware Accelerated)",
                milestone="M80 (v0.65.0)",
                latency_profile="~14ms",
                description="Preserves individual token representations across query and document tokens, scoring relevance via MaxSim sum without lossy pooling.",
                active_parameters={"engine": "colbert_maxsim", "precision": "fp32", "top_k_candidates": 50},
                health_check_endpoint="/v1/search/rerank",
            ),
            PlatformBatteryDTO(
                id="docling_layout_ocr",
                name="Docling Layout-Aware OCR & Table Parser",
                category=BatteryCategory.RETRIEVAL,
                status=BatteryStatus.ACTIVE,
                algorithm_foundation="Docling v2 Deep Layout Parsing & Multi-Column OCR",
                milestone="M72 (v0.58.0)",
                latency_profile="~250ms/page",
                description="Transforms complex enterprise PDFs, scanned tables, and multi-column research papers into clean hierarchical markdown structures.",
                active_parameters={"enable_table_extraction": True, "enable_ocr": True, "format": "markdown"},
                health_check_endpoint="/v1/documents/parse-status",
            ),
            PlatformBatteryDTO(
                id="rlm_python_repl",
                name="RLM Python REPL Execution Sandbox",
                category=BatteryCategory.COMPUTATION_GRAPH,
                status=BatteryStatus.ACTIVE,
                algorithm_foundation="Recursive Language Modeling (RLM) with Restricted Python AST Sandbox",
                milestone="M48 / M56 (v0.45.0)",
                latency_profile="~18ms",
                description="Executes sandboxed Python scripts on-the-fly to perform mathematical aggregations, financial tax math, and dynamic data filtering.",
                active_parameters={"max_runtime_sec": 5, "allowed_builtins": ["sum", "len", "min", "max", "math", "statistics"]},
                health_check_endpoint="/v1/rlm/sandbox/health",
            ),
            PlatformBatteryDTO(
                id="graphrag_hdbscan_clustering",
                name="GraphRAG HDBSCAN Community Clustering",
                category=BatteryCategory.COMPUTATION_GRAPH,
                status=BatteryStatus.ACTIVE,
                algorithm_foundation="Hierarchical Density-Based Spatial Clustering of Applications with Noise (HDBSCAN)",
                milestone="M81 (v0.66.0)",
                latency_profile="~35ms",
                description="Discovers semantic knowledge topics and multi-hop entity relationships without requiring predefined cluster counts (k).",
                active_parameters={"min_cluster_size": 3, "metric": "euclidean", "cluster_selection_epsilon": 0.15},
                health_check_endpoint="/v1/graph/communities",
            ),
            PlatformBatteryDTO(
                id="neo4j_cypher_graph",
                name="Neo4j Cypher Labeled Property Graph Engine",
                category=BatteryCategory.COMPUTATION_GRAPH,
                status=BatteryStatus.ACTIVE,
                algorithm_foundation="Labeled Property Graph (LPG) Indexing & Cypher Multi-Hop Traversal (Bolt Protocol)",
                milestone="M37 / M44 (v0.35.0)",
                latency_profile="<5ms",
                description="High-throughput multi-hop entity traversal, community clustering, and labeled property graph path finding with automatic PostgreSQL Recursive CTE fallback.",
                active_parameters={"engine": "neo4j", "fallback_engine": "postgres_recursive_cte", "max_hops": 5},
                health_check_endpoint="/v1/admin/tenants/{tenantId}/graph/capabilities",
            ),
            PlatformBatteryDTO(
                id="isolation_forest_sentinel",
                name="Telemetry Anomaly Sentinel",
                category=BatteryCategory.ML_INTELLIGENCE,
                status=BatteryStatus.ACTIVE,
                algorithm_foundation="Scikit-Learn Isolation Forest on Shannon Entropy & Velocity Vectors",
                milestone="M83 (v0.68.0)",
                latency_profile="~4ms",
                description="Detects automated API scraping, token abuse, and distributed request bursts via unsupervised multi-dimensional anomaly scoring.",
                active_parameters={"n_estimators": 100, "contamination": 0.05, "entropy_threshold": 0.82},
                health_check_endpoint="/v1/telemetry/sentinel/status",
            ),
            PlatformBatteryDTO(
                id="quantile_effort_regressor",
                name="Project Effort & Timeline Regressor",
                category=BatteryCategory.ML_INTELLIGENCE,
                status=BatteryStatus.ACTIVE,
                algorithm_foundation="Quantile Gradient Boosting Regressor (P50 Median / P90 High-Risk)",
                milestone="M84 (v0.69.0)",
                latency_profile="~6ms",
                description="Estimates software engineering effort, duration, and confidence intervals for scoping proposals based on DAG complexity.",
                active_parameters={"quantiles": [0.1, 0.5, 0.9], "n_estimators": 120, "max_depth": 4},
                health_check_endpoint="/v1/ml/estimate-effort",
            ),
            PlatformBatteryDTO(
                id="kmeans_persona_classifier",
                name="Zero-Cookie Visitor & Lead Scorer",
                category=BatteryCategory.ML_INTELLIGENCE,
                status=BatteryStatus.ACTIVE,
                algorithm_foundation="KMeans Clustering & Balanced Logistic Regression",
                milestone="M85 (v0.70.0)",
                latency_profile="~3ms",
                description="Clusters anonymous visitors into commercial archetypes (Buyer, Recruiter, Evaluator, Peer) and scores B2B deal propensity.",
                active_parameters={"n_clusters": 4, "random_state": 42, "class_weight": "balanced"},
                health_check_endpoint="/v1/ml/classify-visitor",
            ),
            PlatformBatteryDTO(
                id="token_shield_rate_limiter",
                name="Edge AI Token Shield & Rate Limiter",
                category=BatteryCategory.SAFETY_DEFENSE,
                status=BatteryStatus.ACTIVE,
                algorithm_foundation="Upstash Redis Sliding-Window Token Bucket with Local LRU Fallback",
                milestone="M86 (v0.71.0)",
                latency_profile="~2ms",
                description="Protects LLM inference endpoints from runaway infinite loops, replay attacks, and DDoS spikes with RFC 429 headers.",
                active_parameters={"scoping_limit": 10, "rfp_limit": 5, "copilot_limit": 20, "window_seconds": 60},
                health_check_endpoint="/v1/telemetry/rate-limit/status",
            ),
            PlatformBatteryDTO(
                id="llama_guard_safety_rails",
                name="Structured LlamaGuard 3 Safety Rails",
                category=BatteryCategory.SAFETY_DEFENSE,
                status=BatteryStatus.ACTIVE,
                algorithm_foundation="Llama Guard 3 Policy Categorization (S1-S13 Violations)",
                milestone="M85.1 (v0.70.1)",
                latency_profile="~80ms",
                description="Pre-inference content moderation classifying prompts against safety categories (hate, violence, self-harm, sexual, PII).",
                active_parameters={"policy_categories": ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11", "S12", "S13"]},
                health_check_endpoint="/v1/safety/guardrails/status",
            ),
            PlatformBatteryDTO(
                id="longllmlingua_compression",
                name="LongLLMLingua Context Compression",
                category=BatteryCategory.SAFETY_DEFENSE,
                status=BatteryStatus.ACTIVE,
                algorithm_foundation="Statistical Information Entropy & Token Surprise Pruning",
                milestone="M85.2 (v0.70.2)",
                latency_profile="~45ms",
                description="Compresses retrieved chunk context by 2x-3x while preserving critical reasoning tokens, slashing prompt costs.",
                active_parameters={"compression_target_ratio": 0.5, "min_retained_tokens": 150},
                health_check_endpoint="/v1/cognitive/compress/status",
            ),
            PlatformBatteryDTO(
                id="nemo_conversational_guardrails",
                name="NVIDIA NeMo Conversational Safety Rails",
                category=BatteryCategory.SAFETY_DEFENSE,
                status=BatteryStatus.ACTIVE,
                algorithm_foundation="Programmable Colang Dialog Flows & Sub-20ms Fast-Path Input Rails",
                milestone="M94 (v0.79.0)",
                latency_profile="~14ms",
                description="Enforces conversational scope boundaries, brand tone, anti-jailbreak defenses, and post-inference factual grounding.",
                active_parameters={"mode": "full_conversational", "competitor_shield": True, "grounding_threshold": 0.70},
                health_check_endpoint="/v1/guardrails/overview",
            ),
            PlatformBatteryDTO(
                id="durable_workflow_engine",
                name="Durable Asynchronous Workflow Execution Engine",
                category=BatteryCategory.BACKGROUND_WORKFLOWS,
                status=BatteryStatus.ACTIVE,
                algorithm_foundation="Event-Driven Step Memoization & Resilient Directed Acyclic Graph (DAG) Checkpointing",
                milestone="M95 (v0.80.0)",
                latency_profile="~12ms",
                description="Guarantees resilient multi-step execution for vault chunking, graph synthesis, and benchmarks with step-level memoization and automatic backoff.",
                active_parameters={"max_concurrent_per_tenant": 3, "default_retries": 3, "backoff_factor": 2.0, "checkpoint_store": "PostgreSQL+Redis"},
                health_check_endpoint="/v1/admin/workflows/overview",
            ),
            PlatformBatteryDTO(
                id="serverless_gpu_vllm",
                name="Serverless GPU & Dynamic vLLM / LoRA Pipeline",
                category=BatteryCategory.ML_INTELLIGENCE,
                status=BatteryStatus.ACTIVE,
                algorithm_foundation="Serverless GPU Auto-Scaling (Scale-to-Zero) & Multi-LoRA Dynamic Tensor Swapping (vLLM / Modal)",
                milestone="M96 (v0.81.0)",
                latency_profile="~25ms warm / <3s cold-boot",
                description="Serverless GPU auto-scaling down to 0 instances during idle traffic, cutting cloud compute costs by 70%+ with dynamic runtime LoRA weight swapping on a shared base model.",
                active_parameters={"base_model": "meta-llama/Meta-Llama-3.1-8B-Instruct", "gpu_tier": "A10G", "scale_to_zero_window_sec": 300, "max_loras": 16},
                health_check_endpoint="/v1/admin/serverless/status",
            ),
            PlatformBatteryDTO(
                id="autonomous_fde_metaprogrammer",
                name="Autonomous FDE Metaprogrammer & Capability Studio",
                category=BatteryCategory.SYSTEM_EXTENSIBILITY,
                status=BatteryStatus.ACTIVE,
                algorithm_foundation="AST-Driven Program Synthesis, Static Boundary Verification & Dual-Persona Scaffolding",
                milestone="M97 (v0.82.0)",
                latency_profile="~15ms analysis / ~45ms code synthesis",
                description="Dual-persona solution engine: zero-code battery orchestration for business users, and AST-verified Hexagonal architecture code generation for Forward Deployed Engineers.",
                active_parameters={"supported_personas": ["business", "fde_engineer"], "ast_enforcement": True, "plugin_directory": "src/plugins/custom/"},
                health_check_endpoint="/v1/scaffold/status",
            ),
            PlatformBatteryDTO(
                id="sovereign_edge_sync",
                name="Sovereign Edge SQLite & Vector Sync Engine",
                category=BatteryCategory.EDGE_DISTRIBUTION,
                status=BatteryStatus.ACTIVE,
                algorithm_foundation="Differential Sequence Synchronization + Embedded SQLite FTS5 & Vector BLOB Cosine Fusion",
                milestone="M98 (v0.83.0)",
                latency_profile="<2ms local search / ~10ms delta sync",
                description="Bidirectional vector and chunk delta synchronization between cloud PostgreSQL and standalone edge SQLite databases for offline-first RAG and air-gapped field operations.",
                active_parameters={"storage_format": "sqlite3_fts5_vectorblob", "sync_protocol": "differential_checkpoint_stream", "offline_resolution_tiers": ["local_slm", "grounded_extraction", "speculative_queue"]},
                health_check_endpoint="/v1/admin/edge/overview",
            ),
            PlatformBatteryDTO(
                id="multicloud_failover_libsql",
                name="Distributed Multi-Cloud Failover & Edge Turso LibSQL Replication",
                category=BatteryCategory.EDGE_DISTRIBUTION,
                status=BatteryStatus.ACTIVE,
                algorithm_foundation="Active-Active Quorum Consensus + LibSQL Embedded WAL Replication & Automatic Failover",
                milestone="M99 (v0.84.0)",
                latency_profile="<1ms local replica reads / <800ms failover quorum",
                description="Multi-cloud edge active-active replication using Turso LibSQL embedded replicas with automatic multi-cloud failover, cross-region read replicas, and distributed quorum election.",
                active_parameters={"replication_engine": "libsql_embedded_wal", "quorum_threshold": 0.67, "probe_interval_seconds": 10, "supported_clouds": ["oracle", "aws", "fly_io", "cloudflare"]},
                health_check_endpoint="/v1/admin/multicloud/clusters",
            ),
            PlatformBatteryDTO(
                id="sovereign_edge_voice",
                name="Sovereign Edge Voice & Local Whisper / WebRTC Speech Synthesis",
                category=BatteryCategory.EDGE_DISTRIBUTION,
                status=BatteryStatus.ACTIVE,
                algorithm_foundation="Local Whisper STT + Continuous VAD Energy Endpointing + WebRTC Full-Duplex Streaming TTS",
                milestone="M100 (v0.85.0)",
                latency_profile="<250ms TTFAB (Time-to-First-Audio-Byte)",
                description="Zero-cloud audio egress sovereign voice conversational interface with on-device Whisper speech recognition, VAD turn endpointing, and streaming WebRTC speech synthesis.",
                active_parameters={"stt_engine": "whisper_cpp_embedded", "vad_endpoint_ms": 400, "sample_rate_hz": 16000, "signaling": "webrtc_sdp_ice"},
                health_check_endpoint="/v1/admin/voice/telemetry",
            ),
        ]


    def get_platform_batteries(self) -> PlatformBatteriesResponse:
        resolved = [b.model_copy() for b in self._batteries]
        if self._custom_batteries_provider:
            try:
                custom_batteries = self._custom_batteries_provider()
                resolved.extend(custom_batteries)
            except Exception:
                pass
        if self._status_resolver:
            try:
                overrides = self._status_resolver()
                for b in resolved:
                    if b.id in overrides:
                        b.status = overrides[b.id]
            except Exception:
                pass
        active = sum(1 for b in resolved if b.status == BatteryStatus.ACTIVE)
        standby = sum(1 for b in resolved if b.status == BatteryStatus.STANDBY)
        return PlatformBatteriesResponse(
            total_batteries=len(resolved),
            active_count=active,
            standby_count=standby,
            batteries=resolved,
        )

    def get_tenant_batteries(self, tenant_id: str) -> PlatformBatteriesResponse:
        # Returns tenant-visible capabilities
        return self.get_platform_batteries()

    def get_battery(self, battery_id: str) -> PlatformBatteryDTO | None:
        """Fetch single battery by ID with resolved status."""
        resp = self.get_platform_batteries()
        for b in resp.batteries:
            if b.id == battery_id:
                return b
        return None
