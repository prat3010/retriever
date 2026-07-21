from typing import Any

from src.adapters.guardrails.llm_safety_guard import apply_llm_safety_guard
from src.domain.abstractions.config import TenantConfiguration
from src.domain.guardrails.pii_guard import apply_pii_guard


async def apply_input_guardrails(tenant_config: TenantConfiguration, query_text: str) -> str:
    for guard in tenant_config.guardrails:
        guard_type = guard.get("guard_type") if isinstance(guard, dict) else getattr(guard, "guard_type", None)
        if guard_type == "pii_regex":
            query_text = await apply_pii_guard(query_text, guard)
        elif guard_type == "llm_safety":
            query_text = await apply_llm_safety_guard(query_text, guard, tenant_config)
    return query_text
