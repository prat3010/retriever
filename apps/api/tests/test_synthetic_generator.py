"""Unit and API tests for Milestone 77: Synthetic Golden Dataset Generator."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.config import settings
from src.domain.evaluation.synthetic_generator import SyntheticDatasetGenerator
from src.main import app

client = TestClient(app)


# ── 1. Unit Tests: Synthetic Generator ──────────────────────────────────────

@pytest.mark.asyncio
async def test_synthetic_dataset_generator_heuristic_factual():
    """Verify heuristic extractor identifies definition statements and generates questions."""
    generator = SyntheticDatasetGenerator()
    chunks = [
        {
            "chunk_id": "chk_001",
            "content": "A Golden Dataset is a verified benchmark collection of ground-truth Q&A pairs used for evaluating RAG models.",
        }
    ]

    candidates = await generator.synthesize_from_chunks(chunks, count_per_chunk=1)
    assert len(candidates) == 1
    c = candidates[0]
    assert "Golden Dataset" in c.question
    assert "chk_001" in c.relevant_chunk_ids
    assert c.archetype == "factual"
    assert c.ground_truth_answer == chunks[0]["content"]


@pytest.mark.asyncio
async def test_synthetic_dataset_generator_heuristic_conditional():
    """Verify heuristic extractor identifies requirement patterns and marks conditional archetype."""
    generator = SyntheticDatasetGenerator()
    chunks = [
        {
            "chunk_id": "chk_002",
            "content": "The Payment Service requires two-factor authentication for transactions exceeding 10000 rupees.",
        }
    ]

    candidates = await generator.synthesize_from_chunks(chunks, count_per_chunk=1)
    assert len(candidates) == 1
    c = candidates[0]
    assert "Payment Service" in c.question
    assert "chk_002" in c.relevant_chunk_ids
    assert c.archetype == "conditional"


@pytest.mark.asyncio
async def test_synthetic_dataset_generator_with_mock_llm():
    """Verify LLM synthesis parses structured JSON arrays and pairs chunk IDs."""
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = """
    [
      {
        "question": "What is the token quota for starter tier?",
        "ground_truth_answer": "Starter tier comes with 250,000 monthly tokens.",
        "archetype": "factual"
      },
      {
        "question": "How does starter differ from growth tier in storage?",
        "ground_truth_answer": "Starter tier has 100MB while growth tier has 1GB storage.",
        "archetype": "multi_hop"
      }
    ]
    """

    generator = SyntheticDatasetGenerator(llm_provider=mock_llm)
    chunks = [{"chunk_id": "chk_llm_01", "content": "Tier specifications: Starter 250k, Growth 1.5M."}]

    candidates = await generator.synthesize_from_chunks(chunks, count_per_chunk=2)
    assert len(candidates) == 2
    assert candidates[0].question == "What is the token quota for starter tier?"
    assert candidates[0].relevant_chunk_ids == ["chk_llm_01"]
    assert candidates[1].archetype == "multi_hop"


def test_synthetic_dataset_format_dataset():
    """Verify formatting candidates into EvalDataset and EvalQuestion entities."""
    generator = SyntheticDatasetGenerator()
    chunks = [
        {"chunk_id": "chk_01", "content": "Vector similarity search uses Cosine Distance by default in pgvector."}
    ]
    candidates = generator._heuristic_generate("chk_01", chunks[0]["content"], count=1)
    dataset, questions = generator.format_dataset("tn_test", "Golden Benchmark v1", candidates)

    assert dataset.tenant_id == "tn_test"
    assert dataset.name == "Golden Benchmark v1"
    assert dataset.question_count == 1
    assert len(questions) == 1
    assert questions[0].dataset_id == dataset.dataset_id
    assert questions[0].relevant_chunk_ids == ["chk_01"]


# ── 2. API Tests: Admin Synthesis Endpoint ───────────────────────────────────

def test_admin_synthesize_dataset_endpoint():
    """Verify POST /v1/admin/tenants/{tenantId}/datasets/synthesize endpoint."""
    with patch("src.routers.admin.eval_dataset_repo") as mock_repo:
        mock_repo.create_dataset = AsyncMock()
        mock_repo.add_question = AsyncMock()

        response = client.post(
            "/v1/admin/tenants/00000000-0000-0000-0000-000000000000/datasets/synthesize",
            headers={"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY},
            json={
                "name": "API Synthesized Benchmark",
                "chunks": [
                    {
                        "chunk_id": "chk_synth_api",
                        "content": "Retriever Engine supports Hybrid Search combining BM25 keyword matching with dense nomic-embed vectors.",
                    }
                ],
                "count_per_chunk": 1,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "API Synthesized Benchmark"
        assert data["question_count"] == 1
        assert len(data["questions"]) == 1
        assert "Retriever Engine" in data["questions"][0]["question"]

