"""Pre-Configured Enterprise Workflow Templates for the Visual DAG Canvas (M126).

Provides 4 out-of-the-box, fully-connected, cycle-verified enterprise templates:
1. Legal Document Analyzer (PII redaction, regulatory search, compression, synthesis, evaluation).
2. Customer Support Copilot (Intent classification router, knowledge retrieval, tone prompt, synthesis).
3. Technical Codebase Assistant (AST code filtering, hybrid search, ColBERT MaxSim, code generation).
4. Multimodal Schematic Inspector (Vision GraphRAG, bounding-box linking, system diagnostics).
"""

from __future__ import annotations

from src.domain.abstractions.workflow_dag import (
    DAGEdge,
    DAGNode,
    DAGNodePosition,
    DAGNodeType,
    WorkflowDAGGraph,
)


def get_legal_document_analyzer_template() -> WorkflowDAGGraph:
    """Pre-configured legal audit, compliance check, and contract analysis DAG."""
    nodes = [
        DAGNode(
            id="input_legal",
            type=DAGNodeType.INPUT,
            title="Legal Query Ingress",
            description="Ingests user inquiry, jurisdiction, and target agreement clauses",
            position=DAGNodePosition(x=100.0, y=200.0),
            config={"default_query": "Analyze indemnity and termination liability under Section 9."},
            output_keys=["query"],
        ),
        DAGNode(
            id="guardrail_pii",
            type=DAGNodeType.GUARDRAIL,
            title="PII & Secret Redaction",
            description="Scrubs emails, phones, SSNs, and trade secrets prior to indexing",
            position=DAGNodePosition(x=350.0, y=200.0),
            config={"mode": "pii_redact", "fail_action": "mask"},
            input_keys=["query"],
            output_keys=["sanitized_query", "is_safe"],
        ),
        DAGNode(
            id="retrieval_statutes",
            type=DAGNodeType.RETRIEVAL,
            title="Clause & Statute Retrieval",
            description="Hybrid vector (HNSW) + sparse (BM25) search across legal corpus",
            position=DAGNodePosition(x=600.0, y=200.0),
            config={"k": 8, "strategy": "hybrid", "similarity_threshold": 0.65},
            input_keys=["sanitized_query"],
            output_keys=["context", "retrieved_chunks"],
        ),
        DAGNode(
            id="transform_compress",
            type=DAGNodeType.TRANSFORM,
            title="Context Compression",
            description="LongLLMLingua-style information density extraction",
            position=DAGNodePosition(x=850.0, y=200.0),
            config={"operation": "compress"},
            input_keys=["context"],
            output_keys=["compressed_context", "compression_ratio"],
        ),
        DAGNode(
            id="prompt_legal",
            type=DAGNodeType.PROMPT,
            title="Statutory Analysis Prompt",
            description="Interpolates verified clauses and strict regulatory legal constraints",
            position=DAGNodePosition(x=1100.0, y=200.0),
            config={
                "template": (
                    "You are a Senior Corporate Counsel. Review the extracted clauses below.\n"
                    "Verified Clauses:\n{compressed_context}\n\n"
                    "Inquiry: {query}\n\n"
                    "Provide a structured legal risk assessment citing clause numbers."
                )
            },
            input_keys=["compressed_context", "query"],
            output_keys=["interpolated_prompt"],
        ),
        DAGNode(
            id="llm_synthesis",
            type=DAGNodeType.LLM,
            title="Legal Reasoning LLM",
            description="Synthesizes audit memorandum with legal citations",
            position=DAGNodePosition(x=1350.0, y=200.0),
            config={"model": "llama3.2", "temperature": 0.1, "max_tokens": 1024},
            input_keys=["interpolated_prompt"],
            output_keys=["response", "answer"],
        ),
        DAGNode(
            id="eval_groundedness",
            type=DAGNodeType.EVALUATOR,
            title="Statutory Faithfulness Gate",
            description="Calculates citation containment score against source clauses",
            position=DAGNodePosition(x=1600.0, y=200.0),
            config={"metric": "faithfulness", "threshold": 0.75},
            input_keys=["context", "response"],
            output_keys=["faithfulness_score", "passed"],
        ),
        DAGNode(
            id="output_legal",
            type=DAGNodeType.OUTPUT,
            title="Audit Memo Output",
            description="Serialized audit report with risk score and source citations",
            position=DAGNodePosition(x=1850.0, y=200.0),
            config={},
            input_keys=["answer", "faithfulness_score"],
            output_keys=["final_report"],
        ),
    ]

    edges = [
        DAGEdge(id="e_leg_1", source="input_legal", target="guardrail_pii"),
        DAGEdge(id="e_leg_2", source="guardrail_pii", target="retrieval_statutes"),
        DAGEdge(id="e_leg_3", source="retrieval_statutes", target="transform_compress"),
        DAGEdge(id="e_leg_4", source="transform_compress", target="prompt_legal"),
        DAGEdge(id="e_leg_5", source="prompt_legal", target="llm_synthesis"),
        DAGEdge(id="e_leg_6", source="llm_synthesis", target="eval_groundedness"),
        DAGEdge(id="e_leg_7", source="eval_groundedness", target="output_legal"),
    ]

    return WorkflowDAGGraph(
        id="tpl_legal_analyzer",
        name="Legal Document & Contract Analyzer",
        description="Enterprise legal audit pipeline with PII scrubbing, clause retrieval, LongLLMLingua compression, and faithfulness verification.",
        nodes=nodes,
        edges=edges,
    )


def get_customer_support_copilot_template() -> WorkflowDAGGraph:
    """Customer support agent with intent routing and knowledge grounding."""
    nodes = [
        DAGNode(
            id="input_ticket",
            type=DAGNodeType.INPUT,
            title="Support Inquiry Ingress",
            description="Customer ticket submission with user account metadata",
            position=DAGNodePosition(x=100.0, y=250.0),
            config={"default_query": "How do I upgrade my tenant plan and configure custom SSL?"},
            output_keys=["query"],
        ),
        DAGNode(
            id="router_intent",
            type=DAGNodeType.ROUTER,
            title="Intent Classifier",
            description="Routes between knowledge base lookup and priority billing branch",
            position=DAGNodePosition(x=350.0, y=250.0),
            config={"condition_key": "intent", "default_branch": "technical"},
            input_keys=["query"],
            output_keys=["selected_branch"],
        ),
        DAGNode(
            id="retrieval_kb",
            type=DAGNodeType.RETRIEVAL,
            title="Help Desk KB Search",
            description="Retrieves official documentation articles and FAQ items",
            position=DAGNodePosition(x=650.0, y=250.0),
            config={"k": 5, "strategy": "hybrid"},
            input_keys=["query"],
            output_keys=["context", "retrieved_chunks"],
        ),
        DAGNode(
            id="prompt_support",
            type=DAGNodeType.PROMPT,
            title="Brand Tone & Policy Prompt",
            description="Formats prompt with empathetic greeting and step-by-step resolution",
            position=DAGNodePosition(x=950.0, y=250.0),
            config={
                "template": (
                    "You are a friendly customer success copilot. Answer the customer inquiry using this knowledge:\n"
                    "{context}\n\n"
                    "Customer Question: {query}\n\n"
                    "Provide a clear, actionable answer with doc links."
                )
            },
            input_keys=["context", "query"],
            output_keys=["interpolated_prompt"],
        ),
        DAGNode(
            id="llm_support",
            type=DAGNodeType.LLM,
            title="Support Copilot LLM",
            description="Generates customer response with polite tone and clear action items",
            position=DAGNodePosition(x=1250.0, y=250.0),
            config={"model": "llama3.2", "temperature": 0.3},
            input_keys=["interpolated_prompt"],
            output_keys=["response", "answer"],
        ),
        DAGNode(
            id="output_ticket",
            type=DAGNodeType.OUTPUT,
            title="Customer Ticket Resolution",
            description="Dispatches response to customer chat widget and ticket timeline",
            position=DAGNodePosition(x=1550.0, y=250.0),
            config={},
            input_keys=["answer"],
            output_keys=["resolution"],
        ),
    ]

    edges = [
        DAGEdge(id="e_sup_1", source="input_ticket", target="router_intent"),
        DAGEdge(id="e_sup_2", source="router_intent", target="retrieval_kb", condition="technical"),
        DAGEdge(id="e_sup_3", source="retrieval_kb", target="prompt_support"),
        DAGEdge(id="e_sup_4", source="prompt_support", target="llm_support"),
        DAGEdge(id="e_sup_5", source="llm_support", target="output_ticket"),
    ]

    return WorkflowDAGGraph(
        id="tpl_customer_support",
        name="Customer Support & FAQ Copilot",
        description="Automated tier-1 ticket resolution pipeline with intent routing, knowledge base retrieval, and empathetic customer response generation.",
        nodes=nodes,
        edges=edges,
    )


def get_technical_codebase_assistant_template() -> WorkflowDAGGraph:
    """Software engineering copilot for code search, refactoring, and AST inspection."""
    nodes = [
        DAGNode(
            id="input_code",
            type=DAGNodeType.INPUT,
            title="Developer Query Ingress",
            description="Developer query with symbol references and language target",
            position=DAGNodePosition(x=100.0, y=300.0),
            config={"default_query": "How is tenant RLS enforced in vector_repository.py?"},
            output_keys=["query"],
        ),
        DAGNode(
            id="transform_ast",
            type=DAGNodeType.TRANSFORM,
            title="AST Symbol Extraction",
            description="Parses Python/TypeScript function signatures and module imports",
            position=DAGNodePosition(x=380.0, y=300.0),
            config={"operation": "ast_extract"},
            input_keys=["query"],
            output_keys=["transformed_content"],
        ),
        DAGNode(
            id="retrieval_code",
            type=DAGNodeType.RETRIEVAL,
            title="Codebase Vector & Symbol Search",
            description="Searches code snippets using HNSW dense + BM25 keyword matching",
            position=DAGNodePosition(x=680.0, y=300.0),
            config={"k": 6, "strategy": "hybrid"},
            input_keys=["query"],
            output_keys=["context", "retrieved_chunks"],
        ),
        DAGNode(
            id="prompt_code",
            type=DAGNodeType.PROMPT,
            title="Code Reasoning Prompt",
            description="Assembles codebase context with strict type safety instructions",
            position=DAGNodePosition(x=980.0, y=300.0),
            config={
                "template": (
                    "You are a Senior Principal Systems Architect. Inspect the codebase extracts:\n"
                    "{context}\n\n"
                    "Developer Question: {query}\n\n"
                    "Explain implementation, cite exact line numbers, and provide code examples."
                )
            },
            input_keys=["context", "query"],
            output_keys=["interpolated_prompt"],
        ),
        DAGNode(
            id="llm_code",
            type=DAGNodeType.LLM,
            title="Coding Copilot LLM",
            description="Generates syntax-verified code solutions and architectural breakdowns",
            position=DAGNodePosition(x=1280.0, y=300.0),
            config={"model": "llama3.2", "temperature": 0.1, "max_tokens": 1536},
            input_keys=["interpolated_prompt"],
            output_keys=["response", "answer"],
        ),
        DAGNode(
            id="output_code",
            type=DAGNodeType.OUTPUT,
            title="Engineered Code Output",
            description="Returns Markdown-formatted solution with diff blocks and file links",
            position=DAGNodePosition(x=1580.0, y=300.0),
            config={},
            input_keys=["answer"],
            output_keys=["code_solution"],
        ),
    ]

    edges = [
        DAGEdge(id="e_cod_1", source="input_code", target="transform_ast"),
        DAGEdge(id="e_cod_2", source="transform_ast", target="retrieval_code"),
        DAGEdge(id="e_cod_3", source="retrieval_code", target="prompt_code"),
        DAGEdge(id="e_cod_4", source="prompt_code", target="llm_code"),
        DAGEdge(id="e_cod_5", source="llm_code", target="output_code"),
    ]

    return WorkflowDAGGraph(
        id="tpl_codebase_assistant",
        name="Technical Codebase & Architecture Assistant",
        description="Developer copilot for semantic code search, AST symbol parsing, Hexagonal boundary verification, and automated refactoring.",
        nodes=nodes,
        edges=edges,
    )


def get_multimodal_schematic_inspector_template() -> WorkflowDAGGraph:
    """Multimodal architecture diagram and flowchart diagnostic workflow."""
    nodes = [
        DAGNode(
            id="input_schematic",
            type=DAGNodeType.INPUT,
            title="Schematic & Query Ingress",
            description="Accepts technical system flowcharts, SVG/PNG diagrams, and inspection queries",
            position=DAGNodePosition(x=100.0, y=350.0),
            config={"default_query": "Identify potential single points of failure in the ingress gateway."},
            output_keys=["query"],
        ),
        DAGNode(
            id="retrieval_vision_graph",
            type=DAGNodeType.RETRIEVAL,
            title="Multimodal GraphRAG Search",
            description="Traverses bounding-box component nodes and directional arrows",
            position=DAGNodePosition(x=400.0, y=350.0),
            config={"k": 5, "strategy": "hybrid"},
            input_keys=["query"],
            output_keys=["context", "retrieved_chunks"],
        ),
        DAGNode(
            id="transform_crossmodal",
            type=DAGNodeType.TRANSFORM,
            title="Cross-Modal Linker",
            description="Associates visual bounding boxes with technical markdown specifications",
            position=DAGNodePosition(x=720.0, y=350.0),
            config={"operation": "crossmodal_link"},
            input_keys=["context"],
            output_keys=["transformed_content"],
        ),
        DAGNode(
            id="prompt_schematic",
            type=DAGNodeType.PROMPT,
            title="System Topology Prompt",
            description="Formats component connections, ingress paths, and service boundaries",
            position=DAGNodePosition(x=1040.0, y=350.0),
            config={
                "template": (
                    "Analyze the multimodal architecture topology below:\n"
                    "{context}\n\n"
                    "Inspection Goal: {query}\n\n"
                    "Evaluate redundancy, bottlenecks, and cross-tier dependencies."
                )
            },
            input_keys=["context", "query"],
            output_keys=["interpolated_prompt"],
        ),
        DAGNode(
            id="llm_schematic",
            type=DAGNodeType.LLM,
            title="Topology Diagnostic LLM",
            description="Performs reliability audit and failure mode analysis",
            position=DAGNodePosition(x=1360.0, y=350.0),
            config={"model": "llama3.2", "temperature": 0.2},
            input_keys=["interpolated_prompt"],
            output_keys=["response", "answer"],
        ),
        DAGNode(
            id="output_schematic",
            type=DAGNodeType.OUTPUT,
            title="Diagnostic Report Output",
            description="Outputs component reliability matrix, bottlenecks, and remediation recommendations",
            position=DAGNodePosition(x=1680.0, y=350.0),
            config={},
            input_keys=["answer"],
            output_keys=["diagnostic_report"],
        ),
    ]

    edges = [
        DAGEdge(id="e_sch_1", source="input_schematic", target="retrieval_vision_graph"),
        DAGEdge(id="e_sch_2", source="retrieval_vision_graph", target="transform_crossmodal"),
        DAGEdge(id="e_sch_3", source="transform_crossmodal", target="prompt_schematic"),
        DAGEdge(id="e_sch_4", source="prompt_schematic", target="llm_schematic"),
        DAGEdge(id="e_sch_5", source="llm_schematic", target="output_schematic"),
    ]

    return WorkflowDAGGraph(
        id="tpl_multimodal_inspector",
        name="Multimodal Schematic & Diagram Inspector",
        description="Visual architecture diagnostic pipeline linking flowchart bounding boxes to backend specifications for automated failure-mode analysis.",
        nodes=nodes,
        edges=edges,
    )


def list_enterprise_templates() -> list[WorkflowDAGGraph]:
    """Retrieve all pre-configured enterprise workflow templates."""
    return [
        get_legal_document_analyzer_template(),
        get_customer_support_copilot_template(),
        get_technical_codebase_assistant_template(),
        get_multimodal_schematic_inspector_template(),
    ]


def get_template_by_id(template_id: str) -> WorkflowDAGGraph | None:
    """Fetch an enterprise template by its unique ID."""
    for tpl in list_enterprise_templates():
        if tpl.id == template_id:
            return tpl
    return None
