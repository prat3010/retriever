import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os

@pytest.mark.asyncio
async def test_embed_with_retry_batching() -> None:
    from processing_core.embedding import embed_with_retry
    
    # Mock OpenAI client
    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock()
    
    # We will simulate 75 inputs. Since batch_size is 32, this should call API 3 times:
    # Batch 1: 32, Batch 2: 32, Batch 3: 11
    inputs = [f"sentence-{i}" for i in range(75)]
    
    # Mock responses
    class MockEmbeddingItem:
        def __init__(self, index: int):
            self.index = index
            self.embedding = [0.1, 0.2]
            
    class MockResponse:
        def __init__(self, batch_size: int):
            self.data = [MockEmbeddingItem(j) for j in range(batch_size)]
            
    mock_client.embeddings.create.side_effect = [
        MockResponse(32),
        MockResponse(32),
        MockResponse(11)
    ]
    
    embeddings = await embed_with_retry(mock_client, inputs, "text-embedding-3-small")
    
    assert len(embeddings) == 75
    assert mock_client.embeddings.create.call_count == 3


def test_extract_text_from_file_whitelist() -> None:
    from processing_core.pdf_parser import extract_text_from_file
    import tempfile
    
    # 1. Text file extension in whitelist (.txt) should be read
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w+", delete=False, encoding="utf-8") as f:
        f.write("hello from txt file")
        f_path = f.name
        
    try:
        content = extract_text_from_file(f_path)
        assert content == "hello from txt file"
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)
            
    # 2. Binary extension not in whitelist (.docx) should return empty string ""
    with tempfile.NamedTemporaryFile(suffix=".docx", mode="w+", delete=False) as f:
        f.write("fake docx content")
        f_path = f.name
        
    try:
        content = extract_text_from_file(f_path)
        assert content == ""
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)
