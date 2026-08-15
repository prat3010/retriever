"""Recursive Language Model (RLM) Execution Engine.

Orchestrates programmatic document inspection, Python REPL sandbox execution,
and recursive sub-LLM synthesis for analytical multi-document tasks.
"""

import logging
import time
from typing import Any

from src.domain.abstractions.inference import ChatMessage, LlmProvider
from src.domain.abstractions.retrieval import SearchQuery
from src.domain.retrieval.search_service import HybridSearchService
from src.domain.rlm.abstractions import (
    ReplSandboxProvider,
    RlmAnalysisRequest,
    RlmAnalysisResult,
)

logger = logging.getLogger(__name__)

RLM_CODE_GEN_PROMPT = """You are a Recursive Language Model (RLM) analytical planner.
Your goal is to inspect document chunk data programmatically using Python code to solve the user's analytical query.

Context Data Available:
- `chunks`: A list of document chunk objects with attributes: `.content`, `.document_id`, `.score`, `.metadata`.

INSTRUCTIONS:
Write a simple Python script to process `chunks` and calculate/aggregate relevant data.
Store your final computed answer in a variable named `result`.

Example:
```python
total_score = sum(c.score for c in chunks)
result = f"Analyzed {len(chunks)} chunks with total score {total_score:.2f}"
```
Output ONLY the raw Python code block enclosed in ```python ... ```.
"""


class RlmExecutionEngine:
    """Recursive Language Model execution engine."""

    def __init__(
        self,
        llm_provider: LlmProvider,
        sandbox_provider: ReplSandboxProvider,
        search_service: HybridSearchService,
    ) -> None:
        self.llm = llm_provider
        self.sandbox = sandbox_provider
        self.search = search_service

    async def analyze(self, request: RlmAnalysisRequest) -> RlmAnalysisResult:
        """Execute recursive analytical synthesis workflow."""
        start_time = time.monotonic()
        code_executions: list[dict[str, Any]] = []

        # 1. Fetch relevant document chunks via search service
        search_query = SearchQuery(
            tenant_id=request.tenant_id,
            query=request.prompt,
            top_k=10,
            enable_hybrid=True,
            enable_graph_search=True,
        )
        search_resp = await self.search.search(
            tenant_id=request.tenant_id, query=search_query
        )
        chunks = search_resp.results

        # Wrap chunks for Python REPL sandbox context
        class ChunkWrapper:
            def __init__(self, c: Any) -> None:
                self.content = c.content
                self.document_id = c.document_id
                self.score = c.score
                self.metadata = c.metadata

        context_chunks = [ChunkWrapper(c) for c in chunks]

        # 2. Ask LLM to generate data-processing Python code
        code_gen_messages = [
            ChatMessage(role="system", content=RLM_CODE_GEN_PROMPT),
            ChatMessage(
                role="user",
                content=f"Task: {request.prompt}\nLoaded {len(chunks)} target document chunks.",
            ),
        ]
        llm_code_resp = await self.llm.generate(
            messages=code_gen_messages, temperature=0.1, max_tokens=600
        )
        raw_code = llm_code_resp.content.strip()

        # Clean code fences
        if "```python" in raw_code:
            code_snippet = raw_code.split("```python")[1].split("```")[0].strip()
        elif "```" in raw_code:
            code_snippet = raw_code.split("```")[1].split("```")[0].strip()
        else:
            code_snippet = raw_code

        # 3. Execute script in safe AST REPL sandbox
        sandbox_res = await self.sandbox.execute_script(
            tenant_id=request.tenant_id,
            code=code_snippet,
            context_dict={"chunks": context_chunks},
            timeout_seconds=15.0,
        )

        code_executions.append(
            {
                "code": code_snippet,
                "stdout": sandbox_res.output,
                "result": str(sandbox_res.return_value),
                "is_error": sandbox_res.is_error,
                "execution_time_ms": sandbox_res.execution_time_ms,
            }
        )

        # 4. Synthesize final analytical summary combining sandbox output & document evidence
        synthesis_prompt = f"""Target Goal: {request.prompt}
REPL Code Analysis Output: {sandbox_res.return_value}
Console Output: {sandbox_res.output}

Extracted Evidence Highlights:
""" + "\n".join([f"- Document {c.document_id}: {c.content[:200]}" for c in chunks[:5]])

        synth_messages = [
            ChatMessage(
                role="system",
                content="Synthesize a comprehensive analytical response based on the programmatic REPL code analysis and document evidence.",
            ),
            ChatMessage(role="user", content=synthesis_prompt),
        ]
        synth_resp = await self.llm.generate(
            messages=synth_messages, temperature=0.2, max_tokens=1000
        )

        elapsed_ms = (time.monotonic() - start_time) * 1000
        return RlmAnalysisResult(
            tenant_id=request.tenant_id,
            prompt=request.prompt,
            analysis_summary=synth_resp.content.strip(),
            code_executions=code_executions,
            subcalls_count=2,
            execution_time_ms=round(elapsed_ms, 2),
        )
