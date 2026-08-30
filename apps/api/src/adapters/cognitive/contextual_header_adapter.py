"""Contextual Header Generator Adapter (Anthropic Contextual Retrieval).

Generates document-level situational context headers for individual chunks prior to embedding.
Implements the ContextualHeaderGeneratorPort.
"""
import asyncio
import logging
import os
from typing import Any

import openai

from src.domain.abstractions.contextual_retrieval import ContextualHeaderGeneratorPort

logger = logging.getLogger(__name__)

ANTHROPIC_CONTEXT_SYSTEM_PROMPT = (
    "You are an expert AI retrieval assistant. Your task is to give a short, succinct context "
    "(1-2 sentences, max 50-80 words) to situate a given chunk within the overall document "
    "to dramatically improve vector search retrieval and semantic clarity. "
    "Answer ONLY with the succinct context summary and nothing else."
)

DEFAULT_CHUNK_PROMPT_TEMPLATE = """<document>
{document}
</document>
Here is the chunk we want to situate within the whole document:
<chunk>
{chunk}
</chunk>
Please give a short, succinct context (1-2 sentences, max 50-80 words) to situate this chunk within the overall document for the purposes of improving search retrieval. Answer only with the succinct context and nothing else."""


class ContextualHeaderGeneratorAdapter(ContextualHeaderGeneratorPort):
    """Generates situational context headers for document chunks using an LLM."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        default_model: str = "gemini-1.5-flash",
        max_concurrent: int = 5,
        timeout_seconds: float = 12.0,
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._base_url = base_url or os.environ.get("OPENAI_BASE_URL", "")
        self.default_model = default_model
        self.max_concurrent = max_concurrent
        self.timeout_seconds = timeout_seconds
        self._client: openai.AsyncOpenAI | None = None

    def _get_client(
        self, api_key: str | None = None, base_url: str | None = None
    ) -> openai.AsyncOpenAI:
        effective_key = api_key or self._api_key or os.environ.get("OPENAI_API_KEY", "dummy-key")
        effective_base = base_url or self._base_url or os.environ.get("OPENAI_BASE_URL")

        kwargs: dict[str, Any] = {"api_key": effective_key}
        if effective_base:
            url = effective_base if effective_base.endswith("/") else f"{effective_base}/"
            kwargs["base_url"] = url

        return openai.AsyncOpenAI(**kwargs)

    async def generate_context_header_single(
        self,
        document_text: str,
        chunk_content: str,
        tenant_id: str,
        doc_metadata: dict[str, Any] | None = None,
    ) -> str:
        """Generate a situational context header for a single chunk."""
        meta = doc_metadata or {}
        filename = meta.get("filename", "Document")
        doc_type = meta.get("doc_type") or meta.get("default_doc_type", "Text Document")
        topics = meta.get("topics") or meta.get("default_topics", [])
        topic_str = f" regarding {', '.join(topics[:3])}" if isinstance(topics, list) and topics else ""

        # Default fallback header if LLM generation fails or is unavailable
        fallback_header = f"[Context: {filename} ({doc_type}{topic_str})]"

        if not chunk_content.strip() or not document_text.strip():
            return fallback_header

        # Restrict document text excerpt to 8,000 chars to avoid overflowing token budgets
        doc_excerpt = document_text[:8000]
        if len(document_text) > 8000:
            doc_excerpt += "\n... [truncated document content for context]"

        user_content = DEFAULT_CHUNK_PROMPT_TEMPLATE.format(
            document=doc_excerpt,
            chunk=chunk_content[:2000],
        )

        api_key = meta.get("api_key")
        base_url = meta.get("base_url")
        model = meta.get("model") or self.default_model

        try:
            client = self._get_client(api_key=api_key, base_url=base_url)
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": ANTHROPIC_CONTEXT_SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.0,
                    max_tokens=150,
                ),
                timeout=self.timeout_seconds,
            )
            raw_text = response.choices[0].message.content or ""
            cleaned = raw_text.strip()
            # Remove any wrapping quotes or markdown backticks
            cleaned = cleaned.strip("\"'`").strip()

            if cleaned:
                # Strip existing [Context: prefix if LLM hallucinated the bracket wrapper
                if cleaned.lower().startswith("[context:") and cleaned.endswith("]"):
                    cleaned = cleaned[9:-1].strip()
                elif cleaned.lower().startswith("context:"):
                    cleaned = cleaned[8:].strip()

                return f"[Context: {cleaned}]"
            return fallback_header

        except Exception as exc:
            logger.warning(
                "Contextual header generation failed for tenant %s, falling back to default header: %s",
                tenant_id,
                exc,
            )
            return fallback_header

    async def generate_context_headers(
        self,
        document_text: str,
        chunks: list[str],
        tenant_id: str,
        doc_metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        """Generate contextual headers for a batch of chunks concurrently."""
        if not chunks:
            return []

        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def _generate_with_limit(chunk: str, idx: int) -> str:
            async with semaphore:
                chunk_meta = dict(doc_metadata or {})
                chunk_meta["chunk_index"] = idx
                return await self.generate_context_header_single(
                    document_text=document_text,
                    chunk_content=chunk,
                    tenant_id=tenant_id,
                    doc_metadata=chunk_meta,
                )

        tasks = [_generate_with_limit(c, idx) for idx, c in enumerate(chunks)]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return list(results)
