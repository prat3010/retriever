import json
import re

from typing import Any


def format_citations(text: str, context_chunks: list[Any], template: str) -> str:
    chunk_map = {}
    for idx, c in enumerate(context_chunks):
        chunk_id = getattr(c, "chunk_id", None) or (c.get("chunk_id") if isinstance(c, dict) else None)
        if not chunk_id:
            continue

        meta = getattr(c, "metadata", None) or getattr(c, "meta_data", None) or (c.get("metadata") if isinstance(c, dict) else None)
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        filename = (meta or {}).get("filename", "Source")

        chunk_map[chunk_id] = {
            "index": idx + 1,
            "filename": filename,
            "chunk_id": chunk_id,
        }

    pattern = r"\[Source:\s*([a-zA-Z0-9\-]+)\]"

    def _replacer(match):
        cid = match.group(1)
        if cid in chunk_map:
            info = chunk_map[cid]
            try:
                return template.format(
                    index=info["index"],
                    filename=info["filename"],
                    chunk_id=info["chunk_id"],
                )
            except Exception:
                return f"[{info['index']}]"
        return match.group(0)

    return re.sub(pattern, _replacer, text)
