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

                overlap_chunk = []
                overlap_tokens = 0
                for cb, cb_len in reversed(current_chunk):
                    if overlap_tokens + cb_len <= chunk_overlap:
                        overlap_chunk.insert(0, (cb, cb_len))
                        overlap_tokens += cb_len
                    else:
                        break
                current_chunk = overlap_chunk
                current_tokens = overlap_tokens

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
    raw_sentences = re.split(r'(?<=[.?!])\s+', text)
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

        if current_sentences and (current_tokens + len(sentence_tokens) > chunk_size):
            content = " ".join(current_sentences)
            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "document_id": document_id,
                "tenant_id": tenant_id,
                "content": content.strip(),
                "token_count": current_tokens,
                "chunk_index": chunk_index,
                "meta_data": json.dumps({"strategy": "semantic"}),
            })
            chunk_index += 1

            # Simple overlap: carry forward the last sentence
            overlap_sentence = current_sentences[-1]
            overlap_tokens = len(tokenize_text(overlap_sentence))
            current_sentences = [overlap_sentence]
            current_tokens = overlap_tokens

        current_sentences.append(sentence)
        current_tokens += len(sentence_tokens)

        # Check similarity spike drops indicating topic transition
        if idx < len(similarities) and similarities[idx] < semantic_threshold:
            if current_sentences:
                content = " ".join(current_sentences)
                chunks.append({
                    "chunk_id": str(uuid.uuid4()),
                    "document_id": document_id,
                    "tenant_id": tenant_id,
                    "content": content.strip(),
                    "token_count": current_tokens,
                    "chunk_index": chunk_index,
                    "meta_data": json.dumps({"strategy": "semantic"}),
                })
                chunk_index += 1
                overlap_sentence = current_sentences[-1]
                overlap_tokens = len(tokenize_text(overlap_sentence))
                current_sentences = [overlap_sentence]
                current_tokens = overlap_tokens

    if current_sentences:
        content = " ".join(current_sentences)
        chunks.append({
            "chunk_id": str(uuid.uuid4()),
            "document_id": document_id,
            "tenant_id": tenant_id,
            "content": content.strip(),
            "token_count": current_tokens,
            "chunk_index": chunk_index,
            "meta_data": json.dumps({"strategy": "semantic"}),
        })

    return chunks
