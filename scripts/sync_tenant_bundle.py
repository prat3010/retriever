#!/usr/bin/env python3
"""
Retriever — Declarative Tenant Bundle Provisioner & Ingestion CLI
===================================================================
Discovers, validates, and provisions self-contained Tenant Bundles.
Syncs tenant metadata, prompt templates, and knowledge documents into
the Retriever cognitive engine.

Usage:
    # Dry run / validation (offline, zero network/db required):
    python3 scripts/sync_tenant_bundle.py data/tenants/demo --dry-run
    python3 scripts/sync_tenant_bundle.py --all --dry-run

    # Live ingestion via Retriever HTTP API:
    python3 scripts/sync_tenant_bundle.py data/tenants/demo --api-url http://localhost:8000 --api-key <key>

    # Live ingestion via direct PostgreSQL / pgvector connection:
    python3 scripts/sync_tenant_bundle.py data/tenants/demo --direct-db
"""

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
import uuid

# Terminal styling
BOLD = "\033[1m"
GREEN = "\033[0;32m"
CYAN = "\033[0;36m"
YELLOW = "\033[1;33m"
MAGENTA = "\033[0;35m"
RED = "\033[0;31m"
DIM = "\033[2m"
NC = "\033[0m"


def load_env() -> None:
    """Reads local .env file if environment variables are not pre-set."""
    env_paths = [
        Path(__file__).resolve().parent.parent / ".env",
        Path(".env"),
    ]
    for p in env_paths:
        if p.is_file():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k not in os.environ:
                            os.environ[k] = v
                break
            except Exception:
                pass


def validate_tenant_manifest(manifest_path: Path) -> dict:
    """Validates the schema and values of a tenant.json manifest."""
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing tenant manifest at: {manifest_path}")

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON in {manifest_path}: {e}") from e

    # Required fields
    required = ["tenant_id", "name", "system_prompt"]
    for field in required:
        if field not in data or not data[field]:
            raise ValueError(f"Manifest {manifest_path.name} missing required field: '{field}'")

    # Validate UUID
    try:
        uuid.UUID(str(data["tenant_id"]))
    except ValueError as e:
        raise ValueError(f"Invalid UUID in 'tenant_id': {data['tenant_id']}") from e

    # Default optional parameters
    data.setdefault("tier", "developer")
    data.setdefault("active_model", "gemini-2.5-flash")
    data.setdefault("temperature", 0.4)
    data.setdefault("max_tokens", 2048)
    data.setdefault("fallbacks", {})

    return data


def find_bundle_documents(bundle_dir: Path) -> list[Path]:
    """Finds all markdown and text documents within a tenant bundle."""
    docs: list[Path] = []
    docs_dir = bundle_dir / "documents"

    search_dirs = [docs_dir] if docs_dir.is_dir() else [bundle_dir]
    for s_dir in search_dirs:
        for ext in ("*.md", "*.txt"):
            for p in sorted(s_dir.glob(ext)):
                if p.name.upper() not in {"README.MD", "LICENSE.MD", "CONTRIBUTING.MD"}:
                    docs.append(p)

    return docs


def upload_document_raw(
    api_url: str,
    tenant_id: str,
    api_key: str,
    title: str,
    content: str,
) -> tuple[bool, str]:
    """Uploads document content to the Retriever /documents/raw endpoint."""
    url = f"{api_url.rstrip('/')}/v1/tenants/{tenant_id}/documents/raw"
    payload = json.dumps({
        "title": title,
        "content": content,
        "mime_type": "text/markdown",
        "tags": ["tenant_bundle", "knowledge_base"],
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Content-Length": str(len(payload)),
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            chunks = data.get("chunk_count", 0)
            status = data.get("status", "PROCESSED")
            return (True, f"{chunks} chunks [{status}]")
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="ignore")
        return (False, f"HTTP {e.code}: {err}")
    except Exception as e:
        return (False, str(e))


async def ingest_bundle_direct_db(
    bundle_dir: Path,
    manifest: dict,
    docs: list[Path],
    db_url: str,
    ollama_url: str = "http://localhost:11434",
) -> None:
    """Direct PostgreSQL ingestion using asyncpg, layout chunking, and nomic-embed-text."""
    import asyncpg
    import pgvector.asyncpg

    # Add apps/api to path for domain chunker & embedder
    repo_root = Path(__file__).resolve().parent.parent
    api_src = repo_root / "apps" / "api"
    if str(api_src) not in sys.path:
        sys.path.insert(0, str(api_src))

    from src.adapters.cognitive.ollama_embedding_adapter import OllamaEmbeddingAdapter
    from src.domain.ingestion.chunker_factory import ChunkerFactory

    t_id = uuid.UUID(manifest["tenant_id"])
    t_name = manifest["name"]

    print(f"🔌 Connecting to PostgreSQL at {db_url.split('@')[-1]}...")
    conn = await asyncpg.connect(db_url, ssl="require" if "supabase" in db_url else "prefer")
    await pgvector.asyncpg.register_vector(conn)
    print(f"  {GREEN}✓ Connected to database.{NC}")

    # Upsert tenant
    await conn.execute(
        """
        INSERT INTO public.tenants (tenant_id, name, tier, status, created_at, updated_at)
        VALUES ($1, $2, $3, 'ACTIVE', now(), now())
        ON CONFLICT (tenant_id) DO UPDATE SET
            name = EXCLUDED.name,
            tier = EXCLUDED.tier,
            updated_at = now()
        """,
        t_id,
        t_name,
        manifest.get("tier", "developer"),
    )
    print(f"  {GREEN}✓ Upserted tenant record for {t_name}{NC}")

    # Upsert prompt template
    prompt_content = manifest.get("system_prompt", "")
    if prompt_content:
        await conn.execute(
            """
            INSERT INTO public.prompt_templates (
                prompt_id, tenant_id, name, content, is_system_prompt, is_locked, created_at, updated_at
            ) VALUES ($1, $2, 'default', $3, true, true, now(), now())
            ON CONFLICT (tenant_id, name) DO UPDATE SET
                content = EXCLUDED.content,
                updated_at = now()
            """,
            uuid.uuid4(),
            t_id,
            prompt_content,
        )
        print(f"  {GREEN}✓ Synchronized system prompt template in database.{NC}")

    if not docs:
        print(f"  {YELLOW}No documents found to ingest.{NC}")
        await conn.close()
        return

    chunker = ChunkerFactory.get_chunker("layout_aware")
    embedder = OllamaEmbeddingAdapter(
        base_url=ollama_url,
        model="nomic-embed-text",
        batch_size=32,
    )

    docs_to_insert = []
    chunks_to_insert = []
    chunk_texts = []
    chunk_to_doc = []

    print(f"  📄 Processing {len(docs)} documents...")
    for doc_path in docs:
        content = doc_path.read_text(encoding="utf-8")
        doc_id = uuid.uuid4()
        file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        file_size = len(content.encode("utf-8"))

        docs_to_insert.append((
            doc_id,
            t_id,
            doc_path.name,
            file_hash,
            f"tenants/{t_id}/{doc_path.name}",
            file_size,
            "text/markdown",
            "INDEXED",
            ["tenant_bundle"],
            False,
        ))

        raw_chunks = chunker.split_text_with_offsets(content, 500, 100)
        prefix = f"[Document: {doc_path.name}]\n"
        for idx, c in enumerate(raw_chunks):
            chunk_id = uuid.uuid4()
            chunk_content = f"{prefix}{c['content']}"
            meta_json = json.dumps(c.get("metadata") or {})

            chunks_to_insert.append((
                chunk_id,
                doc_id,
                t_id,
                chunk_content,
                len(chunk_content.split()),
                idx,
                None,
                meta_json,
            ))
            chunk_texts.append(chunk_content)
            chunk_to_doc.append((chunk_id, doc_id))

        print(f"   • {doc_path.name:45s} → {len(raw_chunks):2d} chunks ({file_size / 1024:.1f} KB)")

    print(f"  ⚡ {MAGENTA}Generating {len(chunk_texts)} embeddings via Ollama ({ollama_url})...{NC}")
    t0 = time.time()
    embeddings = await embedder.embed_batch(chunk_texts)
    duration = time.time() - t0
    print(f"  {GREEN}✓ Generated {len(embeddings)} vectors in {duration:.2f}s.{NC}")

    vectors_to_insert = [
        (c_id, t_id, emb)
        for (c_id, _), emb in zip(chunk_to_doc, embeddings, strict=True)
    ]

    print("  💾 Writing records to PostgreSQL...")
    async with conn.transaction():
        await conn.executemany(
            """
            INSERT INTO public.documents (
                document_id, tenant_id, filename, file_hash, storage_path,
                file_size, mime_type, status, tags, is_deleted, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, now(), now())
            """,
            docs_to_insert,
        )
        await conn.executemany(
            """
            INSERT INTO public.document_chunks (
                chunk_id, document_id, tenant_id, content, token_count,
                chunk_index, parent_chunk_id, meta_data, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, now())
            """,
            chunks_to_insert,
        )
        await conn.executemany(
            """
            INSERT INTO public.vector_records (
                chunk_id, tenant_id, embedding, created_at
            ) VALUES ($1, $2, $3, now())
            """,
            vectors_to_insert,
        )

    await embedder.client.aclose()
    await conn.close()
    print(f"  {GREEN}✓ Committed {len(docs_to_insert)} docs, {len(chunks_to_insert)} chunks, {len(vectors_to_insert)} vectors.{NC}")


def process_bundle(
    bundle_path: Path,
    dry_run: bool,
    api_url: str | None,
    api_key: str | None,
    direct_db: bool,
    db_url: str | None,
) -> bool:
    """Processes a single tenant bundle."""
    manifest_file = bundle_path / "tenant.json"
    print(f"\n{CYAN}{BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"{CYAN}{BOLD}📦 Tenant Bundle: {bundle_path.name}{NC}")
    print(f"   Path: {DIM}{bundle_path}{NC}")

    try:
        manifest = validate_tenant_manifest(manifest_file)
    except Exception as e:
        print(f"   {RED}❌ Manifest Validation Failed: {e}{NC}")
        return False

    tenant_id = manifest["tenant_id"]
    name = manifest["name"]
    model = manifest["active_model"]
    prompt = manifest["system_prompt"]
    fallbacks = manifest.get("fallbacks", {})
    docs = find_bundle_documents(bundle_path)

    print(f"   • Tenant ID:     {BOLD}{tenant_id}{NC}")
    print(f"   • Tenant Name:   {BOLD}{name}{NC}")
    print(f"   • Active Model:  {model}")
    print(f"   • System Prompt: {len(prompt)} chars (preview: '{prompt[:60]}...')")
    print(f"   • Fallbacks:     {len(fallbacks)} configured ({', '.join(fallbacks.keys()) or 'none'})")
    print(f"   • Documents:     {len(docs)} found ({sum(d.stat().st_size for d in docs):,} bytes total)")

    for d in docs:
        print(f"       - {d.name} ({d.stat().st_size / 1024:.1f} KB)")

    if dry_run:
        print(f"   {GREEN}✓ Validation Successful (DRY-RUN mode, no changes written).{NC}")
        return True

    # Direct database route
    if direct_db or (not api_url and db_url):
        if not db_url:
            print(f"   {RED}❌ DATABASE_URL or --db-url required for direct database ingestion.{NC}")
            return False
        try:
            asyncio.run(ingest_bundle_direct_db(bundle_path, manifest, docs, db_url))
            return True
        except Exception as e:
            print(f"   {RED}❌ Direct DB Ingestion Failed: {e}{NC}")
            return False

    # HTTP API route
    if not api_url:
        api_url = "http://localhost:8000"
    if not api_key:
        print(f"   {RED}❌ --api-key or RETRIEVER_API_KEY required for HTTP API ingestion.{NC}")
        return False

    print(f"   🛰️ Ingesting via API: {api_url}...")
    success = True
    for doc in docs:
        try:
            content = doc.read_text(encoding="utf-8")
            ok, msg = upload_document_raw(api_url, tenant_id, api_key, doc.name, content)
            if ok:
                print(f"       {GREEN}✓ {doc.name}: {msg}{NC}")
            else:
                print(f"       {RED}❌ {doc.name}: {msg}{NC}")
                success = False
            time.sleep(0.5)
        except Exception as e:
            print(f"       {RED}❌ Failed reading {doc.name}: {e}{NC}")
            success = False

    return success


def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(
        description="Retriever Declarative Tenant Bundle Provisioner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "bundle",
        nargs="?",
        help="Path to tenant bundle directory (e.g., data/tenants/demo)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Discover and process all tenant bundles in data/tenants/",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate manifest and preview corpus without making network or database writes",
    )
    parser.add_argument(
        "--api-url",
        default=os.getenv("RETRIEVER_API_URL"),
        help="Base URL of Retriever API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("RETRIEVER_API_KEY") or os.getenv("ADMIN_MASTER_KEY"),
        help="API key for ingestion authentication",
    )
    parser.add_argument(
        "--direct-db",
        action="store_true",
        help="Connect directly to PostgreSQL / pgvector instead of HTTP API",
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv("DATABASE_DIRECT_URL") or os.getenv("DATABASE_URL"),
        help="PostgreSQL connection string (defaults to DATABASE_DIRECT_URL or DATABASE_URL)",
    )

    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    tenants_dir = repo_root / "data" / "tenants"

    target_bundles: list[Path] = []
    if args.all:
        if tenants_dir.is_dir():
            for entry in sorted(tenants_dir.iterdir()):
                if entry.is_dir() and (entry / "tenant.json").is_file():
                    target_bundles.append(entry)
        if not target_bundles:
            print(f"{YELLOW}No tenant bundles found in {tenants_dir}{NC}")
            sys.exit(0)
    elif args.bundle:
        b_path = Path(args.bundle)
        if not b_path.is_dir():
            print(f"{RED}Error: Bundle directory not found: {args.bundle}{NC}")
            sys.exit(1)
        target_bundles.append(b_path)
    else:
        # Default to demo bundle if none specified
        demo_path = tenants_dir / "demo"
        if demo_path.is_dir():
            target_bundles.append(demo_path)
        else:
            parser.print_help()
            sys.exit(1)

    print(f"\n{BOLD}{CYAN}🚀 Retriever — Declarative Tenant Bundle Provisioner{NC}")
    print(f"Targeting {len(target_bundles)} bundle(s)... Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")

    all_ok = True
    for b in target_bundles:
        ok = process_bundle(
            bundle_path=b,
            dry_run=args.dry_run,
            api_url=args.api_url,
            api_key=args.api_key,
            direct_db=args.direct_db,
            db_url=args.db_url,
        )
        if not ok:
            all_ok = False

    print(f"\n{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    if all_ok:
        print(f"{GREEN}{BOLD}✨ All tenant bundles verified and processed successfully.{NC}\n")
        sys.exit(0)
    else:
        print(f"{RED}{BOLD}⚠️ One or more tenant bundles encountered errors.{NC}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
