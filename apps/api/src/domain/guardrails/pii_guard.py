import re
from typing import Any


async def apply_pii_guard(query_text: str, guard: dict | Any) -> str:
    patterns = guard.get("patterns") if isinstance(guard, dict) else getattr(guard, "patterns", None)
    patterns = patterns or [
        r"\b\d{3}-\d{2}-\d{4}\b",
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    ]
    for pat in patterns:
        query_text = re.sub(pat, "[REDACTED]", query_text)
    return query_text
