"""Smart Tool Gateway & Multi-Model Economic Orchestrator (M105).

Provides:
- Task complexity classification (evaluating tool dependency depth & cognitive hurdles).
- Mid-flight escalation detection from mid-tier to frontier models.
- Real-time economic ledger accounting comparing actual spend vs counterfactual frontier costs.
"""

import re
from collections import defaultdict

from src.domain.abstractions.economic_orchestrator import (
    EconomicLedgerRecord,
    EconomicLedgerSummary,
    EconomicOrchestratorProtocol,
    EscalationReason,
    ModelTier,
    TaskComplexity,
)

# Blended token costs per token (USD)
DEFAULT_RATES: dict[str, float] = {
    "mid_tier": 0.00015 / 1.0,   # ~$0.15 per 1K tokens (~Gemini 2.5 Flash / GPT-4o-mini blended)
    "frontier": 0.005 / 1.0,     # ~$5.00 per 1K tokens (~Claude 3.5 Sonnet / GPT-4o blended)
}

# Model identifiers by tier
DEFAULT_TIER_MODELS: dict[ModelTier, str] = {
    ModelTier.MID_TIER: "gemini-2.5-flash",
    ModelTier.FRONTIER: "anthropic/claude-3-5-sonnet-20240620",
}


class SmartToolRouter(EconomicOrchestratorProtocol):
    """Orchestrates multi-model execution, mid-flight thread escalation, and savings ledger."""

    def __init__(
        self,
        rates: dict[str, float] | None = None,
        tier_models: dict[ModelTier, str] | None = None,
        max_ledger_history_per_tenant: int = 500,
    ) -> None:
        self.rates = rates or DEFAULT_RATES
        self.tier_models = tier_models or DEFAULT_TIER_MODELS
        self.max_history = max_ledger_history_per_tenant
        self._tenant_records: dict[str, list[EconomicLedgerRecord]] = defaultdict(list)

    def get_model_for_tier(self, tier: ModelTier) -> str:
        """Return the default concrete model ID for a given tier."""
        return self.tier_models.get(tier, self.tier_models[ModelTier.MID_TIER])

    def classify_complexity(self, query: str, allowed_tools: list[str] | None = None) -> TaskComplexity:
        """Analyze query and tool capabilities to assign complexity score and tier."""
        q_lower = query.lower()
        score = 0.25
        rationale_parts: list[str] = []

        # 1. Length heuristic
        word_count = len(query.split())
        if word_count > 60:
            score += 0.20
            rationale_parts.append("extended context length")
        elif word_count > 30:
            score += 0.10
            rationale_parts.append("multi-sentence prompt")

        # 2. Code & Programming Indicators
        code_patterns = [r"\bdef\b", r"\bclass\b", r"\bimport\b", r"\bscript\b", r"\bpython\b", r"\bcode\b", r"\bdebug\b", r"\brepl\b"]
        has_code = bool(any(re.search(pat, q_lower) for pat in code_patterns) or ("python_sandbox" in (allowed_tools or [])))
        if has_code:
            score += 0.45
            rationale_parts.append("code execution / debugging")

        # 3. Multi-hop Reasoning & Forensic Indicators
        multi_hop_patterns = [r"\bcompare\b", r"\bcontrast\b", r"\bdifference between\b", r"\bforensic\b", r"\breconcile\b", r"\bcorrelation\b", r"\bverify all\b"]
        has_multi_hop = bool(any(re.search(pat, q_lower) for pat in multi_hop_patterns))
        if has_multi_hop:
            score += 0.30
            rationale_parts.append("multi-hop cross-referencing")

        # 4. Mathematical Synthesis Indicators
        math_patterns = [r"\bcalculate\b", r"\bformula\b", r"\bestimate cost\b", r"\bcompound\b", r"\bfinancial\b", r"\bmath\b"]
        has_math = bool(any(re.search(pat, q_lower) for pat in math_patterns))
        if has_math:
            score += 0.25
            rationale_parts.append("mathematical synthesis")

        # 5. Routine single lookup discount
        simple_patterns = [r"^(what is|who is|where is|summarize|list the)\b", r"\bquick question\b"]
        if any(re.search(pat, q_lower) for pat in simple_patterns) and not (has_code or has_multi_hop or has_math):
            score -= 0.10
            rationale_parts.append("standard direct information lookup")

        # Clamp normalized score
        final_score = max(0.05, min(0.99, round(score, 2)))
        tier = ModelTier.FRONTIER if final_score > 0.65 else ModelTier.MID_TIER
        estimated_steps = 1 if final_score < 0.35 else (2 if final_score <= 0.65 else 4)

        rationale = f"Assigned {tier.value.upper()} (score: {final_score:.2f}) based on: " + (", ".join(rationale_parts) if rationale_parts else "standard RAG query depth")

        return TaskComplexity(
            score=final_score,
            tier_assigned=tier,
            estimated_steps=estimated_steps,
            rationale=rationale,
            requires_code_execution=has_code,
            requires_multi_hop=has_multi_hop,
            requires_mathematical_synthesis=has_math,
        )

    def should_escalate(
        self,
        current_tier: ModelTier,
        step_index: int,
        last_tool_error: bool = False,
        self_healing_attempted: bool = False,
        circuit_breaker_tripped: bool = False,
    ) -> tuple[bool, EscalationReason | None, str]:
        """Evaluate whether mid-tier execution should escalate to frontier tier."""
        if current_tier == ModelTier.FRONTIER:
            return False, None, ""

        if circuit_breaker_tripped:
            return (
                True,
                EscalationReason.CIRCUIT_BREAKER_WARNING,
                "Circuit breaker tripped due to repetitive tool execution. Escalating to frontier model to rethink approach.",
            )

        if last_tool_error and self_healing_attempted:
            return (
                True,
                EscalationReason.SELF_HEALING_FAILED,
                "Tool execution exception persisted after self-healing diagnostic. Escalating to frontier model for recovery.",
            )

        if step_index >= 3:
            return (
                True,
                EscalationReason.STEP_COUNT_THRESHOLD,
                f"Iteration threshold reached ({step_index} steps). Escalating to frontier model for final comprehensive synthesis.",
            )

        return False, None, ""

    def record_transaction(
        self,
        tenant_id: str,
        thread_id: str,
        query: str,
        mid_tier_tokens: int,
        frontier_tokens: int,
        mid_tier_model: str,
        frontier_model: str,
        escalated: bool = False,
        escalation_reason: EscalationReason | None = None,
    ) -> EconomicLedgerRecord:
        """Compute costs and persist transaction in tenant economic ledger."""
        rate_mid = self.rates.get("mid_tier", DEFAULT_RATES["mid_tier"])
        rate_front = self.rates.get("frontier", DEFAULT_RATES["frontier"])

        total_tokens = mid_tier_tokens + frontier_tokens
        actual_cost = round((mid_tier_tokens * rate_mid) + (frontier_tokens * rate_front), 6)
        counterfactual_cost = round(total_tokens * rate_front, 6)
        net_savings = max(0.0, round(counterfactual_cost - actual_cost, 6))

        savings_pct = (
            round((net_savings / counterfactual_cost) * 100.0, 2)
            if counterfactual_cost > 0
            else 0.0
        )

        record = EconomicLedgerRecord(
            tenant_id=tenant_id,
            thread_id=thread_id,
            query_preview=query[:80] + ("..." if len(query) > 80 else ""),
            mid_tier_tokens=mid_tier_tokens,
            frontier_tokens=frontier_tokens,
            total_tokens=total_tokens,
            actual_cost_usd=actual_cost,
            counterfactual_frontier_cost_usd=counterfactual_cost,
            net_savings_usd=net_savings,
            savings_percentage=savings_pct,
            escalated=escalated,
            escalation_reason=escalation_reason,
        )

        history = self._tenant_records[tenant_id]
        history.append(record)
        if len(history) > self.max_history:
            self._tenant_records[tenant_id] = history[-self.max_history:]

        return record

    def get_ledger_summary(self, tenant_id: str) -> EconomicLedgerSummary:
        """Compute aggregate economic savings, allocation ratio, and escalation rate."""
        records = self._tenant_records.get(tenant_id, [])

        if not records:
            return EconomicLedgerSummary(
                tenant_id=tenant_id,
                total_queries=0,
                total_tokens=0,
                mid_tier_query_count=0,
                frontier_query_count=0,
                escalated_query_count=0,
                mid_tier_share_percentage=85.0,  # Baseline expectation
                escalation_rate_percentage=0.0,
                total_actual_cost_usd=0.0,
                total_counterfactual_cost_usd=0.0,
                total_savings_usd=0.0,
                average_savings_percentage=0.0,
                records=[],
            )

        total_queries = len(records)
        total_tokens = sum(r.total_tokens for r in records)
        mid_tier_queries = sum(1 for r in records if r.mid_tier_tokens > 0 and not r.frontier_tokens)
        frontier_queries = sum(1 for r in records if r.frontier_tokens > 0 and not r.mid_tier_tokens)
        escalated_queries = sum(1 for r in records if r.escalated)

        # Workload share: queries that started on mid-tier
        mid_tier_started = sum(1 for r in records if r.mid_tier_tokens > 0)
        mid_share = round((mid_tier_started / total_queries) * 100.0, 1) if total_queries > 0 else 0.0
        escalation_rate = round((escalated_queries / total_queries) * 100.0, 1) if total_queries > 0 else 0.0

        total_actual = round(sum(r.actual_cost_usd for r in records), 4)
        total_counterfactual = round(sum(r.counterfactual_frontier_cost_usd for r in records), 4)
        total_savings = max(0.0, round(total_counterfactual - total_actual, 4))
        avg_savings_pct = (
            round((total_savings / total_counterfactual) * 100.0, 1)
            if total_counterfactual > 0
            else 0.0
        )

        return EconomicLedgerSummary(
            tenant_id=tenant_id,
            total_queries=total_queries,
            total_tokens=total_tokens,
            mid_tier_query_count=mid_tier_queries,
            frontier_query_count=frontier_queries,
            escalated_query_count=escalated_queries,
            mid_tier_share_percentage=mid_share,
            escalation_rate_percentage=escalation_rate,
            total_actual_cost_usd=total_actual,
            total_counterfactual_cost_usd=total_counterfactual,
            total_savings_usd=total_savings,
            average_savings_percentage=avg_savings_pct,
            records=records[-20:],  # Return latest 20 for preview
        )
