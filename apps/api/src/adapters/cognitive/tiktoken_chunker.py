from typing import Any
import tiktoken
from src.domain.abstractions.ingestion import TextChunker


class TiktokenChunker(TextChunker):
    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        self.encoding = tiktoken.get_encoding(encoding_name)

    def split_text(self, text: str, chunk_size: int, chunk_overlap: int) -> list[dict[str, Any]]:
        """Split text contents into token-bounded chunks using sliding token windows."""
        tokens = self.encoding.encode(text)
        chunks = []

        start = 0
        chunk_index = 0

        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_content = self.encoding.decode(chunk_tokens)

            chunks.append({
                "content": chunk_content,
                "token_count": len(chunk_tokens),
                "chunk_index": chunk_index,
                "meta_data": {
                    "token_start": start,
                    "token_end": end,
                },
            })

            chunk_index += 1
            # Prevent infinite loops if overlap is configured larger than or equal to size
            step = max(1, chunk_size - chunk_overlap)
            start += step

        return chunks
