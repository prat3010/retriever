import os
import ast
import hashlib
import uuid
import asyncio
from pathlib import Path
from sqlalchemy import delete, text
from sqlalchemy.future import select

from src.config import settings
from src.adapters.database.connection import tenant_session
from src.adapters.database.models import DocumentDb, DocumentChunkDb, VectorRecordDb
from src.adapters.cognitive.embedding_adapter import OpenAIEmbeddingAdapter

SYSTEM_TENANT_ID = "00000000-0000-0000-0000-000000000000"

# Directories to ignore
IGNORE_DIRS = {
    ".git", "node_modules", ".next", ".venv", "venv", 
    ".pytest_cache", ".ruff_cache", "__pycache__", "dist", "storage", ".deepeval"
}

IGNORE_FILES = {
    ".DS_Store", ".env"
}

# Index all files to make the RAG complete
SUPPORTED_EXTENSIONS = {".py", ".md", ".yml", ".yaml", ".json", ".ini", ".toml"}

def get_file_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

class OllamaEmbeddingAdapter(OpenAIEmbeddingAdapter):
    """Custom adapter extending OpenAIEmbeddingAdapter to make it compatible with Ollama and Gemini responses."""
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Process in batches of 32
        batch_size = 32
        all_embeddings = []
        
        for idx in range(0, len(texts), batch_size):
            sub_texts = texts[idx:idx+batch_size]
            sub_embeddings = None
            
            for attempt in range(5):
                try:
                    kwargs = {
                        "input": sub_texts,
                        "model": self._model,
                        "timeout": 30
                    }
                    # If using gemini-embedding-2 or text-embedding-3-small, pass dimensions
                    if self._model in ("gemini-embedding-2", "text-embedding-3-small"):
                        kwargs["extra_body"] = {"dimensions": 768}
                        
                    response = await self.client.embeddings.create(**kwargs)
                    
                    # Handle index null/None issues safely
                    sorted_data = sorted(response.data, key=lambda x: x.index if x.index is not None else 0)
                    sub_embeddings = [item.embedding for item in sorted_data]
                    break
                except Exception as e:
                    if attempt == 4:
                        print(f"  [ERROR] Exhausted embedding retries: {e}")
                        raise
                    sleep_time = (2 ** attempt) + 1
                    print(f"  [Error] Waiting {sleep_time}s to retry sub-batch...")
                    await asyncio.sleep(sleep_time)
            
            if sub_embeddings:
                all_embeddings.extend(sub_embeddings)
                
            # If using Gemini, add a small delay to stay under RPM limits; Ollama can run unthrottled
            if "generativelanguage" in str(self._base_url):
                await asyncio.sleep(3.0)
            
        return all_embeddings

def chunk_code_ast(file_content: str, rel_path: str) -> list[dict]:
    """Parse python code using AST to create logical chunks (Classes, Functions)."""
    chunks = []
    try:
        tree = ast.parse(file_content)
    except Exception:
        # Fallback to simple line-based chunking if AST parsing fails
        lines = file_content.split("\n")
        chunk_size = 50
        for i in range(0, len(lines), chunk_size):
            block = "\n".join(lines[i:i+chunk_size])
            chunks.append({
                "content": block,
                "meta": {
                    "data_type": "source_code",
                    "ast_node_type": "fallback",
                    "file_path": rel_path
                }
            })
        return chunks

    lines = file_content.split("\n")

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            # Class skeleton chunk
            class_header = f"class {node.name}:\n"
            doc = ast.get_docstring(node)
            if doc:
                class_header += f'    """{doc}"""\n'
            
            chunks.append({
                "content": class_header,
                "meta": {
                    "data_type": "source_code",
                    "ast_node_type": "class",
                    "name": node.name,
                    "file_path": rel_path
                }
            })

            # Method Chunks
            for sub_node in node.body:
                if isinstance(sub_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    fn_content = "\n".join(lines[sub_node.lineno-1:sub_node.end_lineno])
                    chunks.append({
                        "content": f"class {node.name}:\n    " + fn_content.replace("\n", "\n    "),
                        "meta": {
                            "data_type": "source_code",
                            "ast_node_type": "function",
                            "name": f"{node.name}.{sub_node.name}",
                            "parent_class": node.name,
                            "file_path": rel_path
                        }
                    })

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Top-level Function
            fn_content = "\n".join(lines[node.lineno-1:node.end_lineno])
            chunks.append({
                "content": fn_content,
                "meta": {
                    "data_type": "source_code",
                    "ast_node_type": "function",
                    "name": node.name,
                    "file_path": rel_path
                }
            })
            
    if not chunks:
        chunks.append({
            "content": file_content,
            "meta": {
                "data_type": "source_code",
                "ast_node_type": "module",
                "file_path": rel_path
            }
        })
    return chunks

def chunk_markdown(content: str, rel_path: str) -> list[dict]:
    chunks = []
    lines = content.split("\n")
    current_chunk = []
    current_header = "Introduction"
    
    for line in lines:
        if line.startswith(("# ", "## ", "### ")):
            if current_chunk:
                chunks.append({
                    "content": "\n".join(current_chunk),
                    "meta": {
                        "data_type": "documentation",
                        "section": current_header,
                        "file_path": rel_path
                    }
                })
                current_chunk = []
            current_header = line.strip("# ")
        current_chunk.append(line)
        
    if current_chunk:
        chunks.append({
            "content": "\n".join(current_chunk),
            "meta": {
                "data_type": "documentation",
                "section": current_header,
                "file_path": rel_path
            }
        })
    return chunks

def chunk_config(content: str, rel_path: str) -> list[dict]:
    chunks = []
    lines = content.split("\n")
    for i in range(0, len(lines), 40):
        block = "\n".join(lines[i:i+40])
        chunks.append({
            "content": block,
            "meta": {
                "data_type": "configuration",
                "file_path": rel_path
            }
        })
    return chunks

async def ingest_file(file_path: Path, root_dir: Path, embedder: OllamaEmbeddingAdapter):
    rel_path = str(file_path.relative_to(root_dir))
    print(f"Indexing: {rel_path}")
    
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        print(f"  Error reading {rel_path}: {e}")
        return
        
    file_hash = get_file_hash(content)
    file_size = file_path.stat().st_size
    mime_type = "text/plain"
    if file_path.suffix == ".py":
        mime_type = "text/x-python"
    elif file_path.suffix == ".md":
        mime_type = "text/markdown"
    elif file_path.suffix in (".yml", ".yaml"):
        mime_type = "text/yaml"
        
    # Get chunks
    if file_path.suffix == ".py":
        chunks = chunk_code_ast(content, rel_path)
    elif file_path.suffix == ".md":
        chunks = chunk_markdown(content, rel_path)
    else:
        chunks = chunk_config(content, rel_path)
        
    # Generate embeddings
    texts_to_embed = [c["content"] for c in chunks]
    try:
        embeddings = await embedder.embed_batch(texts_to_embed)
    except Exception as e:
        print(f"  Failed to generate embeddings for {rel_path}: {e}")
        return
        
    # Save to database
    async with tenant_session(tenant_id=SYSTEM_TENANT_ID) as session:
        # Check if document already exists
        stmt = select(DocumentDb).where(
            DocumentDb.tenant_id == uuid.UUID(SYSTEM_TENANT_ID),
            DocumentDb.filename == rel_path,
            DocumentDb.is_deleted == False
        )
        existing_doc = (await session.execute(stmt)).scalar_one_or_none()
        
        if existing_doc:
            if existing_doc.file_hash == file_hash:
                print(f"  No changes detected for {rel_path}. Skipping.")
                return
            # Delete old version chunks
            await session.execute(
                delete(DocumentChunkDb).where(DocumentChunkDb.document_id == existing_doc.document_id)
            )
            doc_id = existing_doc.document_id
            existing_doc.file_hash = file_hash
            existing_doc.file_size = file_size
            existing_doc.status = "INDEXED"
        else:
            doc_id = uuid.uuid4()
            db_doc = DocumentDb(
                document_id=doc_id,
                tenant_id=uuid.UUID(SYSTEM_TENANT_ID),
                filename=rel_path,
                file_hash=file_hash,
                storage_path=f"local://codebase/{rel_path}",
                file_size=file_size,
                mime_type=mime_type,
                status="INDEXED"
            )
            session.add(db_doc)
            
        await session.flush()
        
        # Save chunks and vectors
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = uuid.uuid4()
            db_chunk = DocumentChunkDb(
                chunk_id=chunk_id,
                document_id=doc_id,
                tenant_id=uuid.UUID(SYSTEM_TENANT_ID),
                content=chunk["content"],
                token_count=len(chunk["content"]) // 4,  # Rough token estimate
                chunk_index=i,
                meta_data=chunk["meta"]
            )
            session.add(db_chunk)
            
            db_vector = VectorRecordDb(
                chunk_id=chunk_id,
                tenant_id=uuid.UUID(SYSTEM_TENANT_ID),
                embedding=embedding
            )
            session.add(db_vector)
            
        await session.flush()
        print(f"  Successfully indexed {len(chunks)} chunks.")

async def main():
    root_dir = Path("/workspace")
    if not root_dir.exists():
        root_dir = Path(__file__).resolve().parent.parent.parent.parent
        
    print(f"Starting Ingestion of codebase in {root_dir}")
    
    # Configure custom/Ollama settings from environment variables
    model_name = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    api_key = os.getenv("OPENAI_API_KEY", settings.OPENAI_API_KEY or "ollama")
    base_url = os.getenv("OPENAI_BASE_URL", settings.OPENAI_BASE_URL or "http://host.docker.internal:11434/v1")
    
    print(f"Using Embedding Model: {model_name}")
    print(f"Using API Base URL: {base_url}")
    
    embedder = OllamaEmbeddingAdapter(
        api_key=api_key,
        base_url=base_url,
        model=model_name
    )
    
    files_to_ingest = []
    
    for root, dirs, files in os.walk(root_dir):
        # Filter directories in-place to avoid traversing them
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            if file in IGNORE_FILES:
                continue
            file_path = Path(root) / file
            if file_path.suffix in SUPPORTED_EXTENSIONS:
                files_to_ingest.append(file_path)
                
    print(f"Found {len(files_to_ingest)} candidate files to index.")
    
    for file_path in files_to_ingest:
        await ingest_file(file_path, root_dir, embedder)
        
    print("Ingestion complete.")

if __name__ == "__main__":
    asyncio.run(main())
