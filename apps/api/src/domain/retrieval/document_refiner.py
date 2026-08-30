"""CRAG Document Refiner Domain Service.

Decomposes retrieved multi-paragraph document chunks into atomic sentences
and strips noisy boilerplate, returning high-signal factual propositions.

Hexagonal boundary rule: Pure domain logic. Zero external DB/framework imports.
"""
import re

from src.domain.abstractions.retrieval import SearchResult


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences while respecting common abbreviations and code patterns."""
    if not text or not text.strip():
        return []

    # Clean multi-newlines and tabs
    normalized = re.sub(r"\s+", " ", text).strip()
    # Split by sentence ending punctuation followed by space or end of string
    raw_sentences = re.split(r"(?<=[.!?])\s+", normalized)

    sentences: list[str] = []
    for s in raw_sentences:
        clean_s = s.strip()
        if len(clean_s) > 10:  # Ignore fragments smaller than 10 chars
            sentences.append(clean_s)

    return sentences if sentences else [text.strip()]


def _sentence_relevance(query_terms: set[str], sentence: str) -> float:
    """Calculate token overlap relevance between query terms and a sentence."""
    if not query_terms or not sentence:
        return 0.0

    sent_tokens = set(re.findall(r"\w+", sentence.lower()))
    if not sent_tokens:
        return 0.0

    matched = sum(1 for term in query_terms if term in sent_tokens)
    return matched / max(1, len(query_terms))


def refine_document_content(query: str, content: str, max_sentences: int = 6) -> str:
    """Extract and reconstruct the most relevant sentences answering the query."""
    if not content or not content.strip() or not query.strip():
        return content

    sentences = split_into_sentences(content)
    if len(sentences) <= 2:
        return content  # Already concise

    query_terms = set(re.findall(r"\w+", query.lower()))
    # Remove ultra-common stop words
    query_terms -= {"the", "a", "an", "is", "in", "of", "and", "or", "to", "for", "with", "on", "at", "by", "what", "how", "why", "who"}

    if not query_terms:
        return " ".join(sentences[:max_sentences])

    scored: list[tuple[int, str, float]] = []
    for idx, sent in enumerate(sentences):
        rel = _sentence_relevance(query_terms, sent)
        scored.append((idx, sent, rel))

    # Pick top sentences by relevance score, but keep at least first sentence if context is needed
    has_matches = any(s[2] > 0.0 for s in scored)
    if not has_matches:
        return " ".join(sentences[:max_sentences])

    # Sort descending by relevance
    sorted_by_rel = sorted(scored, key=lambda x: x[2], reverse=True)
    selected_indices = {s[0] for s in sorted_by_rel[:max_sentences] if s[2] > 0.0}

    # If too few matches, include index 0
    if len(selected_indices) < 2 and len(sentences) > 0:
        selected_indices.add(0)

    # Reconstruct in original chronological document order
    refined_sentences = [sentences[i] for i in sorted(selected_indices)]
    return " ".join(refined_sentences)


def refine_search_results(query: str, results: list[SearchResult], max_sentences_per_chunk: int = 5) -> list[SearchResult]:
    """Refine all chunks in a SearchResult list, stripping noisy sentences."""
    if not results or not query.strip():
        return results

    refined: list[SearchResult] = []
    for res in results:
        refined_text = refine_document_content(query, res.content, max_sentences=max_sentences_per_chunk)
        meta = dict(res.metadata)
        meta["is_refined"] = True
        refined.append(res.model_copy(update={"content": refined_text, "metadata": meta}))

    return refined
