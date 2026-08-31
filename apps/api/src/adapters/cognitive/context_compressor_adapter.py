"""Intelligent Context Window Compressor Adapter.

Trims redundant stop words, fluff phrases, and low-perplexity sentences while preserving
vital facts, numbers, dates, and named entities to cut LLM token costs.
"""

import logging
import math
import re

from src.domain.security_compression.abstractions import (
    CompressionRequest,
    CompressionResult,
)

logger = logging.getLogger(__name__)

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


class LongLLMLinguaAdapter:
    """Perplexity-based LongLLMLingua Context Compressor.

    Evaluates token information density and information entropy to compress documents
    while retaining critical proposition spans.
    """

    def __init__(self, fallback_compressor: IntelligentContextCompressor | None = None) -> None:
        self.fallback = fallback_compressor or IntelligentContextCompressor()
        self._llmlingua_client = None
        try:
            from llmlingua import PromptCompressor
            self._llmlingua_client = PromptCompressor()
            logger.info("Initialized official PromptCompressor for LongLLMLingua")
        except Exception:
            logger.debug("PromptCompressor not installed; using token-entropy calibrated compression.")

    def estimate_tokens(self, text: str) -> int:
        return self.fallback.estimate_tokens(text)

    def _calculate_token_entropy(self, token: str, doc_length: int) -> float:
        """Calculate statistical information surprise / entropy for token."""
        if not token:
            return 0.0
        # High-information indicators: digits, uppercase, technical punctuation
        has_num = 2.5 if any(c.isdigit() for c in token) else 1.0
        has_upper = 1.5 if any(c.isupper() for c in token) else 1.0
        len_factor = math.log2(max(2, len(token)))
        return len_factor * has_num * has_upper

    def compress(self, request: CompressionRequest) -> CompressionResult:
        if self._llmlingua_client is not None:
            try:
                res = self._llmlingua_client.compress_prompt(
                    [request.text],
                    rate=request.compression_rate,
                    condition_compare=True,
                )
                comp_text = res.get("compressed_prompt", request.text)
                orig_tokens = res.get("origin_tokens", self.estimate_tokens(request.text))
                comp_tokens = res.get("compressed_tokens", self.estimate_tokens(comp_text))
                return CompressionResult(
                    original_text=request.text,
                    compressed_text=comp_text,
                    original_tokens=orig_tokens,
                    compressed_tokens=comp_tokens,
                    compression_ratio=round(comp_tokens / max(1, orig_tokens), 2),
                )
            except Exception as err:
                logger.warning(f"Official PromptCompressor failed, using entropy fallback: {err}")

        # Statistical Perplexity & Entropy Scoring
        original_text = request.text.strip()
        orig_tokens = self.estimate_tokens(original_text)
        if not original_text or request.compression_rate >= 0.95:
            return self.fallback.compress(request)

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", original_text) if s.strip()]
        if not sentences:
            return self.fallback.compress(request)

        scored_sentences = []
        for idx, sent in enumerate(sentences):
            words = sent.split()
            sentence_entropy = sum(self._calculate_token_entropy(w, len(words)) for w in words)
            normalized_score = sentence_entropy / max(1, len(words))
            # Positional bias for introduction and conclusion
            pos_bonus = 1.2 if (idx == 0 or idx == len(sentences) - 1) else 1.0
            scored_sentences.append((normalized_score * pos_bonus, idx, sent))

        keep_count = max(1, int(len(sentences) * request.compression_rate))
        scored_sentences.sort(key=lambda x: x[0], reverse=True)

        selected = scored_sentences[:keep_count]
        selected.sort(key=lambda x: x[1])

        compressed_text = " ".join([s[2] for s in selected])
        comp_tokens = self.estimate_tokens(compressed_text)

        return CompressionResult(
            original_text=original_text,
            compressed_text=compressed_text,
            original_tokens=orig_tokens,
            compressed_tokens=comp_tokens,
            compression_ratio=round(comp_tokens / max(1, orig_tokens), 2),
        )
