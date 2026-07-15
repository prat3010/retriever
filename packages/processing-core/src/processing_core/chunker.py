import uuid
import json
import re
import math
import tiktoken
from processing_core.embedding import embed_with_retry


_ENCODING = tiktoken.get_encoding("cl100k_base")


def tokenize_text(text: str) -> list[int]:
    return _ENCODING.encode(text)


def decode_tokens(tokens: list[int]) -> str:
    return _ENCODING.decode(tokens)


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
    document_id: str = "",
    tenant_id: str = "",
) -> list[dict]:
    """Default Token-Aware Sliding Window Chunker."""
    tokens = tokenize_text(text)
    chunks = []
    start = 0
    chunk_index = 0

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_content = decode_tokens(chunk_tokens)
        cid = str(uuid.uuid4())

        chunks.append({
            "chunk_id": cid,
            "document_id": document_id,
            "tenant_id": tenant_id,
            "content": chunk_content,
            "token_count": len(chunk_tokens),
            "chunk_index": chunk_index,
            "meta_data": json.dumps({"token_start": start, "token_end": end, "strategy": "fixed_window"}),
        })

        chunk_index += 1
        step = max(1, chunk_size - chunk_overlap)
        start += step

    return chunks


def chunk_recursive(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
    document_id: str = "",
    tenant_id: str = "",
) -> list[dict]:
    """Token-Aware Hierarchical Recursive Character Splitter."""
    delimiters = ["\n\n", "\n", " ", ""]

    def _split(text_block: str, delim_idx: int) -> list[str]:
        if len(tokenize_text(text_block)) <= chunk_size:
            return [text_block]
        if delim_idx >= len(delimiters):
            return [text_block]

        delim = delimiters[delim_idx]
        if delim == "":
            blocks = list(text_block)
        else:
            blocks = text_block.split(delim)

        results = []
        for b in blocks:
            if not b.strip():
                continue
            b_suffix = b + (delim if delim != "" else "")
            split_sub = _split(b_suffix, delim_idx + 1)
            results.extend(split_sub)
        return results

    raw_blocks = _split(text, 0)

    chunks = []
    current_chunk = []
    current_tokens = 0
    chunk_index = 0

    for block in raw_blocks:
        block_tokens = tokenize_text(block)
        if not block_tokens:
            continue

        if current_tokens + len(block_tokens) <= chunk_size:
            current_chunk.append((block, len(block_tokens)))
            current_tokens += len(block_tokens)
        else:
            if current_chunk:
                content = "".join([c[0] for c in current_chunk])
                chunks.append({
                    "chunk_id": str(uuid.uuid4()),
                    "document_id": document_id,
                    "tenant_id": tenant_id,
                    "content": content.strip(),
                    "token_count": current_tokens,
                    "chunk_index": chunk_index,
                    "meta_data": json.dumps({"strategy": "recursive"}),
                })
                chunk_index += 1

                keep_tokens = 0
                keep_count = 0
                for _, cb_len in reversed(current_chunk):
                    if keep_tokens + cb_len > chunk_overlap:
                        break
                    keep_tokens += cb_len
                    keep_count += 1
                current_chunk = current_chunk[-keep_count:] if keep_count else []
                current_tokens = keep_tokens

            current_chunk.append((block, len(block_tokens)))
            current_tokens += len(block_tokens)

    if current_chunk:
        content = "".join([c[0] for c in current_chunk])
        chunks.append({
            "chunk_id": str(uuid.uuid4()),
            "document_id": document_id,
            "tenant_id": tenant_id,
            "content": content.strip(),
            "token_count": current_tokens,
            "chunk_index": chunk_index,
            "meta_data": json.dumps({"strategy": "recursive"}),
        })

    return chunks


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude_v1 = math.sqrt(sum(a * a for a in v1))
    magnitude_v2 = math.sqrt(sum(b * b for b in v2))
    if magnitude_v1 == 0 or magnitude_v2 == 0:
        return 0.0
    return dot_product / (magnitude_v1 * magnitude_v2)


async def chunk_semantic(
    text: str,
    embed_client,
    embed_model: str,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
    semantic_threshold: float = 0.95,
    document_id: str = "",
    tenant_id: str = "",
) -> list[dict]:
    """Topic-Aware Semantic Similarity Sentence Chunker."""
    # C-1: More robust sentence boundary detection
    raw_sentences = re.split(
        r'(?<=[.?!])\s+(?=[A-Z"\'(])|(?<=[.?!])\s*$',
        text
    )
    sentences = [s.strip() for s in raw_sentences if s.strip()]
    if not sentences:
        return []

    # Batch embed all sentences to prevent redundant API queries
    embeddings = await embed_with_retry(embed_client, sentences, embed_model)

    similarities = []
    for i in range(len(embeddings) - 1):
        similarities.append(_cosine_similarity(embeddings[i], embeddings[i + 1]))

    chunks = []
    current_sentences = []
    current_tokens = 0
    chunk_index = 0

    for idx, sentence in enumerate(sentences):
        sentence_tokens = tokenize_text(sentence)

        did_split = False

        # C-2: Size-triggered split — check BEFORE adding the new sentence
        if current_sentences and (current_tokens + len(sentence_tokens) > chunk_size):
            content = " ".join(current_sentences)
            chunks.append(_make_chunk(content, current_tokens, chunk_index, document_id, tenant_id))
            chunk_index += 1

            # Overlap: carry forward sentences up to chunk_overlap tokens
            keep_tokens = 0
            keep_count = 0
            for s in reversed(current_sentences):
                st = len(tokenize_text(s))
                if keep_tokens + st > chunk_overlap:
                    break
                keep_tokens += st
                keep_count += 1
            current_sentences = current_sentences[-keep_count:] if keep_count else []
            current_tokens = keep_tokens
            did_split = True

        current_sentences.append(sentence)
        current_tokens += len(sentence_tokens)

        # C-2: Similarity-triggered split — only if we did NOT already split this iteration
        if not did_split and idx < len(similarities) and similarities[idx] < semantic_threshold:
            if current_sentences:
                content = " ".join(current_sentences)
                chunks.append(_make_chunk(content, current_tokens, chunk_index, document_id, tenant_id))
                chunk_index += 1
                # Overlap: carry forward sentences up to chunk_overlap tokens
                keep_tokens = 0
                keep_count = 0
                for s in reversed(current_sentences):
                    st = len(tokenize_text(s))
                    if keep_tokens + st > chunk_overlap:
                        break
                    keep_tokens += st
                    keep_count += 1
                current_sentences = current_sentences[-keep_count:] if keep_count else []
                current_tokens = keep_tokens

    if current_sentences:
        content = " ".join(current_sentences)
        chunks.append(_make_chunk(content, current_tokens, chunk_index, document_id, tenant_id))

    return chunks


def build_hierarchy(
    chunks: list[dict],
    group_size: int = 5,
    document_id: str = "",
    tenant_id: str = "",
) -> list[dict]:
    """Group child chunks into parent sections, setting parent_chunk_id on children.

    Each parent is a concatenation of its group_size child chunks.
    Parents are inserted first in the returned list, followed by children.
    """
    if not chunks:
        return []

    parents = []
    children_with_parent = []

    for i in range(0, len(chunks), group_size):
        group = chunks[i : i + group_size]
        parent_id = str(uuid.uuid4())
        parent_content = "\n\n---\n\n".join(c["content"] for c in group)
        parent_tokens = sum(c.get("token_count", 0) for c in group)

        parents.append({
            "chunk_id": parent_id,
            "document_id": document_id or group[0].get("document_id", ""),
            "tenant_id": tenant_id or group[0].get("tenant_id", ""),
            "content": parent_content,
            "token_count": parent_tokens,
            "chunk_index": group[0].get("chunk_index", 0),
            "meta_data": json.dumps({"is_parent": True, "strategy": "hierarchical"}),
        })

        for c in group:
            c["parent_chunk_id"] = parent_id
            children_with_parent.append(c)

    return parents + children_with_parent


def _make_chunk(
    content: str, token_count: int, chunk_index: int,
    document_id: str, tenant_id: str,
) -> dict:
    return {
        "chunk_id": str(uuid.uuid4()),
        "document_id": document_id,
        "tenant_id": tenant_id,
        "content": content.strip(),
        "token_count": token_count,
        "chunk_index": chunk_index,
        "meta_data": json.dumps({"strategy": "semantic"}),
    }
