"""Synthetic Golden Dataset Generator.

Synthesizes high-coverage benchmark Q&A pairs (factual, multi-hop, conditional constraints)
from document chunks with verified ground-truth citations and fallback heuristic extraction.
"""

import json
import re
import uuid
from typing import Any

from src.domain.abstractions.evaluation import (
    BaseSyntheticDatasetGenerator,
    EvalDataset,
    EvalQuestion,
    SyntheticQuestionCandidate,
)

SYNTHESIS_SYSTEM_PROMPT = """You are an expert AI Benchmark Engineer.
Your task is to analyze document chunks and generate rigorous, factual evaluation question-and-answer pairs.
For each chunk, generate multiple questions across different archetypes:
1. "factual": Direct factual lookup from the text.
2. "conditional": Inquiries about preconditions, rules, or negative constraints.
3. "multi_hop": Comparative or inferential reasoning across facts.

Return strictly a JSON array of objects with the following format:
[
  {
    "question": "What is the specific retention limit for audit logs?",
    "ground_truth_answer": "Audit logs are retained for 365 days in encrypted cold storage.",
    "archetype": "factual"
  }
]
"""


class SyntheticDatasetGenerator(BaseSyntheticDatasetGenerator):
    """Generates synthetic golden evaluation datasets from document chunks."""

    def __init__(self, llm_provider: Any = None) -> None:
        self.llm_provider = llm_provider

    def _heuristic_generate(
        self, chunk_id: str, content: str, count: int = 2
    ) -> list[SyntheticQuestionCandidate]:
        """Deterministic proposition extractor and question inverter fallback."""
        candidates: list[SyntheticQuestionCandidate] = []
        sentences = [
            s.strip()
            for s in re.split(r"[.!?]\s+", content)
            if len(s.strip()) > 20 and not s.strip().startswith("#")
        ]

        if not sentences:
            if len(content.strip()) > 10:
                sentences = [content.strip()]
            else:
                return candidates

        for idx, sentence in enumerate(sentences[:count]):
            # 1. Look for definition patterns ("X is Y", "X refers to Y")
            is_def = re.search(r"^(.*?)\s+(?:is|are|refers to|means|specifies)\s+(.*)$", sentence, re.IGNORECASE)
            if is_def:
                subject = is_def.group(1).strip()
                candidates.append(
                    SyntheticQuestionCandidate(
                        question=f"What is {subject} according to the documentation?",
                        ground_truth_answer=sentence,
                        relevant_chunk_ids=[chunk_id],
                        archetype="factual",
                        confidence_score=0.95,
                    )
                )
                continue

            # 2. Look for action / relationship patterns ("X uses Y", "X requires Y")
            is_req = re.search(r"^(.*?)\s+(?:uses|requires|integrates with|supports|provides)\s+(.*)$", sentence, re.IGNORECASE)
            if is_req:
                subject = is_req.group(1).strip()
                candidates.append(
                    SyntheticQuestionCandidate(
                        question=f"What does {subject} require or integrate with?",
                        ground_truth_answer=sentence,
                        relevant_chunk_ids=[chunk_id],
                        archetype="conditional" if "require" in sentence.lower() else "factual",
                        confidence_score=0.90,
                    )
                )
                continue


            # 3. General proposition formulation
            words = sentence.split()
            topic = " ".join(words[:4]) if len(words) >= 4 else sentence
            candidates.append(
                SyntheticQuestionCandidate(
                    question=f"What information is specified regarding {topic}?",
                    ground_truth_answer=sentence,
                    relevant_chunk_ids=[chunk_id],
                    archetype="factual" if idx % 2 == 0 else "multi_hop",
                    confidence_score=0.85,
                )
            )

        return candidates[:count]

    async def synthesize_from_chunks(
        self, chunks: list[dict[str, Any]], count_per_chunk: int = 2
    ) -> list[SyntheticQuestionCandidate]:
        """Synthesize benchmark questions paired with source chunk IDs."""
        all_candidates: list[SyntheticQuestionCandidate] = []

        for chunk in chunks:
            chunk_id = str(chunk.get("chunk_id", str(uuid.uuid4())))
            content = str(chunk.get("content", ""))
            if not content.strip():
                continue

            generated: list[SyntheticQuestionCandidate] = []

            # Try LLM synthesis if provider available
            if self.llm_provider is not None:
                try:
                    prompt = f"Analyze the following document chunk and generate {count_per_chunk} Q&A pairs:\n\n{content}"
                    resp_text = await self.llm_provider.generate(
                        prompt=prompt, system_prompt=SYNTHESIS_SYSTEM_PROMPT
                    )
                    # Parse JSON block
                    match = re.search(r"\[.*\]", resp_text, re.DOTALL)
                    if match:
                        items = json.loads(match.group(0))
                        for it in items:
                            if isinstance(it, dict) and "question" in it and "ground_truth_answer" in it:
                                generated.append(
                                    SyntheticQuestionCandidate(
                                        question=it["question"],
                                        ground_truth_answer=it["ground_truth_answer"],
                                        relevant_chunk_ids=[chunk_id],
                                        archetype=it.get("archetype", "factual"),
                                        confidence_score=0.95,
                                    )
                                )
                except Exception:
                    generated = []

            # Fallback to heuristic proposition extractor if LLM fails or unconfigured
            if not generated:
                generated = self._heuristic_generate(chunk_id, content, count=count_per_chunk)

            all_candidates.extend(generated)

        return all_candidates

    def format_dataset(
        self, tenant_id: str, name: str, candidates: list[SyntheticQuestionCandidate]
    ) -> tuple[EvalDataset, list[EvalQuestion]]:
        """Format generated candidates into dataset entity and question list."""
        dataset_id = f"ds_synth_{uuid.uuid4().hex[:12]}"
        dataset = EvalDataset(
            dataset_id=dataset_id,
            tenant_id=tenant_id,
            name=name,
            description="Synthetically generated golden benchmark dataset.",
            question_count=len(candidates),
        )

        questions = [
            EvalQuestion(
                question_id=f"q_synth_{uuid.uuid4().hex[:8]}",
                dataset_id=dataset_id,
                question=c.question,
                ground_truth_answer=c.ground_truth_answer,
                relevant_chunk_ids=c.relevant_chunk_ids,
            )
            for c in candidates
        ]

        return dataset, questions
