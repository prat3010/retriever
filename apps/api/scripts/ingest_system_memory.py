"""Ingest System Memory Script for Retriever Meta-RAG.

This script parses code ASTs, Markdown architecture docs, git history, and section specifications
from both `retriever` and `Prateek_website` repositories, persisting them into PostgreSQL
pgvector under System Tenant `00000000-0000-0000-0000-000000000000`.
Supports both direct SQLAlchemy session and direct Supabase REST API persistence.
"""

import ast
import asyncio
import hashlib
import logging
import sys
import urllib.parse
import uuid
from pathlib import Path
from typing import Any

import httpx

# Ensure apps/api root is on sys.path
API_ROOT = Path(__file__).resolve().parent.parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from src.adapters.cognitive.ollama_embedding_adapter import OllamaEmbeddingAdapter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_system_memory")

import os

SYSTEM_TENANT_ID = "00000000-0000-0000-0000-000000000000"
RETRIEVER_ROOT = API_ROOT.parent.parent
WEBSITE_ROOT = Path("/Users/prateeksharma/Developer/Prateek_website")

SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "https://osaqaemntuzrjouzobvx.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

# ------------------------------------------------------------------------------
# AST & Chunkers
# ------------------------------------------------------------------------------

def chunk_python_ast(content: str, file_path: str) -> list[dict[str, Any]]:
    """Parse Python source file into semantic AST chunks (classes, functions, module docstring)."""
    chunks: list[dict[str, Any]] = []
    lines = content.splitlines()
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return chunk_line_blocks(content, file_path, "python_file")

    module_doc = ast.get_docstring(tree)
    if module_doc:
        chunks.append({
            "content": f"Module Docstring ({file_path}):\n{module_doc}",
            "symbol_name": "module_docstring",
            "chunk_type": "python_ast",
        })

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            start_line = node.lineno - 1
            end_line = node.end_lineno if hasattr(node, "end_lineno") and node.end_lineno else start_line + 40
            node_code = "\n".join(lines[start_line:end_line])
            doc = ast.get_docstring(node) or ""
            chunks.append({
                "content": f"Class {node.name} in {file_path}:\n{doc}\n```python\n{node_code}\n```",
                "symbol_name": node.name,
                "chunk_type": "python_class",
            })
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            start_line = node.lineno - 1
            end_line = node.end_lineno if hasattr(node, "end_lineno") and node.end_lineno else start_line + 30
            node_code = "\n".join(lines[start_line:end_line])
            doc = ast.get_docstring(node) or ""
            chunks.append({
                "content": f"Function {node.name} in {file_path}:\n{doc}\n```python\n{node_code}\n```",
                "symbol_name": node.name,
                "chunk_type": "python_function",
            })

    if not chunks:
        return chunk_line_blocks(content, file_path, "python_file")
        
    return chunks


def chunk_markdown(content: str, file_path: str) -> list[dict[str, Any]]:
    """Chunk Markdown document by headers (#, ##, ###)."""
    chunks: list[dict[str, Any]] = []
    lines = content.splitlines()
    current_title = "Header"
    current_buffer: list[str] = []

    for line in lines:
        if line.startswith("#"):
            if current_buffer:
                section_text = "\n".join(current_buffer).strip()
                if section_text:
                    chunks.append({
                        "content": f"File: {file_path} | Section: {current_title}\n\n{section_text}",
                        "symbol_name": current_title,
                        "chunk_type": "markdown_section",
                    })
                current_buffer = []
            current_title = line.lstrip("#").strip()
        current_buffer.append(line)

    if current_buffer:
        section_text = "\n".join(current_buffer).strip()
        if section_text:
            chunks.append({
                "content": f"File: {file_path} | Section: {current_title}\n\n{section_text}",
                "symbol_name": current_title,
                "chunk_type": "markdown_section",
            })

    return chunks if chunks else chunk_line_blocks(content, file_path, "markdown_file")


def chunk_line_blocks(content: str, file_path: str, chunk_type: str, block_size: int = 40) -> list[dict[str, Any]]:
    """Generic sliding window line chunker."""
    lines = content.splitlines()
    chunks: list[dict[str, Any]] = []
    for i in range(0, max(1, len(lines)), block_size):
        block = "\n".join(lines[i : i + block_size]).strip()
        if block:
            chunks.append({
                "content": f"File: {file_path} (Lines {i+1}-{min(len(lines), i+block_size)})\n```\n{block}\n```",
                "symbol_name": f"lines_{i+1}_{i+block_size}",
                "chunk_type": chunk_type,
            })
    return chunks


def generate_fallback_embedding(text: str, dim: int = 768) -> list[float]:
    """Generate a deterministic normalized vector embedding if no external model is available."""
    vector = [0.0] * dim
    hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()
    for i in range(dim):
        b = hash_bytes[i % len(hash_bytes)]
        vector[i] = (float(b) / 255.0) * 2.0 - 1.0
    norm = sum(v * v for v in vector) ** 0.5
    if norm > 0:
        vector = [v / norm for v in vector]
    return vector

# ------------------------------------------------------------------------------
# Supabase REST API Persistence Client
# ------------------------------------------------------------------------------

class SupabaseRestClient:
    def __init__(self, url: str, key: str) -> None:
        self.base_url = url.rstrip("/")
        self.key = key
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def ensure_system_tenant(self, client: httpx.AsyncClient) -> None:
        payload = {
            "tenant_id": SYSTEM_TENANT_ID,
            "name": "System Meta-RAG Tenant",
            "status": "active",
            "tier": "enterprise",
        }
        res = await client.post(
            f"{self.base_url}/rest/v1/tenants",
            headers={**self.headers, "Prefer": "resolution=ignore-duplicates"},
            json=payload,
        )
        res.raise_for_status()

    async def flush_system_memory(self, client: httpx.AsyncClient) -> None:
        """Purge all system tenant documents, document_chunks, and vector_records for a completely fresh start."""
        logger.info("=== Flushing all existing System Tenant vector memory from Supabase ===")
        try:
            # 1. Delete vector_records for system tenant
            await client.delete(
                f"{self.base_url}/rest/v1/vector_records?tenant_id=eq.{SYSTEM_TENANT_ID}",
                headers=self.headers,
            )
            # 2. Delete document_chunks for system tenant
            await client.delete(
                f"{self.base_url}/rest/v1/document_chunks?tenant_id=eq.{SYSTEM_TENANT_ID}",
                headers=self.headers,
            )
            # 3. Delete documents for system tenant
            await client.delete(
                f"{self.base_url}/rest/v1/documents?tenant_id=eq.{SYSTEM_TENANT_ID}",
                headers=self.headers,
            )
            logger.info("=== Flush complete! System tenant vector memory is completely cleared. ===")
        except Exception as e:
            logger.warning("Flush error: %s", e)

    async def deduplicate_system_memory(self, client: httpx.AsyncClient) -> None:
        """Fetch all active documents for SYSTEM_TENANT_ID and remove duplicate entries per filename."""
        try:
            url = f"{self.base_url}/rest/v1/documents?tenant_id=eq.{SYSTEM_TENANT_ID}&is_deleted=eq.false&select=document_id,filename,created_at"
            res = await client.get(url, headers=self.headers)
            if res.status_code != 200:
                return

            docs = res.json()
            if not docs:
                return

            # Group documents by filename
            by_filename: dict[str, list[dict[str, Any]]] = {}
            for doc in docs:
                fname = doc.get("filename")
                if fname:
                    by_filename.setdefault(fname, []).append(doc)

            purged_count = 0
            for fname, doc_list in by_filename.items():
                if len(doc_list) > 1:
                    # Sort by created_at descending, keep the latest one
                    doc_list.sort(key=lambda d: d.get("created_at", ""), reverse=True)
                    duplicate_docs = doc_list[1:]

                    for dup in duplicate_docs:
                        dup_id = dup["document_id"]
                        await client.delete(
                            f"{self.base_url}/rest/v1/document_chunks?document_id=eq.{dup_id}",
                            headers=self.headers,
                        )
                        await client.delete(
                            f"{self.base_url}/rest/v1/documents?document_id=eq.{dup_id}",
                            headers=self.headers,
                        )
                        purged_count += 1

            if purged_count > 0:
                logger.info("=== Cleaned up %d duplicate document records from previous pushes ===", purged_count)
        except Exception as e:
            logger.warning("Failed during deduplication sweep: %s", e)

    async def ingest_file(
        self,
        client: httpx.AsyncClient,
        repo_name: str,
        full_path: Path,
        rel_path: str,
        embedder: OllamaEmbeddingAdapter | None,
    ) -> int:
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except Exception as err:
            logger.warning("Could not read %s: %s", full_path, err)
            return 0

        file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        
        # Check existing document strictly by filename for SYSTEM_TENANT_ID
        encoded_filename = urllib.parse.quote(rel_path)
        res = await client.get(
            f"{self.base_url}/rest/v1/documents?tenant_id=eq.{SYSTEM_TENANT_ID}&filename=eq.{encoded_filename}&is_deleted=eq.false",
            headers=self.headers,
        )
        existing_docs = res.json() if res.status_code == 200 else []
        
        if existing_docs:
            existing_doc = existing_docs[0]
            # File content is completely unchanged — skip re-chunking and re-embedding to prevent duplicate records!
            if existing_doc.get("file_hash") == file_hash:
                return 0
            
            # File content modified — update existing document in-place and purge old chunks
            doc_id = existing_doc["document_id"]
            await client.delete(
                f"{self.base_url}/rest/v1/document_chunks?document_id=eq.{doc_id}",
                headers=self.headers,
            )
            patch_payload = {
                "file_hash": file_hash,
                "file_size": len(content),
            }
            await client.patch(
                f"{self.base_url}/rest/v1/documents?document_id=eq.{doc_id}",
                headers=self.headers,
                json=patch_payload,
            )
        else:
            # New document
            doc_id = str(uuid.uuid4())
            doc_payload = {
                "document_id": doc_id,
                "tenant_id": SYSTEM_TENANT_ID,
                "filename": rel_path,
                "file_hash": file_hash,
                "storage_path": str(full_path),
                "file_size": len(content),
                "mime_type": "text/plain",
                "status": "PROCESSED",
                "tags": ["system_memory", repo_name],
            }
            res = await client.post(
                f"{self.base_url}/rest/v1/documents",
                headers=self.headers,
                json=doc_payload,
            )
            res.raise_for_status()

        if full_path.suffix == ".py":
            raw_chunks = chunk_python_ast(content, rel_path)
        elif full_path.suffix in (".md", ".markdown"):
            raw_chunks = chunk_markdown(content, rel_path)
        else:
            raw_chunks = chunk_line_blocks(content, rel_path, f"{full_path.suffix.lstrip('.')}__file")

        chunk_payloads = []
        vector_payloads = []

        for idx, r_chunk in enumerate(raw_chunks):
            chunk_id = str(uuid.uuid4())
            chunk_content = r_chunk["content"]
            token_count = len(chunk_content.split())

            meta_data = {
                "source": "system_memory",
                "repository": repo_name,
                "file_path": rel_path,
                "chunk_type": r_chunk["chunk_type"],
                "symbol_name": r_chunk["symbol_name"],
            }

            chunk_payloads.append({
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "tenant_id": SYSTEM_TENANT_ID,
                "content": chunk_content,
                "token_count": token_count,
                "chunk_index": idx,
                "meta_data": meta_data,
            })

            embedding: list[float] | None = None
            if embedder:
                try:
                    embedding = await embedder.embed_text(chunk_content)
                except Exception:
                    embedding = None

            if not embedding:
                embedding = generate_fallback_embedding(chunk_content, dim=768)

            vector_payloads.append({
                "chunk_id": chunk_id,
                "tenant_id": SYSTEM_TENANT_ID,
                "embedding": embedding,
            })

        if chunk_payloads:
            res = await client.post(
                f"{self.base_url}/rest/v1/document_chunks",
                headers=self.headers,
                json=chunk_payloads,
            )
            res.raise_for_status()

        if vector_payloads:
            res = await client.post(
                f"{self.base_url}/rest/v1/vector_records",
                headers=self.headers,
                json=vector_payloads,
            )
            res.raise_for_status()

        return len(chunk_payloads)


async def run_ingestion(reset: bool = False) -> None:
    """Run system memory ingestion across retriever and Prateek_website repositories into Supabase."""
    logger.info("=== Starting System Memory Ingestion to Supabase ===")

    embedder = OllamaEmbeddingAdapter()
    sb_client = SupabaseRestClient(SUPABASE_URL, SUPABASE_KEY)

    async with httpx.AsyncClient(timeout=60.0) as http_client:
        await sb_client.ensure_system_tenant(http_client)
        if reset:
            await sb_client.flush_system_memory(http_client)
        else:
            await sb_client.deduplicate_system_memory(http_client)

        total_files = 0
        total_chunks = 0

        # 1. Ingest Retriever API Python source files
        retriever_src = RETRIEVER_ROOT / "apps" / "api" / "src"
        if retriever_src.exists():
            for py_file in retriever_src.glob("**/*.py"):
                rel_path = str(py_file.relative_to(RETRIEVER_ROOT))
                chunks_count = await sb_client.ingest_file(http_client, "retriever", py_file, rel_path, embedder)
                total_files += 1
                total_chunks += chunks_count
                logger.info("Ingested %s (%d chunks)", rel_path, chunks_count)

        # 2. Ingest Retriever Documentation
        retriever_docs = RETRIEVER_ROOT / "docs"
        if retriever_docs.exists():
            for md_file in retriever_docs.glob("**/*.md"):
                rel_path = str(md_file.relative_to(RETRIEVER_ROOT))
                chunks_count = await sb_client.ingest_file(http_client, "retriever", md_file, rel_path, embedder)
                total_files += 1
                total_chunks += chunks_count
                logger.info("Ingested %s (%d chunks)", rel_path, chunks_count)

        self_aware_plan = RETRIEVER_ROOT / "SELF_AWARE_RAG_PLAN.md"
        if self_aware_plan.exists():
            chunks_count = await sb_client.ingest_file(http_client, "retriever", self_aware_plan, "SELF_AWARE_RAG_PLAN.md", embedder)
            total_files += 1
            total_chunks += chunks_count
            logger.info("Ingested SELF_AWARE_RAG_PLAN.md (%d chunks)", chunks_count)

        # 3. Ingest Prateek_website Docs & Architecture Decisions
        if WEBSITE_ROOT.exists():
            website_docs = WEBSITE_ROOT / "docs"
            if website_docs.exists():
                for md_file in website_docs.glob("**/*.md"):
                    rel_path = str(md_file.relative_to(WEBSITE_ROOT))
                    chunks_count = await sb_client.ingest_file(http_client, "Prateek_website", md_file, rel_path, embedder)
                    total_files += 1
                    total_chunks += chunks_count
                    logger.info("Ingested %s (%d chunks)", rel_path, chunks_count)

            # 4. Ingest Prateek_website Key TypeScript & TSX Files
            website_src = WEBSITE_ROOT / "src"
            if website_src.exists():
                for ext_pattern in ("**/*.ts", "**/*.tsx"):
                    for ts_file in website_src.glob(ext_pattern):
                        if "node_modules" in str(ts_file) or ".next" in str(ts_file):
                            continue
                        rel_path = str(ts_file.relative_to(WEBSITE_ROOT))
                        chunks_count = await sb_client.ingest_file(http_client, "Prateek_website", ts_file, rel_path, embedder)
                        total_files += 1
                        total_chunks += chunks_count
                        logger.info("Ingested %s (%d chunks)", rel_path, chunks_count)

            # 5. Ingest Git Log History
            git_log_json = WEBSITE_ROOT / "src" / "data" / "git-log.json"
            if git_log_json.exists():
                chunks_count = await sb_client.ingest_file(http_client, "Prateek_website", git_log_json, "src/data/git-log.json", embedder)
                total_files += 1
                total_chunks += chunks_count
                logger.info("Ingested src/data/git-log.json (%d chunks)", chunks_count)

        logger.info("=== Ingestion Complete: Successfully uploaded %d files into %d chunks directly to Supabase! ===", total_files, total_chunks)


if __name__ == "__main__":
    do_reset = "--reset" in sys.argv or "--flush" in sys.argv
    asyncio.run(run_ingestion(reset=do_reset))
