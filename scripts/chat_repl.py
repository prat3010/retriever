#!/usr/bin/env python3
"""
Retriever — Interactive Terminal Chat REPL
===========================================
Terminal-native conversational RAG client. Allows developers to test queries,
explore knowledge grounding, and inspect citation spans directly from the shell
without opening a browser.

Usage:
    python3 scripts/chat_repl.py
    python3 scripts/chat_repl.py --tenant <tenant_id>
    python3 scripts/chat_repl.py --api-url http://localhost:8000
"""

import argparse
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

# Optional readline support for bash-like history
try:
    import readline  # noqa: F401
except ImportError:
    pass

# Terminal Colors
BOLD = "\033[1m"
GREEN = "\033[0;32m"
CYAN = "\033[0;36m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
MAGENTA = "\033[0;35m"
DIM = "\033[2m"
NC = "\033[0m"


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

    # Aliases
    if "ADMIN_MASTER_KEY" in os.environ and "RETRIEVER_ADMIN_MASTER_KEY" not in os.environ:
        os.environ["RETRIEVER_ADMIN_MASTER_KEY"] = os.environ["ADMIN_MASTER_KEY"]



def api_request(
    url: str,
    method: str = "GET",
    data: dict | None = None,
    headers: dict | None = None,
) -> tuple[bool, dict | list]:
    """Helper to execute JSON HTTP requests via urllib."""
    hdrs = {
        "Accept": "application/json",
        "User-Agent": "Retriever-REPL/1.0",
    }
    if headers:
        hdrs.update(headers)

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        hdrs["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read().decode("utf-8")
            return (True, json.loads(content))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return (False, json.loads(raw))
        except Exception:
            return (False, {"error": f"HTTP {e.code}: {raw}"})
    except Exception as e:
        return (False, {"error": str(e)})


def list_tenants(api_url: str, admin_key: str) -> list[dict]:
    """Fetches registered tenants for quick selection."""
    url = f"{api_url.rstrip('/')}/v1/admin/tenants?limit=20"
    ok, res = api_request(url, headers={"X-Admin-Master-Key": admin_key})
    if ok and isinstance(res, dict):
        return res.get("items", [])
    if ok and isinstance(res, list):
        return res
    return []


def list_documents(api_url: str, tenant_id: str, admin_key: str) -> list[dict]:
    """Fetches documents belonging to a tenant."""
    url = f"{api_url.rstrip('/')}/v1/admin/tenants/{tenant_id}/documents?limit=20"
    ok, res = api_request(url, headers={"X-Admin-Master-Key": admin_key})
    if ok and isinstance(res, list):
        return res
    if ok and isinstance(res, dict):
        return res.get("items", [])
    return []


def issue_session_key(api_url: str, tenant_id: str, admin_key: str) -> str | None:
    """Generates an ephemeral client API key for this terminal session using admin master key."""
    url = f"{api_url.rstrip('/')}/v1/admin/tenants/{tenant_id}/api-keys"
    ok, res = api_request(
        url,
        method="POST",
        data={"name": "Terminal REPL Session", "role": "client"},
        headers={"X-Admin-Master-Key": admin_key},
    )
    if ok and isinstance(res, dict) and "apiKey" in res:
        return res["apiKey"]
    return None


def search_tenant(
    api_url: str,
    tenant_id: str,
    query: str,
    api_key: str | None,
    admin_key: str | None,
    top_k: int = 4,
) -> tuple[bool, list[dict]]:
    """Executes hybrid vector search against tenant."""
    url = f"{api_url.rstrip('/')}/v1/tenants/{tenant_id}/search"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        headers["X-User-ID"] = "terminal_user"
    elif admin_key:
        headers["X-Admin-Master-Key"] = admin_key
        headers["X-User-ID"] = "terminal_user"

    payload = {"query": query, "limit": top_k}
    ok, res = api_request(url, method="POST", data=payload, headers=headers)
    if ok and isinstance(res, list):
        return (True, res)
    if ok and isinstance(res, dict) and "results" in res:
        return (True, res["results"])
    return (False, res if isinstance(res, dict) else {"error": str(res)})


def print_banner():
    print(f"\n{CYAN}{BOLD}")
    print("  ____      _       _                          ____  _____ ____  _     ")
    print(" |  _ \\ ___| |_ _ _(_) _____   _____ _ __     |  _ \\| ____|  _ \\| |    ")
    print(" | |_) / _ \\ __| '__| |/ _ \\ \\ / / _ \\ '__|    | |_) |  _| | |_) | |    ")
    print(" |  _ <  __/ |_| |  | |  __/\\ V /  __/ |       |  _ <| |___|  __/| |___ ")
    print(" |_| \\_\\___|\\__|_|  |_|\\___| \\_/ \\___|_|       |_| \\_\\_____|_|   |_____|")
    print(f"{NC}")
    print(f"{BOLD}Interactive Cognitive Terminal REPL (v1.0){NC}")
    print(f"{DIM}Commands: /docs, /tenant, /clear, /help, /exit{NC}")
    print("----------------------------------------------------------------------")


def main():
    load_env()
    parser = argparse.ArgumentParser(description="Retriever Interactive Terminal Chat")
    parser.add_argument(
        "--api-url",
        default=os.getenv("RETRIEVER_API_URL", "https://rag.prateeq.in"),
        help="Base API URL",
    )
    parser.add_argument(
        "--tenant",
        default=os.getenv("RETRIEVER_TENANT_ID"),
        help="Tenant UUID",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("RETRIEVER_API_KEY"),
        help="Client API Key",
    )
    parser.add_argument(
        "--admin-key",
        default=os.getenv("RETRIEVER_ADMIN_MASTER_KEY"),
        help="Admin Master Key",
    )
    args = parser.parse_args()

    api_url = args.api_url.rstrip("/")
    admin_key = args.admin_key
    tenant_id = args.tenant
    api_key = args.api_key

    print_banner()

    # If tenant not specified, discover available tenants
    if not tenant_id and admin_key:
        print(f"Discovering active tenants from {CYAN}{api_url}{NC}...")
        tenants = list_tenants(api_url, admin_key)
        if tenants:
            print(f"\n{BOLD}Available Tenants:{NC}")
            for i, t in enumerate(tenants, 1):
                tid = t.get("tenantId", t.get("id", ""))
                name = t.get("name", "Unnamed")
                print(f"  [{i}] {BOLD}{name}{NC} {DIM}({tid}){NC}")
            choice = input(f"\nSelect tenant number [1-{len(tenants)}] (or enter UUID): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(tenants):
                selected = tenants[int(choice) - 1]
                tenant_id = selected.get("tenantId", selected.get("id"))
            elif choice:
                tenant_id = choice

    if not tenant_id:
        tenant_id = input(f"{BOLD}Enter Tenant UUID to connect to:{NC} ").strip()

    if not tenant_id:
        print(f"{RED}[ERROR] No tenant specified. Exiting.{NC}")
        sys.exit(1)

    if not api_key and admin_key:
        api_key = issue_session_key(api_url, tenant_id, admin_key)

    print(f"\n{GREEN}Connected to Tenant:{NC} {BOLD}{tenant_id}{NC}")
    if api_key:
        print(f"{DIM}Session API Key active: {api_key[:16]}...{NC}")
    print(f"{DIM}Type your query and press Enter. Type /help for command list.{NC}\n")

    while True:
        try:
            query = input(f"{CYAN}{BOLD}retriever> {NC}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}Goodbye!{NC}")
            break

        if not query:
            continue

        # REPL Commands
        if query in ("/exit", "exit", "quit", ":q"):
            print(f"{DIM}Goodbye!{NC}")
            break

        elif query in ("/clear", "clear"):
            os.system("clear" if os.name != "nt" else "cls")
            print_banner()
            continue

        elif query in ("/help", "help"):
            print(f"\n{BOLD}Available REPL Commands:{NC}")
            print(f"  {CYAN}/docs{NC}     — List all indexed documents for this tenant")
            print(f"  {CYAN}/tenant{NC}   — Switch to another tenant UUID")
            print(f"  {CYAN}/clear{NC}    — Clear the terminal screen")
            print(f"  {CYAN}/exit{NC}     — Exit the chat REPL\n")
            continue

        elif query == "/docs":
            if not admin_key:
                print(f"{YELLOW}Admin master key required to inspect document library.{NC}\n")
                continue
            docs = list_documents(api_url, tenant_id, admin_key)
            if not docs:
                print(f"{YELLOW}No documents found in this tenant.{NC}\n")
            else:
                print(f"\n{BOLD}Indexed Documents ({len(docs)}):{NC}")
                for d in docs:
                    fname = d.get("filename", "unnamed")
                    status = d.get("status", "unknown")
                    chunks = d.get("chunkCount", d.get("chunks", 0))
                    print(f"  • {BOLD}{fname}{NC} {DIM}[status: {status}, chunks: {chunks}]{NC}")
                print()
            continue

        elif query.startswith("/tenant"):
            parts = query.split(maxsplit=1)
            if len(parts) > 1:
                tenant_id = parts[1].strip()
                print(f"{GREEN}Switched to tenant:{NC} {BOLD}{tenant_id}{NC}\n")
            else:
                new_t = input(f"{BOLD}Enter new Tenant UUID:{NC} ").strip()
                if new_t:
                    tenant_id = new_t
                    print(f"{GREEN}Switched to tenant:{NC} {BOLD}{tenant_id}{NC}\n")
            continue

        # Execute Search Query
        print(f"{DIM}Thinking & searching knowledge base...{NC}")
        ok, results = search_tenant(api_url, tenant_id, query, api_key, admin_key, top_k=3)

        if not ok:
            err = results.get("error", "Search failed")
            print(f"{RED}Error:{NC} {err}\n")
            continue

        if not results:
            print(f"{YELLOW}No relevant passages found in tenant knowledge base.{NC}\n")
            continue

        print(f"\n{BOLD}{GREEN}✓ Found {len(results)} Grounded Passage(s):{NC}\n")
        for i, hit in enumerate(results, 1):
            content = hit.get("content", hit.get("text", "")).strip()
            score = hit.get("score", 0.0)
            meta = hit.get("metadata") or {}
            doc_name = meta.get("filename", hit.get("documentId", "Document"))

            print(f"  {MAGENTA}[Citation #{i}] {BOLD}{doc_name}{NC} {DIM}(Similarity Score: {score:.4f}){NC}")
            # Indent snippet
            wrapped = "\n".join(f"    {line}" for line in content.splitlines()[:6])
            print(f"{wrapped}")
            if len(content.splitlines()) > 6:
                print(f"    {DIM}... [truncated]{NC}")
            print()


if __name__ == "__main__":
    main()
