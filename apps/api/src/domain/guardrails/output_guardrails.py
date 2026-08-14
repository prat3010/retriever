"""Domain output guardrail pipeline service."""

import re
from typing import Any

from src.domain.abstractions.config import TenantConfiguration

# Patterns for scrubbing sensitive PII and API keys from model output
PII_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED SSN]"),
    (re.compile(r"\b(?:\d[ -]*?){13,16}\b"), "[REDACTED CREDIT CARD]"),
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "[REDACTED API KEY]"),
    (re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE), "Bearer [REDACTED TOKEN]"),
]


def redact_output_pii(text: str) -> str:
    """Scrub sensitive PII patterns from generated LLM text."""
    clean_text = text
    for pattern, replacement in PII_PATTERNS:
        clean_text = pattern.sub(replacement, clean_text)
    return clean_text


async def apply_output_guardrails(
    text: str,
    tenant_config: TenantConfiguration,
    output_safety_fn: Any | None = None,
) -> str:
    """Apply configured output guardrails to generated text."""
    if not text:
        return text

    clean_text = redact_output_pii(text)

    if output_safety_fn is not None:
        clean_text = await output_safety_fn(clean_text, tenant_config)

    return clean_text
