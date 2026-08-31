"""Tier 2 Structured Small Language Model (SLM) Judge Engine.

Provides deep claim-by-claim verification, grounded citation span localization,
and structured JSON reasoning reports using local Ollama or lightweight LLM judges.
"""

import json
import re
import time
from typing import Any

from src.domain.abstractions.evaluation import (
    BaseSlmJudge,
    SlmClaimAnalysis,
    SlmJudgeResult,
)
from src.domain.evaluation.nli_evaluator import NliEvaluator


class SlmJudgeEngine(BaseSlmJudge):
    """Tier 2 Structured SLM Judge evaluating factual grounding with span localization."""

    def __init__(self, nli_evaluator: NliEvaluator | None = None) -> None:
        self.nli_evaluator = nli_evaluator or NliEvaluator()

    async def judge_response(
        self, query: str, answer: str, contexts: list[str], llm_provider: Any = None
    ) -> SlmJudgeResult:
        """Evaluate factual grounding and return structured JSON verdict with claim reasoning."""
        start_time = time.monotonic()

        if not answer or not answer.strip():
            return SlmJudgeResult(
                verdict="FAIL",
                faithfulness_score=0.0,
                claim_analyses=[],
                reasoning="Empty generated answer.",
                latency_ms=0.0,
            )

        # 1. Attempt LLM/SLM Structured Evaluation if provider is passed
        if llm_provider is not None:
            try:
                result = await self._call_slm_provider(query, answer, contexts, llm_provider)
                if result is not None:
                    elapsed = (time.monotonic() - start_time) * 1000
                    result.latency_ms = round(elapsed, 2)
                    return result
            except Exception:
                # Fall back to NLI-driven deterministic structural judge
                pass

        # 2. Fallback Deterministic Structural Judge using NLI Evaluator
        fallback_result = self._generate_structural_judge_result(query, answer, contexts)
        elapsed = (time.monotonic() - start_time) * 1000
        fallback_result.latency_ms = round(elapsed, 2)
        return fallback_result

    async def _call_slm_provider(
        self, query: str, answer: str, contexts: list[str], llm_provider: Any
    ) -> SlmJudgeResult | None:
        """Prompt Small Language Model for structured claim-by-claim evaluation."""
        formatted_contexts = "\n\n".join(
            f"[Context {i+1}]: {c}" for i, c in enumerate(contexts[:5])
        )

        prompt = (
            "You are a strict, impartial Fact-Checking Judge. Evaluate whether every claim in the Answer is strictly supported by the Provided Contexts.\n\n"
            f"User Query: {query}\n\n"
            f"Provided Contexts:\n{formatted_contexts}\n\n"
            f"Candidate Answer:\n{answer}\n\n"
            "Respond ONLY with a valid JSON object matching this exact schema:\n"
            "{\n"
            '  "verdict": "PASS" | "FAIL" | "PARTIAL",\n'
            '  "faithfulness_score": 0.0 to 1.0,\n'
            '  "reasoning": "summary explanation",\n'
            '  "claim_analyses": [\n'
            '    {\n'
            '      "claim": "exact sentence claim",\n'
            '      "status": "supported" | "unsupported" | "contradicted",\n'
            '      "evidence_span": "verbatim text quote from context or empty",\n'
            '      "confidence": 0.0 to 1.0,\n'
            '      "rationale": "explanation of verification"\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        raw_resp = ""
        if hasattr(llm_provider, "generate"):
            raw_resp = await llm_provider.generate(prompt)
        elif hasattr(llm_provider, "complete"):
            raw_resp = await llm_provider.complete(prompt)
        elif hasattr(llm_provider, "chat"):
            raw_resp = await llm_provider.chat([{"role": "user", "content": prompt}])

        raw_str = str(raw_resp) if raw_resp else ""
        return self._parse_json_response(raw_str)

    def _parse_json_response(self, raw_text: str) -> SlmJudgeResult | None:
        """Extract and parse structured JSON verdict from model response text."""
        if not raw_text or not raw_text.strip():
            return None

        # Strip markdown fences if present
        cleaned = re.sub(r"```json\s*", "", raw_text)
        cleaned = re.sub(r"```\s*$", "", cleaned).strip()

        # Find JSON object boundaries
        json_match = re.search(r"\{[\s\S]*\}", cleaned)
        if not json_match:
            return None

        try:
            data = json.loads(json_match.group(0))
            analyses = []
            for item in data.get("claim_analyses", []):
                analyses.append(
                    SlmClaimAnalysis(
                        claim=item.get("claim", ""),
                        status=item.get("status", "unsupported"),
                        evidence_span=item.get("evidence_span", ""),
                        confidence=float(item.get("confidence", 1.0)),
                        rationale=item.get("rationale", ""),
                    )
                )

            return SlmJudgeResult(
                verdict=data.get("verdict", "PARTIAL"),
                faithfulness_score=float(data.get("faithfulness_score", 0.5)),
                claim_analyses=analyses,
                reasoning=data.get("reasoning", "SLM structured evaluation complete."),
            )
        except Exception:
            return None

    def _generate_structural_judge_result(
        self, query: str, answer: str, contexts: list[str]
    ) -> SlmJudgeResult:
        """Generate deterministic fallback verification report using NLI analysis."""
        claims = self.nli_evaluator.extract_claims(answer)
        nli_res = self.nli_evaluator.evaluate_claims(claims, contexts)

        claim_analyses: list[SlmClaimAnalysis] = []
        for c in nli_res.classifications:
            if c.status == "entailment":
                status = "supported"
                span = c.premise[:120] + "..." if len(c.premise) > 120 else c.premise
                conf = c.entailment_prob
                rationale = "Claim is grounded in context premise with consistent polarity."
            elif c.status == "contradiction":
                status = "contradicted"
                span = c.premise[:120] + "..." if len(c.premise) > 120 else c.premise
                conf = c.contradiction_prob
                rationale = "Claim directly contradicts statement in retrieved context."
            else:
                status = "unsupported"
                span = ""
                conf = c.neutral_prob
                rationale = "No direct supporting evidence found in retrieved chunks."

            claim_analyses.append(
                SlmClaimAnalysis(
                    claim=c.claim,
                    status=status,
                    evidence_span=span,
                    confidence=conf,
                    rationale=rationale,
                )
            )

        if nli_res.contradicted_claims > 0:
            verdict = "FAIL"
            reasoning = f"Answer contains {nli_res.contradicted_claims} contradicted claims violating context facts."
        elif nli_res.faithfulness_score >= 0.80:
            verdict = "PASS"
            reasoning = f"Answer is highly faithful ({nli_res.faithfulness_score * 100:.1f}%) with {nli_res.entailed_claims}/{nli_res.total_claims} verified claims."
        else:
            verdict = "PARTIAL"
            reasoning = f"Answer has partial support ({nli_res.faithfulness_score * 100:.1f}%) with {nli_res.neutral_claims} ungrounded claims."

        return SlmJudgeResult(
            verdict=verdict,
            faithfulness_score=nli_res.faithfulness_score,
            claim_analyses=claim_analyses,
            reasoning=reasoning,
        )
