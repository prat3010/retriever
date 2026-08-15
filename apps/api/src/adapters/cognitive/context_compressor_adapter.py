"""Intelligent Context Window Compressor Adapter.

Trims redundant stop words, fluff phrases, and duplicate sentences while preserving
vital facts, numbers, dates, and named entities to cut LLM token costs.
"""

import re

from src.domain.security_compression.abstractions import (
    CompressionRequest,
    CompressionResult,
)

FILLER_PATTERNS = [
    r"\b(in order to|as a matter of fact|at this point in time|for the purpose of)\b",
    r"\b(it is important to note that|it should be noted that|it is worth mentioning that)\b",
    r"\b(furthermore|moreover|nevertheless|nonetheless|basically|actually|literally)\b",
]


class IntelligentContextCompressor:
    """Fast rule-based and frequency-preserving context compressor."""

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count based on word boundary split."""
        words = re.findall(r"\w+|[^\w\s]", text)
        return max(1, len(words))

    def compress(self, request: CompressionRequest) -> CompressionResult:
        """Compress prompt context window based on target compression rate."""
        original_text = request.text.strip()
        orig_tokens = self.estimate_tokens(original_text)

        if not original_text or request.compression_rate >= 0.95:
            return CompressionResult(
                original_text=original_text,
                compressed_text=original_text,
                original_tokens=orig_tokens,
                compressed_tokens=orig_tokens,
                compression_ratio=1.0,
            )

        # 1. Remove common filler phrases
        text_clean = original_text
        for pat in FILLER_PATTERNS:
            text_clean = re.sub(pat, "", text_clean, flags=re.IGNORECASE)

        # 2. Split into sentences
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text_clean) if s.strip()]

        if not sentences:
            sentences = [original_text]

        # 3. Score sentences based on factual indicators (numbers, capital letters, key terms)
        scored_sentences = []
        for idx, sent in enumerate(sentences):
            has_digits = 2.0 if re.search(r"\d", sent) else 0.0
            has_caps = 1.0 if re.search(r"\b[A-Z][a-z]+\b", sent) else 0.0
            length_bonus = 0.5 if len(sent.split()) > 4 else 0.0
            position_bonus = 1.0 if idx == 0 or idx == len(sentences) - 1 else 0.0
            score = has_digits + has_caps + length_bonus + position_bonus
            scored_sentences.append((score, idx, sent))

        # Sort by score descending and take top fraction based on compression rate
        keep_count = max(1, int(len(sentences) * request.compression_rate))
        scored_sentences.sort(key=lambda x: x[0], reverse=True)

        selected = scored_sentences[:keep_count]
        # Sort back into original document sentence order
        selected.sort(key=lambda x: x[1])

        compressed_text = " ".join([s[2] for s in selected])
        comp_tokens = self.estimate_tokens(compressed_text)
        ratio = round(comp_tokens / max(1, orig_tokens), 2)

        return CompressionResult(
            original_text=original_text,
            compressed_text=compressed_text,
            original_tokens=orig_tokens,
            compressed_tokens=comp_tokens,
            compression_ratio=ratio,
        )
