import uuid
from unittest.mock import AsyncMock

import pytest

from src.domain.abstractions.config import (
    CorrectiveRetrievalSettings,
    TenantConfiguration,
)
from src.domain.abstractions.inference import InferenceResponse, Usage
from src.domain.abstractions.retrieval import (
    CorrectiveRetrievalDecision,
    CorrectiveRetrievalProvider,
    SearchQuery,
    SearchResult,
)
from src.domain.retrieval.corrective_retrieval_service import CorrectiveRetrievalService


def _make_result(chunk_id: str, score: float, content: str = "text") -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        document_id=str(uuid.uuid4()),
        content=content,
        score=score,
        metadata={},
    )


def _make_decision(
    needs_re_retrieval: bool = False,
    confidence_score: float = 0.9,
    reformulated_query: str | None = None,
) -> CorrectiveRetrievalDecision:
    return CorrectiveRetrievalDecision(
        needs_re_retrieval=needs_re_retrieval,
        confidence_score=confidence_score,
        reason="test",
        reformulated_query=reformulated_query,
    )


@pytest.fixture
def mock_search_service():
    svc = AsyncMock()
    svc.search = AsyncMock(return_value=AsyncMock())
    return svc


@pytest.fixture
def mock_orchestrator():
    orch = AsyncMock()
    orch.generate = AsyncMock(
        return_value=InferenceResponse(
            content="test answer",
            usage=Usage(input_tokens=10, output_tokens=20, total_tokens=30),
        )
    )
    return orch


@pytest.fixture
def mock_corrective_provider():
    return AsyncMock(spec=CorrectiveRetrievalProvider)


@pytest.fixture
def tenant_config():
    tc = TenantConfiguration(tenant_id="test-tenant")
    tc.corrective_retrieval_settings = CorrectiveRetrievalSettings(
        enable_corrective_retrieval=True,
        max_retrieval_rounds=2,
        confidence_threshold=0.4,
    )
    return tc


@pytest.fixture
def service(mock_search_service, mock_orchestrator, mock_corrective_provider):
    return CorrectiveRetrievalService(
        search_service=mock_search_service,
        orchestrator=mock_orchestrator,
        corrective_provider=mock_corrective_provider,
    )


def _setup_search_return(service, results: list[SearchResult]):
    resp = AsyncMock()
    resp.results = results
    service.search_service.search.return_value = resp
    return resp


class TestCorrectiveRetrievalService:

    async def test_skips_correction_when_confidence_is_high(
        self, service, mock_corrective_provider, tenant_config
    ):
        _setup_search_return(service, [_make_result("a", 0.95)])
        mock_corrective_provider.evaluate_response.return_value = _make_decision(
            needs_re_retrieval=False, confidence_score=0.95
        )

        response = await service.generate_with_correction(
            tenant_id="t1",
            session_id="s1",
            query="test query",
            search_query=SearchQuery(query="test", tenant_id="t1"),
            tenant_config=tenant_config,
        )

        assert response.content == "test answer"
        assert mock_corrective_provider.evaluate_response.call_count == 1
        assert service.search_service.search.call_count == 1
        assert service.orchestrator.generate.call_count == 1

    async def test_triggers_correction_when_confidence_is_low(
        self, service, mock_corrective_provider, tenant_config
    ):
        _setup_search_return(service, [_make_result("a", 0.95)])
        mock_corrective_provider.evaluate_response.return_value = _make_decision(
            needs_re_retrieval=True, confidence_score=0.2, reformulated_query="refined query"
        )

        response = await service.generate_with_correction(
            tenant_id="t1",
            session_id="s1",
            query="test query",
            search_query=SearchQuery(query="test", tenant_id="t1"),
            tenant_config=tenant_config,
        )

        assert response.content == "test answer"
        assert mock_corrective_provider.evaluate_response.call_count == 1
        assert service.search_service.search.call_count == 2
        assert service.orchestrator.generate.call_count == 2

    async def test_respects_max_retrieval_rounds(
        self, service, mock_corrective_provider, tenant_config
    ):
        tenant_config.corrective_retrieval_settings.max_retrieval_rounds = 3
        _setup_search_return(service, [_make_result("a", 0.95)])
        mock_corrective_provider.evaluate_response.return_value = _make_decision(
            needs_re_retrieval=True, confidence_score=0.1, reformulated_query="refined"
        )

        await service.generate_with_correction(
            tenant_id="t1",
            session_id="s1",
            query="test query",
            search_query=SearchQuery(query="test", tenant_id="t1"),
            tenant_config=tenant_config,
        )

        assert service.search_service.search.call_count == 3
        assert service.orchestrator.generate.call_count == 3
        assert mock_corrective_provider.evaluate_response.call_count == 2

    async def test_caps_at_two_default_rounds(
        self, service, mock_corrective_provider, tenant_config
    ):
        _setup_search_return(service, [_make_result("a", 0.95)])
        mock_corrective_provider.evaluate_response.return_value = _make_decision(
            needs_re_retrieval=True, confidence_score=0.1, reformulated_query="refined"
        )

        await service.generate_with_correction(
            tenant_id="t1",
            session_id="s1",
            query="test query",
            search_query=SearchQuery(query="test", tenant_id="t1"),
            tenant_config=tenant_config,
        )

        assert service.search_service.search.call_count == 2
        assert service.orchestrator.generate.call_count == 2

    async def test_uses_reformulated_query_for_second_search(
        self, service, mock_corrective_provider, tenant_config
    ):
        _setup_search_return(service, [_make_result("a", 0.95)])
        mock_corrective_provider.evaluate_response.return_value = _make_decision(
            needs_re_retrieval=True,
            confidence_score=0.2,
            reformulated_query="improved query",
        )

        await service.generate_with_correction(
            tenant_id="t1",
            session_id="s1",
            query="original query",
            search_query=SearchQuery(query="original query", tenant_id="t1"),
            tenant_config=tenant_config,
        )

        calls = service.search_service.search.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0].query == "original query"
        assert calls[1][0][0].query == "improved query"

    async def test_falls_back_to_original_query_when_reformulated_is_none(
        self, service, mock_corrective_provider, tenant_config
    ):
        _setup_search_return(service, [_make_result("a", 0.95)])
        mock_corrective_provider.evaluate_response.return_value = _make_decision(
            needs_re_retrieval=True,
            confidence_score=0.2,
            reformulated_query=None,
        )

        await service.generate_with_correction(
            tenant_id="t1",
            session_id="s1",
            query="original query",
            search_query=SearchQuery(query="original query", tenant_id="t1"),
            tenant_config=tenant_config,
        )

        assert service.search_service.search.call_args_list[1][0][0].query == "original query"

    async def test_stops_if_provider_evaluation_fails(
        self, service, mock_corrective_provider, tenant_config
    ):
        _setup_search_return(service, [_make_result("a", 0.95)])
        mock_corrective_provider.evaluate_response.side_effect = Exception("evaluation failed")

        response = await service.generate_with_correction(
            tenant_id="t1",
            session_id="s1",
            query="test query",
            search_query=SearchQuery(query="test", tenant_id="t1"),
            tenant_config=tenant_config,
        )

        assert response.content == "test answer"
        assert service.search_service.search.call_count == 1
        assert service.orchestrator.generate.call_count == 1


class TestLLMCorrectiveRetrievalAdapter:

    @pytest.mark.asyncio
    async def test_adapter_returns_decision_on_success(self):
        from src.adapters.cognitive.corrective_retrieval_adapter import (
            LLMCorrectiveRetrievalAdapter,
        )

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock()
        mock_llm.generate.return_value.content = (
            '{"needs_re_retrieval": true, "confidence_score": 0.3, "reason": "low confidence", "reformulated_query": "improved query"}'
        )

        adapter = LLMCorrectiveRetrievalAdapter(llm=mock_llm)
        decision = await adapter.evaluate_response(
            query="test",
            response="test answer",
            context_chunks=[_make_result("a", 0.9, content="some context")],
        )

        assert decision.needs_re_retrieval is True
        assert decision.confidence_score == 0.3
        assert decision.reformulated_query == "improved query"
        assert mock_llm.generate.call_count == 1

    @pytest.mark.asyncio
    async def test_adapter_graceful_on_failure(self):
        from src.adapters.cognitive.corrective_retrieval_adapter import (
            LLMCorrectiveRetrievalAdapter,
        )

        mock_llm = AsyncMock()
        mock_llm.generate.side_effect = Exception("LLM call failed")

        adapter = LLMCorrectiveRetrievalAdapter(llm=mock_llm)
        decision = await adapter.evaluate_response(
            query="test", response="test answer", context_chunks=[]
        )

        assert decision.needs_re_retrieval is False
        assert decision.confidence_score == 1.0
