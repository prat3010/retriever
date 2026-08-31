"""Unit tests for Milestone 73: Hierarchical Community Summarizer."""

from unittest.mock import AsyncMock

import pytest

from src.domain.abstractions.graph import EntityTriple, GraphCommunity
from src.domain.graph.community_summarizer import CommunitySummarizer


def test_heuristic_summary_generation():
    """Verify heuristic summarizer produces structured markdown without LLM."""
    summarizer = CommunitySummarizer()
    comm = GraphCommunity(
        community_id="comm_test_123",
        tenant_id="tenant_abc",
        level=0,
        title="Payment Processing Cluster",
        entities=["Stripe", "Invoice", "CreditCard", "WebhookService"],
        triples=[
            EntityTriple(subject="Stripe", predicate="PROCESSES", object="CreditCard"),
            EntityTriple(subject="Stripe", predicate="CREATES", object="Invoice"),
            EntityTriple(subject="WebhookService", predicate="LISTENS_TO", object="Stripe"),
        ],
        weight=0.8,
    )

    summary = summarizer._generate_heuristic_summary(comm)

    assert "Payment Processing Cluster" in summary
    assert "Primary Entity Hubs:" in summary
    assert "Stripe" in summary
    assert "PROCESSES" in summary or "CREATES" in summary
    assert "Total Entities:** 4" in summary


@pytest.mark.asyncio
async def test_llm_summary_integration():
    """Verify LLM synthesis when provider is available and fallback on failure."""
    summarizer = CommunitySummarizer()
    comm = GraphCommunity(
        community_id="comm_test_456",
        tenant_id="tenant_abc",
        level=1,
        title="Observability Domain",
        entities=["Prometheus", "Grafana", "OTelCollector"],
        triples=[
            EntityTriple(subject="OTelCollector", predicate="EXPORTS_TO", object="Prometheus"),
            EntityTriple(subject="Grafana", predicate="QUERIES", object="Prometheus"),
        ],
        weight=0.9,
    )

    # 1. Successful LLM provider mock
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = "Executive Summary: Prometheus and Grafana form the core telemetry backbone."
    
    result = await summarizer.summarize_community(comm, llm_provider=mock_llm)
    assert "Executive Summary:" in result
    assert comm.summary == result

    # 2. Failing LLM provider triggers heuristic fallback
    failing_llm = AsyncMock()
    failing_llm.generate.side_effect = RuntimeError("API rate limit reached")
    
    fallback_res = await summarizer.summarize_community(comm, llm_provider=failing_llm)
    assert "### Observability Domain" in fallback_res
    assert "Primary Entity Hubs:" in fallback_res
