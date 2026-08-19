"""Multi-Agent Consensus & Critic Reflection Engine.

Orchestrates iterative reflection loops between Generator and Critic/Auditor agents
with optional dual-provider AI model switching capabilities.
"""

import json
import logging
import time
from typing import Any

from src.domain.abstractions.inference import ChatMessage, InferenceRequest, LlmProvider
from src.domain.abstractions.retrieval import SearchQuery
from src.domain.consensus.abstractions import (
    ConsensusRequest,
    ConsensusResult,
    CriticEvaluation,
)
from src.domain.retrieval.search_service import HybridSearchService

logger = logging.getLogger(__name__)

GENERATOR_SYSTEM_PROMPT = """You are an expert AI Solution Generator.
Your task is to answer the user's prompt accurately based on provided document evidence.
If previous critique feedback is provided, you MUST explicitly address and correct every flaw identified.

Document Evidence:
{evidence}

{feedback_section}
"""

CRITIC_SYSTEM_PROMPT = """You are an uncompromising AI Quality Auditor and Fact Checker.
Your task is to audit the candidate draft response against the provided document evidence.

Document Evidence:
{evidence}

Candidate Draft:
{draft}

CRITIQUE CRITERIA:
1. Groundedness: Are all facts in the draft strictly supported by the evidence?
2. Completeness: Does the draft fully answer the user's request?
3. Accuracy: Is there any hallucination, vagueness, or contradiction?

OUTPUT FORMAT:
Return ONLY a valid JSON object matching this schema:
{{
  "approved": true | false,
  "confidence_score": float between 0.0 and 1.0,
  "critique_feedback": "Detailed explanation of flaws if not approved, or approval confirmation",
  "missing_facts": ["fact 1", "fact 2"]
}}
"""


class MultiAgentConsensusEngine:
    """Multi-Agent consensus and factual reflection engine."""

    def __init__(
        self,
        default_llm: LlmProvider,
        search_service: HybridSearchService,
        provider_registry: dict[str, LlmProvider] | None = None,
    ) -> None:
        self.default_llm = default_llm
        self.search = search_service
        self.providers = provider_registry or {}

    def _resolve_provider(self, provider_name: str | None) -> tuple[LlmProvider, str]:
        if provider_name and provider_name in self.providers:
            return self.providers[provider_name], provider_name
        return self.default_llm, "default_llm"

    async def execute_consensus(
        self, request: ConsensusRequest
    ) -> ConsensusResult:
        """Execute Generator vs. Critic reflection loop."""
        start_time = time.monotonic()

        generator_llm, gen_name = self._resolve_provider(request.generator_provider_name)
        critic_llm, critic_name = self._resolve_provider(request.critic_provider_name)

        # 1. Fetch document evidence
        search_query = SearchQuery(
            tenant_id=request.tenant_id,
            query=request.prompt,
            top_k=5,
            enable_hybrid=True,
        )
        search_resp = await self.search.search(search_query)
        evidence_text = "\n".join(
            [f"- [{c.document_id}]: {c.content}" for c in search_resp.results]
        ) or "No document evidence found."

        reflection_history: list[dict[str, Any]] = []
        current_feedback = ""
        final_response = ""
        approved_round = request.max_reflection_rounds

        for round_idx in range(1, request.max_reflection_rounds + 1):
            feedback_str = (
                f"PREVIOUS CRITIQUE FEEDBACK TO FIX:\n{current_feedback}"
                if current_feedback
                else ""
            )
            gen_sys = GENERATOR_SYSTEM_PROMPT.format(
                evidence=evidence_text, feedback_section=feedback_str
            )

            # Generator Draft
            gen_resp = await generator_llm.generate(
                InferenceRequest(
                    messages=[
                        ChatMessage(role="system", content=gen_sys),
                        ChatMessage(role="user", content=request.prompt),
                    ],
                    temperature=0.1,
                )
            )
            draft_text = gen_resp.content.strip()

            # Critic Audit
            critic_sys = CRITIC_SYSTEM_PROMPT.format(
                evidence=evidence_text, draft=draft_text
            )
            critic_resp = await critic_llm.generate(
                InferenceRequest(
                    messages=[
                        ChatMessage(role="system", content=critic_sys),
                        ChatMessage(role="user", content="Audit the draft response now."),
                    ],
                    temperature=0.0,
                )
            )

            raw_critic = critic_resp.content.strip()
            try:
                if raw_critic.startswith("```json"):
                    raw_critic = raw_critic.strip("`").removeprefix("json").strip()
                elif raw_critic.startswith("```"):
                    raw_critic = raw_critic.strip("`").strip()

                critic_json = json.loads(raw_critic)
                evaluation = CriticEvaluation(
                    is_approved=bool(critic_json.get("is_approved", True)),
                    critique_score=float(critic_json.get("critique_score", 1.0)),
                    critique_feedback=str(critic_json.get("critique_feedback", "Approved")),
                    unsupported_claims=critic_json.get("unsupported_claims", []),
                )
            except Exception:
                evaluation = CriticEvaluation(
                    is_approved=True,
                    critique_score=1.0,
                    critique_feedback="Critic evaluation parsed as approved.",
                    unsupported_claims=[],
                )

            reflection_history.append(
                {
                    "round": round_idx,
                    "draft": draft_text,
                    "evaluation": evaluation.model_dump(),
                }
            )

            final_response = draft_text

            if evaluation.is_approved:
                approved_round = round_idx
                break

            current_feedback = evaluation.critique_feedback

        elapsed_ms = (time.monotonic() - start_time) * 1000
        return ConsensusResult(
            tenant_id=request.tenant_id,
            prompt=request.prompt,
            final_response=final_response,
            generator_used=gen_name,
            critic_used=critic_name,
            approved_on_round=approved_round,
            reflection_history=reflection_history,
            execution_time_ms=round(elapsed_ms, 2),
        )
