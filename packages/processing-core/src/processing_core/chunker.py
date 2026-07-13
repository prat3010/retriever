import uuid
import json
import tiktoken


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
            "meta_data": json.dumps({"token_start": start, "token_end": end}),
        })

        chunk_index += 1
        step = max(1, chunk_size - chunk_overlap)
        start += step

    return chunks
