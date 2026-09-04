"""Domain Abstractions for NeMo Guardrails & Multi-Turn Conversational Safety Rails (M94).

Defines pure domain entities, DTOs, and abstract interfaces for programmable Colang
flows, fast-path injection screening, and post-inference factual grounding.
Contains zero external framework, adapter, or database imports.
"""

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class GuardrailExecutionMode(StrEnum):
    """Operational mode controlling guardrail strictness and latency profile."""

    OFF = "off"
    FAST_INPUT_ONLY = "fast_input_only"  # Sub-20ms heuristic + injection scanner
    FULL_CONVERSATIONAL = "full_conversational"  # Fast-path + Colang flow execution
    STRICT_FACTUAL = "strict_factual"  # Full conversational + post-inference claim grounding


class GuardrailAction(StrEnum):
    """Action taken by the guardrail engine upon evaluation."""

    ALLOW = "allow"
    STEER = "steer"  # Divert conversation via Colang predefined bot response
    BLOCK = "block"  # Hard rejection (HTTP 400 or refusal text)
    MASK = "mask"  # Redact or sanitize prohibited entities (e.g. competitor names, PII)


class ColangFlowDefinition(BaseModel):
    """Represents a programmable Colang (.co) dialogue flow definition."""

    flow_id: str
    name: str
    description: str = ""
    user_intents: list[str] = Field(default_factory=list)
    bot_responses: list[str] = Field(default_factory=list)
    raw_colang: str = ""
    is_active: bool = True
    priority: int = 10  # Lower number = higher evaluation precedence


class GuardrailRule(BaseModel):
    """Specific guardrail behavioral policy or boundary constraint."""

    rule_id: str
    name: str
    category: str  # e.g., "safety", "scope", "brand", "grounding"
    description: str = ""
    action: GuardrailAction = GuardrailAction.BLOCK
    enabled: bool = True
    parameters: dict[str, Any] = Field(default_factory=dict)


class GuardrailViolation(BaseModel):
    """Detailed record of a detected security, scope, or factual violation."""

    violation_id: str
    tenant_id: str
    timestamp: str
    category: str
    matched_flow_or_rule: str
    action_taken: GuardrailAction
    query_excerpt: str
    severity: str = "medium"  # "low", "medium", "high", "critical"
    latency_ms: float = 0.0


class GuardrailCheckResult(BaseModel):
    """Result of evaluating an input prompt or output response against guardrails."""

    allowed: bool = True
    action: GuardrailAction = GuardrailAction.ALLOW
    reason: str = "Passed all active guardrail checks."
    rewritten_query: str | None = None
    bot_response: str | None = None
    matched_flow: str | None = None
    violations: list[GuardrailViolation] = Field(default_factory=list)
    latency_ms: float = 0.0
    grounding_score: float | None = None  # 0.0 - 1.0 confidence for factual checks


class TenantGuardrailsConfig(BaseModel):
    """Tenant-level configuration for NeMo conversational safety rails."""

    tenant_id: str
    mode: GuardrailExecutionMode = GuardrailExecutionMode.FULL_CONVERSATIONAL
    colang_script: str = ""
    active_flows: list[ColangFlowDefinition] = Field(default_factory=list)
    rules: list[GuardrailRule] = Field(default_factory=list)
    pii_redaction_enabled: bool = True
    competitor_shield_enabled: bool = True
    competitor_names: list[str] = Field(default_factory=list)
    brand_tone: str = "professional, objective, and factual"
    grounding_threshold: float = 0.70  # Min context entailment required in STRICT_FACTUAL
    fallback_response: str = "I am specifically scoped to assist with our platform services and documentation. How may I help you within that scope?"
    updated_at: str = ""


class INeMoGuardrailsAdapter(ABC):
    """Abstract interface (port) for the NeMo Guardrails engine."""

    @abstractmethod
    async def evaluate_input(
        self,
        tenant_id: str,
        query: str,
        config: TenantGuardrailsConfig,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> GuardrailCheckResult:
        """Evaluate a candidate user input query against fast-path and Colang rails."""
        pass

    @abstractmethod
    async def evaluate_output(
        self,
        tenant_id: str,
        query: str,
        generated_response: str,
        retrieved_contexts: list[str],
        config: TenantGuardrailsConfig,
    ) -> GuardrailCheckResult:
        """Evaluate generated assistant response for factual grounding and scope."""
        pass

    @abstractmethod
    def parse_colang_script(self, raw_script: str) -> list[ColangFlowDefinition]:
        """Parse raw Colang (.co) script into structured flow definitions."""
        pass
