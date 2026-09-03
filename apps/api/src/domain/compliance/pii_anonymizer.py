"""Enterprise Context-Aware PII Anonymization & Redaction Engine (Milestone 88).

Provides multi-category entity recognition, Luhn checksum validation, synthetic masking,
and cryptographic pseudonymization for HIPAA, GDPR, and SOC 2 compliance.
"""

import hashlib
import re
from typing import Any

from src.domain.abstractions.compliance import (
    MaskingMode,
    PiiCategory,
    PiiEntityMatch,
    PiiRedactionRequest,
    PiiRedactionResponse,
)


def luhn_checksum(card_number: str) -> bool:
    """Validate credit card number using Luhn algorithm to eliminate false positive matches."""
    digits = [int(c) for c in card_number if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = d * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += d
    return checksum % 10 == 0


# Enterprise regex patterns grouped by regulatory domain
ENTERPRISE_PII_DEFINITIONS: dict[str, dict[str, Any]] = {
    # ── Financial (PCI-DSS / AML) ──
    "credit_card": {
        "category": PiiCategory.FINANCIAL,
        "pattern": re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
        "validator": luhn_checksum,
    },
    "iban": {
        "category": PiiCategory.FINANCIAL,
        "pattern": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"),
    },
    "indian_ifsc": {
        "category": PiiCategory.FINANCIAL,
        "pattern": re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
    },

    # ── Identification (GDPR Art. 9 / KYC) ──
    "ssn": {
        "category": PiiCategory.IDENTIFICATION,
        "pattern": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    },
    "indian_aadhaar": {
        "category": PiiCategory.IDENTIFICATION,
        "pattern": re.compile(r"\b\d{4}[ -]\d{4}[ -]\d{4}\b"),
    },
    "indian_pan": {
        "category": PiiCategory.IDENTIFICATION,
        "pattern": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    },
    "passport": {
        "category": PiiCategory.IDENTIFICATION,
        "pattern": re.compile(r"\b[A-Z][0-9]{7,8}\b"),
    },

    # ── Secrets & Credentials (SOC 2 / Zero-Trust) ──
    "aws_access_key": {
        "category": PiiCategory.SECRETS,
        "pattern": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    },
    "openai_key": {
        "category": PiiCategory.SECRETS,
        "pattern": re.compile(r"\bsk-[a-zA-Z0-9_-]{20,}\b"),
    },
    "github_token": {
        "category": PiiCategory.SECRETS,
        "pattern": re.compile(r"\bghp_[a-zA-Z0-9]{36}\b"),
    },
    "jwt_token": {
        "category": PiiCategory.SECRETS,
        "pattern": re.compile(r"\beyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\b"),
    },
    "private_key_header": {
        "category": PiiCategory.SECRETS,
        "pattern": re.compile(r"-----BEGIN[ A-Z0-9_-]+PRIVATE KEY-----"),
    },

    # ── Network & Infrastructure ──
    "ipv4": {
        "category": PiiCategory.NETWORK,
        "pattern": re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"),
    },
    "mac_address": {
        "category": PiiCategory.NETWORK,
        "pattern": re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2})\b"),
    },

    # ── Health & Medical (HIPAA Safe Harbor) ──
    "medical_record_number": {
        "category": PiiCategory.HEALTH_HIPAA,
        "pattern": re.compile(r"\bMRN[ -]?[0-9]{6,10}\b", re.IGNORECASE),
    },

    # ── Contact Information ──
    "email": {
        "category": PiiCategory.CONTACT,
        "pattern": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    },
    "phone": {
        "category": PiiCategory.CONTACT,
        "pattern": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    },
}


class PiiAnonymizer:
    """Enterprise-grade PII and sensitive data redactor supporting multiple compliance masking modes."""

    def __init__(self) -> None:
        self.definitions = ENTERPRISE_PII_DEFINITIONS

    def _generate_mask(self, raw_value: str, entity_type: str, category: PiiCategory, mode: MaskingMode) -> str:
        if mode == MaskingMode.REDACT:
            return f"[REDACTED_{entity_type.upper()}]"

        if mode == MaskingMode.PSEUDONYMIZE:
            # Deterministic hash token allows consistent cross-document correlation without storing raw entity
            digest = hashlib.sha256(raw_value.strip().encode("utf-8")).hexdigest()[:8]
            return f"[PSEUDONYM:{digest}]"

        if mode == MaskingMode.SYNTHETIC:
            digits = "".join(c for c in raw_value if c.isdigit())
            if entity_type == "credit_card" and len(digits) >= 4:
                return f"****-****-****-{digits[-4:]}"
            if entity_type == "ssn" and len(digits) >= 4:
                return f"***-**-{digits[-4:]}"
            if entity_type == "email" and "@" in raw_value:
                parts = raw_value.split("@")
                return f"{parts[0][:2]}***@{parts[1]}"
            return f"[{entity_type.upper()}-MASKED]"

        return f"[REDACTED_{entity_type.upper()}]"

    def redact(self, request: PiiRedactionRequest) -> PiiRedactionResponse:
        """Full-featured enterprise redaction pipeline with non-overlapping interval scheduling."""
        text = request.text
        if not text:
            return PiiRedactionResponse(
                original_length=0,
                redacted_text="",
                entities_detected=[],
                total_redacted=0,
            )

        active_categories = set(request.categories) if request.categories else set(PiiCategory)
        raw_candidates: list[PiiEntityMatch] = []

        # 1. Process built-in entity definitions
        for entity_type, rule in self.definitions.items():
            category = rule["category"]
            if category not in active_categories:
                continue

            pattern: re.Pattern = rule["pattern"]
            validator = rule.get("validator")

            for match in pattern.finditer(text):
                val = match.group(0)
                if validator and not validator(val):
                    continue

                mask = self._generate_mask(val, entity_type, category, request.masking_mode)
                raw_candidates.append(
                    PiiEntityMatch(
                        category=category,
                        entity_type=entity_type,
                        original_value=val,
                        masked_value=mask,
                        start=match.start(),
                        end=match.end(),
                    )
                )

        # 2. Process custom patterns
        if request.custom_patterns:
            for i, raw_pat in enumerate(request.custom_patterns):
                try:
                    compiled = re.compile(raw_pat)
                    for match in compiled.finditer(text):
                        val = match.group(0)
                        mask = f"[REDACTED_CUSTOM_{i + 1}]"
                        raw_candidates.append(
                            PiiEntityMatch(
                                category=PiiCategory.CUSTOM,
                                entity_type=f"custom_{i + 1}",
                                original_value=val,
                                masked_value=mask,
                                start=match.start(),
                                end=match.end(),
                            )
                        )
                except Exception:
                    pass

        # 3. Non-overlapping Interval Selection: longer match wins
        raw_candidates.sort(key=lambda m: (m.end - m.start), reverse=True)
        selected_matches: list[PiiEntityMatch] = []
        occupied_spans: list[tuple[int, int]] = []

        for candidate in raw_candidates:
            overlaps = False
            for occ_start, occ_end in occupied_spans:
                if max(candidate.start, occ_start) < min(candidate.end, occ_end):
                    overlaps = True
                    break
            if not overlaps:
                selected_matches.append(candidate)
                occupied_spans.append((candidate.start, candidate.end))

        # 4. Sort selected matches backwards by start index to substitute safely
        selected_matches.sort(key=lambda m: m.start, reverse=True)

        redacted_text = text
        for m in selected_matches:
            redacted_text = redacted_text[: m.start] + m.masked_value + redacted_text[m.end :]

        # 5. Return matches in original document reading order
        selected_matches.sort(key=lambda m: m.start)

        return PiiRedactionResponse(
            original_length=len(text),
            redacted_text=redacted_text,
            entities_detected=selected_matches,
            total_redacted=len(selected_matches),
        )

    def anonymize_text(
        self,
        text: str,
        enabled_types: list[str] | None = None,
        custom_patterns: list[str] | None = None,
    ) -> str:
        """Backward-compatible entrypoint used during document chunking & ingestion."""
        res = self.redact(
            PiiRedactionRequest(
                text=text,
                masking_mode=MaskingMode.REDACT,
                custom_patterns=custom_patterns,
            )
        )
        return res.redacted_text
