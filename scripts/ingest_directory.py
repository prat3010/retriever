#!/usr/bin/env python3
"""
Retriever — Batch Directory Ingestion Engine (CLI)
===================================================
Recursively crawls a local filesystem directory, filters relevant knowledge
files (Markdown, PDF, TXT, JSON, CSV), and batch-indexes them into a target
tenant workspace on the Retriever platform.

Usage:
    python3 scripts/ingest_directory.py --tenant <tenant_id> --dir ./docs
    python3 scripts/ingest_directory.py --tenant <tenant_id> --dir ./lore --ext md,txt --dry-run
"""

import argparse
import os
import sys
from pathlib import Path
import urllib.request
import urllib.error
import json
import mimetypes

# Terminal styling
BOLD = "\033[1m"
GREEN = "\033[0;32m"
CYAN = "\033[0;36m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
DIM = "\033[2m"
NC = "\033[0m"

IGNORE_DIRS = {
    ".git",
    "node_modules",
    ".next",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    "venv",
    ".pytest_cache",
    ".ruff_cache",
    ".gemini",
    ".agent",
    ".agents",
}


def find_files(
    directory: Path,
    extensions: set[str],
    recursive: bool = True,
    max_files: int = 100,
) -> list[Path]:
    """Scans directory for matching files, pruning ignored trees."""
    matches: list[Path] = []

    def scan(curr: Path):
        if len(matches) >= max_files:
            return
        try:
            for entry in curr.iterdir():
                if len(matches) >= max_files:
                    break
                if entry.is_dir():
                    if recursive and entry.name not in IGNORE_DIRS and not entry.name.startswith("."):
                        scan(entry)
                elif entry.is_file():
                    if entry.suffix.lower() in extensions and not entry.name.startswith("."):
                        matches.append(entry)
        except PermissionError:
            pass

    scan(directory)
    return matches


def upload_file_multipart(
    url: str,
    file_path: Path,
    admin_key: str,
) -> tuple[bool, dict]:
    """Uploads a single file using pure standard library multipart encoding."""
    boundary = "----WebKitFormBoundary" + os.urandom(16).hex()
    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"

    filename = file_path.name
    file_bytes = file_path.read_bytes()

    body_parts = [
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode(),
        f"Content-Type: {content_type}".encode(),
        b"",
        file_bytes,
        f"--{boundary}--".encode(),
        b"",
    ]
    payload = b"\r\n".join(body_parts)

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-Admin-Master-Key": admin_key,
            "Accept": "application/json",
            "User-Agent": "Retriever-Ingest-CLI/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return (True, data)
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode()
        return (False, {"error": f"HTTP {e.code}: {err_msg}"})
    except Exception as e:
        return (False, {"error": str(e)})


def load_env():
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

    if "ADMIN_MASTER_KEY" in os.environ and "RETRIEVER_ADMIN_MASTER_KEY" not in os.environ:
        os.environ["RETRIEVER_ADMIN_MASTER_KEY"] = os.environ["ADMIN_MASTER_KEY"]


def main():
    load_env()
    parser = argparse.ArgumentParser(
        description="Retriever Batch Directory Ingestion Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dir", required=True, help="Local directory path to ingest")
    parser.add_argument(
        "--tenant",
        default=os.getenv("RETRIEVER_TENANT_ID"),
        help="Target Tenant UUID (or set RETRIEVER_TENANT_ID)",
    )
    parser.add_argument(
        "--api-url",
        default=os.getenv("RETRIEVER_API_URL", "https://rag.prateeq.in"),
        help="Retriever Base API URL (default: https://rag.prateeq.in)",
    )
    parser.add_argument(
        "--admin-key",
        default=os.getenv("RETRIEVER_ADMIN_MASTER_KEY"),
        help="Admin Master Key (or set RETRIEVER_ADMIN_MASTER_KEY)",
    )
    parser.add_argument(
        "--ext",
        default="md,txt,pdf,json,csv",
        help="Comma-separated file extensions to include (default: md,txt,pdf,json,csv)",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not crawl subdirectories recursively",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=100,
        help="Safety cap on total files to upload (default: 100)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and list files without actually uploading",
    )

    args = parser.parse_args()

    target_dir = Path(args.dir).resolve()
    if not target_dir.is_dir():
        print(f"{RED}[ERROR] Directory not found: {target_dir}{NC}")
        sys.exit(1)

    if not args.dry_run and not args.tenant:
        print(f"{RED}[ERROR] Missing --tenant ID or RETRIEVER_TENANT_ID env variable.{NC}")
        sys.exit(1)

    if not args.dry_run and not args.admin_key:
        print(f"{RED}[ERROR] Missing --admin-key or RETRIEVER_ADMIN_MASTER_KEY env variable.{NC}")
        sys.exit(1)

    ext_set = {f".{e.strip().lstrip('.').lower()}" for e in args.ext.split(",") if e.strip()}

    print(f"\n{CYAN}{BOLD}Retriever Batch Directory Ingestion Engine{NC}")
    print(f"  • Source Directory: {target_dir}")
    print(f"  • Included Exts:    {', '.join(sorted(ext_set))}")
    print(f"  • Recursive Crawl:  {'No' if args.no_recursive else 'Yes'}")
    if not args.dry_run:
        print(f"  • Target Tenant:    {args.tenant}")
        print(f"  • API Gateway:      {args.api_url}")
    print("----------------------------------------------------------------------")

    files = find_files(target_dir, ext_set, recursive=not args.no_recursive, max_files=args.max_files)
    print(f"Discovered {BOLD}{len(files)}{NC} matching document(s).\n")

    if not files:
        print(f"{YELLOW}No files matched criteria. Exiting.{NC}")
        return

    if args.dry_run:
        print(f"{YELLOW}[DRY RUN] Files that would be uploaded:{NC}")
        for i, f in enumerate(files, 1):
            size_kb = round(f.stat().st_size / 1024, 1)
            print(f"  [{i:02d}] {f.relative_to(target_dir)} {DIM}({size_kb} KB){NC}")
        print(f"\n{GREEN}Scan complete. Remove --dry-run to start ingestion.{NC}")
        return

    upload_url = f"{args.api_url.rstrip('/')}/v1/admin/tenants/{args.tenant}/documents/upload"
    success_count = 0
    fail_count = 0

    for i, file_path in enumerate(files, 1):
        rel = file_path.relative_to(target_dir)
        size_kb = round(file_path.stat().st_size / 1024, 1)
        sys.stdout.write(f"[{i:02d}/{len(files):02d}] Uploading {rel} ({size_kb} KB)... ")
        sys.stdout.flush()

        ok, resp = upload_file_multipart(upload_url, file_path, args.admin_key)
        if ok:
            doc_id = resp.get("documentId", resp.get("id", "uploaded"))
            print(f"{GREEN}✓ OK{NC} {DIM}(ID: {doc_id}){NC}")
            success_count += 1
        else:
            err = resp.get("error", "Unknown error")
            print(f"{RED}FAILED{NC} {YELLOW}({err}){NC}")
            fail_count += 1

    print("\n----------------------------------------------------------------------")
    if fail_count == 0:
        print(f"{GREEN}{BOLD}✓ ALL {success_count} DOCUMENTS INGESTED SUCCESSFULLY!{NC}")
    else:
        print(f"{YELLOW}Batch complete: {success_count} succeeded, {fail_count} failed.{NC}")
    print("----------------------------------------------------------------------\n")


if __name__ == "__main__":
    main()
