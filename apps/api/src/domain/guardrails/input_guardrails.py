"""Domain guardrail pipeline service."""

from collections.abc import Awaitable, Callable
from typing import Any

from src.domain.abstractions.config import TenantConfiguration
from src.domain.guardrails.pii_guard import apply_pii_guard

SafetyGuardFn = Callable[[str, dict[str, Any], TenantConfiguration], Awaitable[str]]


async def apply_input_guardrails(
    tenant_config: TenantConfiguration,
    query_text: str,
    llm_safety_fn: SafetyGuardFn | None = None,
) -> str:
    """Apply configured input guardrails to query text."""
    for guard in tenant_config.guardrails:
        guard_type = (
            guard.get("guard_type")
            if isinstance(guard, dict)
            else getattr(guard, "guard_type", None)
        )
        if guard_type == "pii_regex":
            query_text = await apply_pii_guard(query_text, guard)
        elif guard_type == "llm_safety" and llm_safety_fn is not None:
            query_text = await llm_safety_fn(query_text, guard, tenant_config)
    return query_text
