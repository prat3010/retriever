"""Requirement Analyzer Domain Service (M97).

Analyzes natural language business or technical requirements, determines
which of the platform's 16 active batteries match the request, and assesses
whether the requirement can be satisfied via zero-code battery configuration
or requires custom code scaffolding. Zero infrastructure or framework imports.
"""

import re
from typing import Any, ClassVar

from src.domain.abstractions.scaffolding import (
    RecommendedBatteryConfig,
    RequirementAnalyzerProtocol,
    SolutionPersona,
    UseCaseRequirement,
)


class RequirementAnalyzer(RequirementAnalyzerProtocol):
    """Pure domain implementation of requirement analysis and battery matching."""

    # Taxonomy of platform batteries with keyword triggers and suggested configs
    BATTERY_KNOWLEDGE_BASE: ClassVar[list[dict[str, Any]]] = [
        {
            "id": "docling_layout_ocr",
            "name": "Docling Layout-Aware OCR & Table Parser",
            "category": "retrieval",
            "keywords": ["ocr", "scan", "scanned", "pdf", "table", "invoice", "paper", "layout", "document", "form"],
            "rationale": "Layout-aware vision parsing extracts hierarchical tables and multi-column text with high fidelity.",
            "hyperparams": {"enable_table_extraction": True, "enable_ocr": True, "format": "markdown"},
            "endpoint": "/v1/documents/parse-status",
        },
        {
            "id": "compliance_vault_pii",
            "name": "Enterprise Compliance Vault & Presidio PII Redactor",
            "category": "safety_defense",
            "keywords": ["pii", "redact", "redaction", "hipaa", "gdpr", "privacy", "credit card", "ssn", "medical", "patient", "mask", "pseudonym"],
            "rationale": "Automated Presidio-grade entity masking with deterministic cryptographic pseudonymization and audit erasure certs.",
            "hyperparams": {"masking_strategy": "pseudonym", "enforce_luhn": True, "redact_secrets": True},
            "endpoint": "/v1/compliance/verify",
        },
        {
            "id": "slack_workspace_bot",
            "name": "Slack Workspace Bot & Interactive Actions",
            "category": "connectors",
            "keywords": ["slack", "bot", "channel", "alert", "message", "chat bot", "notification", "team chat"],
            "rationale": "Native Slack bot integration with HMAC signature verification and interactive Block Kit feedback.",
            "hyperparams": {"enable_citations": True, "interactive_feedback": True},
            "endpoint": "/v1/integrations/slack/health",
        },
        {
            "id": "colbert_maxsim_reranker",
            "name": "ColBERT MaxSim Late-Interaction Reranker",
            "category": "retrieval",
            "keywords": ["rerank", "precision", "accuracy", "colbert", "fine-grained", "ranking", "relevance", "token-level"],
            "rationale": "Preserves individual token representations scoring query-document relevance without lossy embedding pooling.",
            "hyperparams": {"precision": "fp32", "top_k_candidates": 50},
            "endpoint": "/v1/search/rerank",
        },
        {
            "id": "pgvector_hnsw_dense",
            "name": "pgvector HNSW Dense Embeddings",
            "category": "retrieval",
            "keywords": ["vector", "semantic", "search", "embedding", "hnsw", "cosine", "similarity", "dense"],
            "rationale": "High-dimensional cosine distance vector search with strict PostgreSQL RLS tenant isolation.",
            "hyperparams": {"distance_metric": "cosine", "m": 16, "ef_construction": 64},
            "endpoint": "/v1/search/dense",
        },
        {
            "id": "bm25_sparse_retrieval",
            "name": "Sublinear BM25 Keyword Search",
            "category": "retrieval",
            "keywords": ["keyword", "exact", "bm25", "id", "sku", "code", "lookup", "term", "identifier", "error code"],
            "rationale": "Okapi BM25 inverted index for fast keyword matching and exact token lookups.",
            "hyperparams": {"k1": 1.5, "b": 0.75},
            "endpoint": "/v1/search/bm25",
        },
        {
            "id": "graphrag_hdbscan_clustering",
            "name": "GraphRAG HDBSCAN Community Clustering",
            "category": "computation_graph",
            "keywords": ["graph", "cluster", "clustering", "community", "topics", "hdbscan", "unsupervised", "relationships", "entity"],
            "rationale": "Discovers semantic knowledge topics and multi-hop entity relationships across tenant documents.",
            "hyperparams": {"min_cluster_size": 3, "metric": "euclidean"},
            "endpoint": "/v1/graph/communities",
        },
        {
            "id": "neo4j_cypher_graph",
            "name": "Neo4j Cypher Labeled Property Graph",
            "category": "computation_graph",
            "keywords": ["neo4j", "cypher", "knowledge graph", "triples", "hops", "multi-hop", "ontologies"],
            "rationale": "High-throughput multi-hop entity traversal and labeled property graph path finding.",
            "hyperparams": {"max_hops": 5, "fallback_engine": "postgres_recursive_cte"},
            "endpoint": "/v1/admin/tenants/graph/capabilities",
        },
        {
            "id": "durable_workflow_engine",
            "name": "Durable Asynchronous Workflow Execution Engine",
            "category": "background_workflows",
            "keywords": ["workflow", "durable", "background", "batch", "memoization", "retry", "long-running", "pipeline", "job", "dag"],
            "rationale": "Guarantees step-level memoization in PostgreSQL with automatic exponential retries for complex jobs.",
            "hyperparams": {"default_retries": 3, "backoff_factor": 2.0},
            "endpoint": "/v1/admin/workflows/overview",
        },
        {
            "id": "serverless_gpu_vllm",
            "name": "Serverless GPU & Dynamic vLLM / LoRA Pipeline",
            "category": "ml_intelligence",
            "keywords": ["gpu", "vllm", "lora", "modal", "fine-tune", "adapter", "serverless", "scale-to-zero", "dedicated"],
            "rationale": "Serverless GPU scaling down to zero idle instances with dynamic multi-tenant LoRA tensor swapping.",
            "hyperparams": {"gpu_tier": "A10G", "scale_to_zero_window_sec": 300},
            "endpoint": "/v1/admin/serverless/status",
        },
        {
            "id": "nemo_conversational_guardrails",
            "name": "NVIDIA NeMo Conversational Safety Rails",
            "category": "safety_defense",
            "keywords": ["guardrail", "safety", "jailbreak", "colang", "brand tone", "moderation", "factual grounding", "nemo"],
            "rationale": "Programmable Colang flows controlling dialogue scope, sub-20ms fast input rails, and factual ground checks.",
            "hyperparams": {"mode": "full_conversational", "competitor_shield": True},
            "endpoint": "/v1/guardrails/overview",
        },
        {
            "id": "rlm_python_repl",
            "name": "RLM Python REPL Execution Sandbox",
            "category": "computation_graph",
            "keywords": ["math", "calculation", "python", "repl", "formula", "financial", "tax", "sandbox", "aggregation"],
            "rationale": "Restricted Python AST sandbox for executing on-the-fly mathematical and financial calculations.",
            "hyperparams": {"max_runtime_sec": 5},
            "endpoint": "/v1/rlm/sandbox/health",
        },
    ]

    CUSTOM_SCAFFOLD_TRIGGERS: ClassVar[list[str]] = [
        "custom",
        "sync",
        "connector",
        "webhook",
        "integration",
        "hubspot",
        "salesforce",
        "jira",
        "adapter",
        "plugin",
        "export",
        "api",
        "endpoint",
        "cron",
        "database",
        "stripe",
        "zendesk",
        "github",
        "linear",
        "notion",
        "postgres",
        "mongodb",
    ]

    def analyze(self, req: UseCaseRequirement) -> list[RecommendedBatteryConfig]:
        """Match requirement against active platform batteries."""
        prompt_lower = req.prompt.lower()
        domain_lower = req.target_domain.lower()
        tokens = set(re.findall(r"\b\w+\b", prompt_lower + " " + domain_lower))

        recommendations: list[RecommendedBatteryConfig] = []

        for b in self.BATTERY_KNOWLEDGE_BASE:
            keyword_matches = [k for k in b["keywords"] if k in prompt_lower or k in tokens]
            if keyword_matches:
                # Calculate confidence score based on match count and prompt length
                match_ratio = min(1.0, 0.45 + (len(keyword_matches) * 0.18))
                recommendations.append(
                    RecommendedBatteryConfig(
                        battery_id=b["id"],
                        battery_name=b["name"],
                        category=b["category"],
                        match_confidence=round(match_ratio, 2),
                        rationale=b["rationale"] + f" (Matched intents: {', '.join(keyword_matches[:3])})",
                        suggested_hyperparameters=b["hyperparams"],
                        health_check_endpoint=b["endpoint"],
                    )
                )

        # Sort recommendations by highest confidence
        recommendations.sort(key=lambda r: r.match_confidence, reverse=True)
        return recommendations[:5]

    def assess_capability_gap(self, req: UseCaseRequirement) -> bool:
        """Evaluate if requirement needs custom code scaffolding."""
        if req.persona == SolutionPersona.FDE_ENGINEER:
            return True

        prompt_lower = req.prompt.lower()
        has_custom_trigger = any(trigger in prompt_lower for trigger in self.CUSTOM_SCAFFOLD_TRIGGERS)
        if has_custom_trigger:
            return True

        # If existing batteries cannot match with confidence >= 0.75, it's a capability gap
        matches = self.analyze(req)
        if not matches or matches[0].match_confidence < 0.75:
            return True

        return False
