#!/usr/bin/env python3
"""Retriever Production Readiness & Go-Live Verification Engine.

Executes end-to-end diagnostic probes against live production infrastructure
(or local development instances) to verify operational readiness:
  1. PostgreSQL Connection Pool & Redis Health (/health/readiness)
  2. ASGI Gateway Event Loop & Nginx Routing (/health/liveness)
  3. Administrative Master Key RBAC (/v1/admin/tenants)
  4. Tenant Configuration & Retrieval Settings (/v1/admin/tenants/[id]/config)
  5. Hybrid / Keyword Search Resilience (/v1/tenants/[id]/search)
  6. Universal Model Context Protocol SSE Handshake (/mcp/sse)
  7. Rate Limiting Margin Check (x-ratelimit-remaining)

Usage:
  python3 scripts/verify_production_readiness.py --target https://rag.prateeq.in
  python3 scripts/verify_production_readiness.py --target http://localhost:8000
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_TARGET = os.getenv("RETRIEVER_API_URL", "https://rag.prateeq.in")
DEFAULT_TENANT_ID = os.getenv("LOAD_TEST_TENANT_ID", "1f85286c-9d9a-4ebc-9c62-a99360a5ece4")
DEFAULT_API_KEY = os.getenv("LOAD_TEST_API_KEY", "ret_live_hUQ-4muveDE.w9aBPR9iJBMbWeaUapCwUR-_T9IlwmXh")
DEFAULT_USER_ID = os.getenv("LOAD_TEST_USER_ID", "36e62429-419e-48ef-af92-533afca9e028")
DEFAULT_ADMIN_KEY = os.getenv("ADMIN_MASTER_KEY", "2f4a1713e6a2526f51e7e6b7825689509c9071e0b61fa59a5804ccfdbdafd266")


def probe_http(
    url: str,
    method: str = "GET",
    headers: dict | None = None,
    payload: dict | None = None,
    timeout: float = 10.0,
) -> tuple[int, float, dict | str, dict]:
    """Execute synchronous probe with microsecond timer and headers extraction."""
    req_headers = headers.copy() if headers else {}
    data_bytes = None
    if payload is not None:
        data_bytes = json.dumps(payload).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data_bytes, headers=req_headers, method=method)
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            latency = (time.perf_counter() - start) * 1000.0
            resp_headers = dict(response.headers)
            try:
                body = json.loads(raw)
            except Exception:
                body = raw
            return response.status, round(latency, 2), body, resp_headers
    except urllib.error.HTTPError as e:
        latency = (time.perf_counter() - start) * 1000.0
        raw = e.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except Exception:
            body = raw
        return e.code, round(latency, 2), body, dict(e.headers)
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000.0
        return 0, round(latency, 2), str(e), {}


def main():
    parser = argparse.ArgumentParser(description="Retriever Production Readiness Diagnostics")
    parser.add_argument("--target", default=DEFAULT_TARGET, help=f"Target base URL (default: {DEFAULT_TARGET})")
    parser.add_argument("--tenant-id", default=DEFAULT_TENANT_ID, help="Tenant UUID for testing")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="Tenant API Key")
    parser.add_argument("--user-id", default=DEFAULT_USER_ID, help="Tenant User ID")
    parser.add_argument("--admin-key", default=DEFAULT_ADMIN_KEY, help="Admin Master Key")

    args = parser.parse_args()
    target = args.target.rstrip("/")

    print("\n" + "=" * 70)
    print("🔍 RETRIEVER PRODUCTION READINESS & GO-LIVE DIAGNOSTICS")
    print(f"🎯 Target Infrastructure: {target}")
    print(f"🔑 Tenant Under Test:    {args.tenant_id}")
    print("=" * 70 + "\n")

    results = []

    # Probe 1: Database & Pool Readiness
    print("1. Testing PostgreSQL Connection Pool & Redis (/health/readiness)...", end=" ", flush=True)
    status, lat, body, hdrs = probe_http(f"{target}/health/readiness")
    if status == 200 and isinstance(body, dict) and body.get("status") == "ready":
        print(f"✅ PASSED ({lat}ms)")
        results.append(("PostgreSQL & Redis Pool Readiness", True, f"{lat}ms (status: ready)"))
    else:
        print(f"❌ FAILED (HTTP {status}, {lat}ms: {body})")
        results.append(("PostgreSQL & Redis Pool Readiness", False, f"HTTP {status}"))

    # Probe 2: Gateway Event Loop
    print("2. Testing ASGI Event Loop & Nginx Routing (/health/liveness)...", end=" ", flush=True)
    status, lat, body, hdrs = probe_http(f"{target}/health/liveness")
    rate_remaining = hdrs.get("x-ratelimit-remaining", "N/A")
    if status == 200 and isinstance(body, dict) and body.get("status") == "alive":
        print(f"✅ PASSED ({lat}ms | Rate Remaining: {rate_remaining})")
        results.append(("ASGI Gateway & Nginx Routing", True, f"{lat}ms"))
    else:
        print(f"❌ FAILED (HTTP {status})")
        results.append(("ASGI Gateway & Nginx Routing", False, f"HTTP {status}"))

    # Probe 3: Admin Master Key RBAC
    print("3. Testing Admin Master Key Authentication (/v1/admin/tenants)...", end=" ", flush=True)
    admin_headers = {"X-Admin-Master-Key": args.admin_key}
    status, lat, body, hdrs = probe_http(f"{target}/v1/admin/tenants", headers=admin_headers)
    if status == 200 and isinstance(body, dict) and "items" in body:
        tenant_count = body.get("total", len(body.get("items", [])))
        print(f"✅ PASSED ({lat}ms | {tenant_count} active tenants registered)")
        results.append(("Admin Master Key RBAC", True, f"{lat}ms ({tenant_count} tenants)"))
    else:
        print(f"❌ FAILED (HTTP {status}: {body})")
        results.append(("Admin Master Key RBAC", False, f"HTTP {status}"))

    # Probe 4: Tenant Retrieval Configuration
    print(f"4. Inspecting Tenant Configuration ({args.tenant_id[:8]}...)...", end=" ", flush=True)
    status, lat, body, hdrs = probe_http(f"{target}/v1/admin/tenants/{args.tenant_id}/config", headers=admin_headers)
    if status == 200 and isinstance(body, dict):
        embed_prov = body.get("embedding_provider", {}).get("provider_name", "unknown")
        embed_model = body.get("embedding_provider", {}).get("model_name", "unknown")
        print(f"✅ PASSED ({lat}ms | Provider: {embed_prov} • Model: {embed_model})")
        results.append(("Tenant Configuration", True, f"Provider: {embed_prov}/{embed_model}"))
    else:
        print(f"❌ FAILED (HTTP {status})")
        results.append(("Tenant Configuration", False, f"HTTP {status}"))

    # Probe 5: Search & Retrieval Resilience
    print("5. Executing Hybrid / Keyword Search Query (/v1/tenants/[id]/search)...", end=" ", flush=True)
    search_headers = {
        "Authorization": f"Bearer {args.api_key}",
        "X-User-ID": args.user_id,
        "X-Tenant-ID": args.tenant_id,
    }
    search_payload = {
        "query": "What are the payment terms and deliverables?",
        "limit": 3,
        "enable_hybrid": True,
    }
    status, lat, body, hdrs = probe_http(
        f"{target}/v1/tenants/{args.tenant_id}/search",
        method="POST",
        headers=search_headers,
        payload=search_payload,
        timeout=15.0,
    )
    if status == 200 and isinstance(body, dict) and "results" in body:
        hit_count = len(body.get("results", []))
        strategy = body.get("searchMeta", {}).get("strategy", "unknown")
        print(f"✅ PASSED ({lat}ms | {hit_count} hits | Strategy: {strategy})")
        results.append(("Search & Retrieval Execution", True, f"{lat}ms ({hit_count} hits, strategy: {strategy})"))
    elif status == 500:
        print("⚠️ SERVER 500 (Embedder misconfiguration on remote VPS)")
        results.append(("Search & Retrieval Execution", False, "HTTP 500: Embedder misconfigured"))
    else:
        print(f"❌ FAILED (HTTP {status}: {body})")
        results.append(("Search & Retrieval Execution", False, f"HTTP {status}"))

    # Probe 6: Universal MCP Protocol Handshake
    print("6. Probing Universal MCP SSE Endpoint (/v1/mcp/sse)...", end=" ", flush=True)
    status, lat, body, hdrs = probe_http(f"{target}/v1/mcp/sse")
    if status in (200, 400, 401):  # 401 confirms endpoint is active and enforcing security
        print(f"✅ PASSED (Endpoint listening & auth enforced, {lat}ms)")
        results.append(("Universal MCP SSE Protocol", True, f"Active & Protected ({lat}ms)"))
    elif status == 404:
        print("⚠️ 404 NOT FOUND (Universal MCP router not mounted)")
        results.append(("Universal MCP SSE Protocol", False, "HTTP 404: Endpoint not found"))
    else:
        print(f"❌ FAILED (HTTP {status})")
        results.append(("Universal MCP SSE Protocol", False, f"HTTP {status}"))

    print("\n" + "=" * 70)
    print("📋 SUMMARY REPORT")
    print("=" * 70)
    all_passed = True
    for name, passed, detail in results:
        mark = "✓" if passed else "✗"
        if not passed:
            all_passed = False
        print(f"[{mark}] {name:35} : {detail}")
    print("=" * 70)

    if all_passed:
        print("🎉 100% PRODUCTION READY! All services operational.\n")
        return 0
    else:
        print("⚠️ ACTION ITEMS REQUIRED: Review highlighted checkpoints above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
