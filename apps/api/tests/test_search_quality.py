"""Search quality metrics in production flow.

Tests that the orchestrator emits nDCG@10, MRR, and hit_rate@10
as Prometheus observations, using LLM citations as relevance proxy.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.abstractions.config import TenantConfiguration
from src.domain.abstractions.inference import InferenceResponse, LlmProvider, Usage
from src.domain.abstractions.retrieval import SearchResult
from src.domain.abstractions.telemetry import MetricsRegistry
from src.domain.inference.citation_validator import CitationValidator
from src.domain.inference.orchestrator import InferenceOrchestrator
from src.domain.inference.prompt_builder import PromptBuilder


def _make_result(chunk_id: str, score: float = 0.9) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        document_id=str(uuid.uuid4()),
        content="some content",
        score=score,
        metadata={},
    )


@pytest.fixture
def mock_llm():
    llm = AsyncMock(spec=LlmProvider)
    llm.generate.return_value = InferenceResponse(
        content="Answer citing [Source: chunk_a] and [Source: chunk_b].",
        usage=Usage(input_tokens=10, output_tokens=20, total_tokens=30),
    )
    return llm


@pytest.fixture
def mock_metrics():
    metrics = MagicMock(spec=MetricsRegistry)
    return metrics


@pytest.fixture
def mock_session_repo():
    repo = AsyncMock()
    repo.get_messages.return_value = []
    return repo


@pytest.fixture
def mock_prompt_builder():
    builder = AsyncMock(spec=PromptBuilder)
    builder.build_messages.return_value = []
    return builder


@pytest.fixture
def orchestrator(mock_llm, mock_prompt_builder, mock_session_repo, mock_metrics):
    return InferenceOrchestrator(
        llm_provider=mock_llm,
        prompt_builder=mock_prompt_builder,
        citation_validator=CitationValidator(),
        session_repo=mock_session_repo,
        log_writer=AsyncMock(),
        metrics_registry=mock_metrics,
    )


class TestSearchQualityMetrics:

    @pytest.fixture
    def tenant_config(self):
        return TenantConfiguration(tenant_id="t1")

    async def test_emits_metrics_when_citations_present(
        self, orchestrator, mock_metrics, tenant_config
    ):
        chunks = [_make_result("chunk_a"), _make_result("chunk_b"), _make_result("chunk_c")]
        orchestrator.citation_validator.set_valid_ids(["chunk_a", "chunk_b", "chunk_c"])

        await orchestrator.generate(
            tenant_id="t1",
            session_id="s1",
            query="test query",
            context_chunks=chunks,
            tenant_config=tenant_config,
        )

        assert mock_metrics.observe.call_count == 3
        metric_names = {call[0][0] for call in mock_metrics.observe.call_args_list}
        assert "search_ndcg_at_10" in metric_names
        assert "search_mrr" in metric_names
        assert "search_hit_rate_at_10" in metric_names

    async def test_skips_metrics_when_no_citations(
        self, orchestrator, mock_metrics, tenant_config
    ):
        orchestrator.llm.generate.return_value = InferenceResponse(
            content="Answer with no citations.",
            usage=Usage(input_tokens=5, output_tokens=10, total_tokens=15),
        )

        await orchestrator.generate(
            tenant_id="t1",
            session_id="s1",
            query="test query",
            context_chunks=[_make_result("chunk_a")],
            tenant_config=tenant_config,
        )

        mock_metrics.observe.assert_not_called()

    async def test_skips_metrics_when_no_metrics_registry(
        self, mock_llm, mock_prompt_builder, mock_session_repo, tenant_config
    ):
        mock_llm.generate.return_value = InferenceResponse(
            content="Answer citing [Source: chunk_a].",
            usage=Usage(input_tokens=5, output_tokens=10, total_tokens=15),
        )
        orch = InferenceOrchestrator(
            llm_provider=mock_llm,
            prompt_builder=mock_prompt_builder,
            citation_validator=CitationValidator(),
            session_repo=mock_session_repo,
            log_writer=AsyncMock(),
            metrics_registry=None,
        )
        orch.citation_validator.set_valid_ids(["chunk_a"])

        response = await orch.generate(
            tenant_id="t1",
            session_id="s1",
            query="test query",
            context_chunks=[_make_result("chunk_a")],
            tenant_config=tenant_config,
        )

        assert response.content == "Answer citing [Source: chunk_a]."

    async def test_emits_correct_search_metrics_values(
        self, orchestrator, mock_metrics, tenant_config
    ):
        chunks = [_make_result("chunk_a"), _make_result("chunk_b"), _make_result("chunk_c")]
        orchestrator.citation_validator.set_valid_ids(["chunk_a", "chunk_b", "chunk_c"])

        await orchestrator.generate(
            tenant_id="t1",
            session_id="s1",
            query="test query",
            context_chunks=chunks,
            tenant_config=tenant_config,
        )

        calls = {call[0][0]: call[0][1] for call in mock_metrics.observe.call_args_list}
        # chunk_a, chunk_b cited; chunk_a at rank 1, chunk_b at rank 2
        assert calls["search_mrr"] == 1.0
        assert 0 < calls["search_ndcg_at_10"] <= 1.0
        assert calls["search_hit_rate_at_10"] == 1.0
