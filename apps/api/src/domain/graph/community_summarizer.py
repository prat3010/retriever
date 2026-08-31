"""Hierarchical Community Summarizer for GraphRAG.

Synthesizes knowledge graph community clusters into structured executive summaries,
enabling macro-level global reasoning and dataset-wide query answering.
"""

from collections import Counter, defaultdict
from typing import Any

from src.domain.abstractions.graph import BaseCommunitySummarizer, GraphCommunity


class CommunitySummarizer(BaseCommunitySummarizer):
    """Summarizes GraphRAG entity community clusters into structured narratives."""

    def __init__(self, default_model: str = "gemini-3.6-flash") -> None:
        self.default_model = default_model

    async def summarize_community(
        self, community: GraphCommunity, llm_provider: Any = None
    ) -> str:
        """Generate executive narrative summary for a community cluster."""
        if not community.entities and not community.triples:
            return "Empty community cluster."

        # If an LLM provider is available, attempt synthesis via prompt
        if llm_provider is not None:
            try:
                summary_text = await self._generate_llm_summary(community, llm_provider)
                if summary_text and len(summary_text.strip()) > 20:
                    community.summary = summary_text.strip()
                    return community.summary
            except Exception:
                # Fall back to heuristic summarizer on LLM failure
                pass

        # Heuristic deterministic summarization
        heuristic_summary = self._generate_heuristic_summary(community)
        community.summary = heuristic_summary
        return heuristic_summary

    async def _generate_llm_summary(
        self, community: GraphCommunity, llm_provider: Any
    ) -> str:
        """Call LLM provider to synthesize community into an executive brief."""
        triples_formatted = "\n".join(
            f"- {t.subject} [{t.predicate}] {t.object} (conf: {t.confidence})"
            for t in community.triples[:30]
        )
        entities_formatted = ", ".join(community.entities[:25])

        prompt = (
            f"You are a Knowledge Graph synthesis engine. Synthesize this entity community cluster into a concise executive brief:\n\n"
            f"Community Title: {community.title}\n"
            f"Level: {community.level} ({'Micro-Cluster' if community.level == 0 else 'Domain Theme' if community.level == 1 else 'Global Macro-Theme'})\n"
            f"Key Entities: {entities_formatted}\n\n"
            f"Core Relational Triples:\n{triples_formatted}\n\n"
            f"Generate a clear 2-3 paragraph summary detailing the core theme, primary entity hubs, and operational dynamics."
        )

        # Support both generate() and chat_completion() interfaces
        if hasattr(llm_provider, "generate"):
            res = await llm_provider.generate(prompt)
            return str(res)
        elif hasattr(llm_provider, "complete"):
            res = await llm_provider.complete(prompt)
            return str(res)
        elif hasattr(llm_provider, "chat"):
            res = await llm_provider.chat([{"role": "user", "content": prompt}])
            return str(res)
        return ""

    def _generate_heuristic_summary(self, community: GraphCommunity) -> str:
        """Generate structured markdown summary using graph topology metrics."""
        entity_counts: Counter[str] = Counter()
        predicate_groups: dict[str, list[str]] = defaultdict(list)

        for t in community.triples:
            entity_counts[t.subject] += 1
            entity_counts[t.object] += 1
            predicate_groups[t.predicate].append(f"{t.subject} -> {t.object}")

        top_hubs = [ent for ent, _ in entity_counts.most_common(3)]
        hub_str = ", ".join(top_hubs) if top_hubs else "N/A"

        pred_lines = []
        for pred, rels in sorted(predicate_groups.items(), key=lambda x: len(x[1]), reverse=True)[:4]:
            sample_rels = ", ".join(rels[:3])
            pred_lines.append(f"- **{pred}** ({len(rels)} links): {sample_rels}")

        pred_summary = "\n".join(pred_lines) if pred_lines else "- No specific predicate groupings."

        summary = (
            f"### {community.title} (Level {community.level})\n"
            f"**Primary Entity Hubs:** {hub_str}\n"
            f"**Total Entities:** {len(community.entities)} | **Total Relations:** {len(community.triples)}\n\n"
            f"#### Key Relational Dynamics\n"
            f"{pred_summary}\n\n"
            f"This community clusters tightly coupled concepts centered around {hub_str}, representing "
            f"key operational domain knowledge across the tenant index."
        )
        return summary
