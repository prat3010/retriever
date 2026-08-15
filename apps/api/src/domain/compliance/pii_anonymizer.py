"""Domain service for zero-footprint inline PII anonymization during document ingestion."""

import re

DEFAULT_PII_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
}


class PiiAnonymizer:
    """Anonymizes personally identifiable information (PII) from document text before chunking."""

    def anonymize_text(
        self,
        text: str,
        enabled_types: list[str] | None = None,
        custom_patterns: list[str] | None = None,
    ) -> str:
        """Replace sensitive PII tokens with redaction placeholders."""
        if not text:
            return ""

        redacted_text = text
        types_to_mask = enabled_types or list(DEFAULT_PII_PATTERNS.keys())

        for pii_type in types_to_mask:
            pattern = DEFAULT_PII_PATTERNS.get(pii_type)
            if pattern:
                placeholder = f"[REDACTED_{pii_type.upper()}]"
                redacted_text = pattern.sub(placeholder, redacted_text)

        if custom_patterns:
            for i, raw_pattern in enumerate(custom_patterns):
                try:
                    compiled = re.compile(raw_pattern)
                    redacted_text = compiled.sub(f"[REDACTED_CUSTOM_{i+1}]", redacted_text)
                except Exception:
                    pass

        return redacted_text
