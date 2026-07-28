"""Prompt Builder Service.

Resolves prompt templates, injects chat history and retrieved context
chunks, and enforces token budget limits via compression.
Depends only on domain abstractions — no infrastructure imports.
"""

import tiktoken

from src.domain.abstractions.exceptions import PromptTemplateNotFoundError
from src.domain.abstractions.inference import (
    ChatMessage,
    PromptTemplateRegistry,
)

CONTEXT_HEADER = "Here is the relevant context for answering (all chunks are equally important, order does not indicate priority):"
CONTEXT_TEMPLATE = "[Source: {chunk_id}] {content}"


_TIKTOKEN_ENCODING = tiktoken.get_encoding("cl100k_base")

def _estimate_tokens(text: str) -> int:
    return max(1, len(_TIKTOKEN_ENCODING.encode(text)))


class PromptBuilder:
    """Compiles structured prompts from templates, context, and history."""

    def __init__(self, template_registry: PromptTemplateRegistry) -> None:
        self.template_registry = template_registry

    async def build_messages(
        self,
        tenant_id: str,
        query: str,
        history: list[ChatMessage],
        context_chunks: list[dict],
        max_tokens: int = 4096,
        system_prompt_name: str = "default",
    ) -> list[ChatMessage]:
        """Build a message list ready for LLM inference.

        Compression strategy when over budget:
        1. Trim oldest history messages first.
        2. Prune lowest-scoring context chunks.
        """
        # 1. Resolve system prompt
        system_content = await self._resolve_system_prompt(
            tenant_id, system_prompt_name
        )

        # 2. Format context chunks
        context_block = self._format_context(context_chunks)

        # 3. Build candidate message list
        system_msg = ChatMessage(role="system", content=system_content)
        context_msg = ChatMessage(role="system", content=context_block)
        user_msg = ChatMessage(role="user", content=query)

        candidates = [system_msg] + history + [context_msg, user_msg]

        # 4. Compress if over budget
        budget = int(max_tokens * 0.95)
        total = sum(_estimate_tokens(m.content) for m in candidates)

        if total > budget:
            candidates = self._compress(candidates, budget, len(context_chunks))

        return candidates

    def _format_context(self, chunks: list[dict]) -> str:
        """Format retrieved chunks into a structured context block grouped by document."""
        if not chunks:
            return "No relevant context was found."

        docs: dict[str, list[dict]] = {}
        for c in chunks:
            doc_id = c.get("document_id", "unknown")
            docs.setdefault(doc_id, []).append(c)

        sections = [CONTEXT_HEADER]
        for doc_id, doc_chunks in docs.items():
            lines = [f"Document: {doc_id}"]
            for c in doc_chunks:
                meta = c.get("metadata") or {}
                parent_id = meta.get("parent_chunk_id") if isinstance(meta, dict) else None
                chunk_id = c.get("chunk_id", "unknown")
                content = c.get("content", "")
                if parent_id:
                    content = f"[This is part of section {parent_id}]\n{content}"
                lines.append(CONTEXT_TEMPLATE.format(chunk_id=chunk_id, content=content))
            sections.append("\n".join(lines))
        return "\n\n".join(sections)

    async def _resolve_system_prompt(
        self, tenant_id: str, name: str
    ) -> str:
        """Fetch system prompt from the template registry. Fail if missing."""
        template = await self.template_registry.get_template(tenant_id, name)
        if not template:
            raise PromptTemplateNotFoundError(tenant_id, name)
        return template.content

    def _compress(
        self,
        messages: list[ChatMessage],
        budget: int,
        chunk_count: int,
    ) -> list[ChatMessage]:
        """Compress messages to fit within token budget."""
        # System prompt is mandatory — keep it
        system = messages[0]
        remaining = messages[1:]

        # Remove oldest history messages first (but keep context + user)
        # Context is the second-to-last, user is last
        if len(remaining) > 2:
            context_msg = remaining[-2]
            user_msg = remaining[-1]
            history = remaining[:-2]

            while history and _estimate_tokens(
                system.content + "".join(m.content for m in history)
                + context_msg.content + user_msg.content
            ) > budget:
                history.pop(0)

            remaining = history + [context_msg, user_msg]

        # If still over budget, trim context chunks
        if _estimate_tokens(
            system.content + "".join(m.content for m in remaining)
        ) > budget:
            context_msg = remaining[-2]
            lines = context_msg.content.split("\n\n")
            header = lines[0] if lines else ""
            chunks = lines[1:]
            while chunks and _estimate_tokens(
                system.content + "".join(m.content for m in remaining[:-2])
                + header + "\n\n" + "\n\n".join(chunks)
                + remaining[-1].content
            ) > budget:
                chunks.pop()
            remaining[-2] = ChatMessage(
                role="system",
                content=header + "\n\n" + "\n\n".join(chunks)
                if chunks else "Context was truncated due to token limits.",
            )

        return [system] + remaining
