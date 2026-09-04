"""Pure Domain Durable Workflow Engine (Milestone 95).

Orchestrates workflow blueprint registration, event-to-pipeline matching,
and per-tenant execution throttling policies.
Contains ZERO external framework, adapter, or database imports.
"""

import logging

from src.domain.abstractions.durable_workflow import (
    WorkflowDefinition,
    WorkflowEventDispatch,
    WorkflowRunRequest,
    WorkflowStepDefinition,
)
from src.domain.abstractions.exceptions import TenantIsolationViolationError

logger = logging.getLogger(__name__)


class DurableWorkflowEngine:
    """Pure domain orchestrator managing workflow definitions and event routing."""

    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowDefinition] = {}
        self._event_routing: dict[str, list[str]] = {}
        self._register_default_blueprints()

    def register_workflow(self, workflow: WorkflowDefinition) -> None:
        """Register a workflow blueprint in the engine catalog."""
        self._workflows[workflow.name] = workflow
        if workflow.trigger_event:
            self._event_routing.setdefault(workflow.trigger_event, [])
            if workflow.name not in self._event_routing[workflow.trigger_event]:
                self._event_routing[workflow.trigger_event].append(workflow.name)

    def get_workflow(self, name: str) -> WorkflowDefinition | None:
        """Fetch a workflow blueprint by unique name."""
        return self._workflows.get(name)

    def list_workflows(self) -> list[WorkflowDefinition]:
        """Return all registered workflow blueprints."""
        return list(self._workflows.values())

    def match_event(self, event: WorkflowEventDispatch) -> list[WorkflowDefinition]:
        """Find all registered workflows that subscribe to an event."""
        workflow_names = self._event_routing.get(event.event_name, [])
        return [self._workflows[name] for name in workflow_names if name in self._workflows]

    def validate_tenant(self, tenant_id: str) -> None:
        """Validate tenant identifier integrity."""
        if not tenant_id or not tenant_id.strip():
            raise TenantIsolationViolationError("Tenant ID cannot be empty.")

    def build_initial_run_request(
        self, workflow: WorkflowDefinition, event: WorkflowEventDispatch
    ) -> WorkflowRunRequest:
        """Construct a workflow run request from an inbound event dispatch."""
        return WorkflowRunRequest(
            workflow_name=workflow.name,
            input_payload=event.payload,
            idempotency_key=event.idempotency_key,
        )

    def _register_default_blueprints(self) -> None:
        """Register enterprise out-of-the-box durable workflows."""
        # 1. Vault Bulk Ingestion Pipeline
        self.register_workflow(
            WorkflowDefinition(
                name="vault_bulk_ingest",
                title="Enterprise Vault Bulk Ingestion",
                description="Resilient document parsing, PII redaction, chunking, contextualization, embedding, and graph triple extraction.",
                trigger_event="documents.vault_upload",
                concurrency_limit=3,
                max_step_retries=3,
                backoff_factor=2.0,
                initial_interval_seconds=1.0,
                steps=[
                    WorkflowStepDefinition(
                        name="extract_and_anonymize",
                        description="Extract layout/text from binary document and execute Presidio PII redaction.",
                        max_attempts=3,
                        timeout_seconds=60,
                    ),
                    WorkflowStepDefinition(
                        name="hierarchical_or_ast_chunk",
                        description="Decompose document text into semantic AST or hierarchical proposition chunks.",
                        max_attempts=3,
                        timeout_seconds=45,
                    ),
                    WorkflowStepDefinition(
                        name="generate_contextual_headers",
                        description="Generate Anthropic contextual situational headers for each chunk prior to embedding.",
                        max_attempts=3,
                        timeout_seconds=90,
                    ),
                    WorkflowStepDefinition(
                        name="embed_and_index_vectors",
                        description="Compute local nomic-embed-text dense embeddings and insert into pgvector partition.",
                        max_attempts=4,
                        timeout_seconds=120,
                    ),
                    WorkflowStepDefinition(
                        name="extract_knowledge_graph",
                        description="Extract entities, relationships, and commit knowledge graph triples.",
                        max_attempts=3,
                        timeout_seconds=90,
                    ),
                    WorkflowStepDefinition(
                        name="finalize_document_catalog",
                        description="Update document status to COMPLETED and emit ingestion completion telemetry.",
                        max_attempts=2,
                        timeout_seconds=30,
                    ),
                ],
            )
        )

        # 2. Batch Knowledge Graph Extraction Pipeline
        self.register_workflow(
            WorkflowDefinition(
                name="batch_graph_extraction",
                title="Batch Knowledge Graph Synthesis",
                description="Traverse document vault chunks, extract entity-relation triples, and synthesize community clusters.",
                trigger_event="graph.batch_extract",
                concurrency_limit=2,
                max_step_retries=3,
                backoff_factor=2.0,
                initial_interval_seconds=1.0,
                steps=[
                    WorkflowStepDefinition(
                        name="scan_vault_documents",
                        description="Fetch unprocessed document chunks for entity extraction.",
                        max_attempts=3,
                        timeout_seconds=60,
                    ),
                    WorkflowStepDefinition(
                        name="extract_entities_and_triples",
                        description="Execute LLM entity extraction and validate typed relationship links.",
                        max_attempts=3,
                        timeout_seconds=180,
                    ),
                    WorkflowStepDefinition(
                        name="resolve_cross_document_links",
                        description="Resolve entity canonical IDs and unify identical semantic nodes across documents.",
                        max_attempts=3,
                        timeout_seconds=60,
                    ),
                    WorkflowStepDefinition(
                        name="commit_graph_topology",
                        description="Persist graph triples to Neo4j Cypher / PostgreSQL graph tables.",
                        max_attempts=3,
                        timeout_seconds=60,
                    ),
                ],
            )
        )

        # 3. Synthetic Evaluation Benchmark Generator
        self.register_workflow(
            WorkflowDefinition(
                name="synthetic_eval_generator",
                title="Synthetic Evaluation Dataset Generator",
                description="Generate ground-truth Q&A scenarios from document chunks and benchmark retrieval accuracy.",
                trigger_event="evaluation.synthetic_generate",
                concurrency_limit=2,
                max_step_retries=3,
                backoff_factor=2.0,
                initial_interval_seconds=1.0,
                steps=[
                    WorkflowStepDefinition(
                        name="sample_document_propositions",
                        description="Sample diverse proposition chunks across tenant collections.",
                        max_attempts=2,
                        timeout_seconds=30,
                    ),
                    WorkflowStepDefinition(
                        name="generate_qa_scenarios",
                        description="Generate challenging synthetic user queries and expected ground-truth answers.",
                        max_attempts=3,
                        timeout_seconds=120,
                    ),
                    WorkflowStepDefinition(
                        name="execute_model_inferences",
                        description="Run candidate retrieval and generation against target LLM models.",
                        max_attempts=3,
                        timeout_seconds=150,
                    ),
                    WorkflowStepDefinition(
                        name="evaluate_grounding_metrics",
                        description="Calculate Faithfulness, Context Recall, and Semantic NLI consistency scores.",
                        max_attempts=3,
                        timeout_seconds=90,
                    ),
                ],
            )
        )

        # 4. Bulk Vector Re-Embedding Pipeline
        self.register_workflow(
            WorkflowDefinition(
                name="bulk_reembed_pipeline",
                title="Bulk Vector Space Re-Embedding",
                description="Zero-downtime re-embedding of document chunks when migrating embedding models or dimensions.",
                trigger_event="vectors.bulk_reembed",
                concurrency_limit=1,
                max_step_retries=4,
                backoff_factor=2.0,
                initial_interval_seconds=2.0,
                steps=[
                    WorkflowStepDefinition(
                        name="validate_target_dimension",
                        description="Verify target vector partition table (768d, 1024d, 1536d, 3072d) and model availability.",
                        max_attempts=2,
                        timeout_seconds=30,
                    ),
                    WorkflowStepDefinition(
                        name="batch_fetch_chunks",
                        description="Page through tenant document chunks requiring vector re-embedding.",
                        max_attempts=3,
                        timeout_seconds=60,
                    ),
                    WorkflowStepDefinition(
                        name="generate_vector_embeddings",
                        description="Batch compute dense embeddings with local Ollama / dedicated embedding provider.",
                        max_attempts=4,
                        timeout_seconds=300,
                    ),
                    WorkflowStepDefinition(
                        name="swap_vector_partitions",
                        description="Atomically route tenant retrieval queries to newly populated vector partition.",
                        max_attempts=2,
                        timeout_seconds=45,
                    ),
                ],
            )
        )
