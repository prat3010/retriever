#!/usr/bin/env python3
"""Phase 3: Cross-Tenant RLS Penetration Attack & Boundary Guillotine"""
import urllib.request
import urllib.error
import json
import time

with open("data/test_tenants.json") as f:
    tenants = json.load(f)

red_team_key = tenants["red_team"]["api_key"]
fin_audit_id = tenants["fin_audit"]["tenant_id"]
fin_audit_key = tenants["fin_audit"]["api_key"]

print("🛡️ RUNNING PHASE 3: CROSS-TENANT RLS PENETRATION ATTACK...")

# --- Test 1: Penetration Search (Adversary searches for another tenant's proprietary data) ---
print("\n[Attack 1] Adversary searches for fin_audit 10-K filings via red_team workspace...")
search_url = "http://localhost:8000/v1/tenants/red_team/search"
payload = {
    "query": "Apple total net sales 10-K balance sheet consolidated statements revenue",
    "top_k": 10
}
req = urllib.request.Request(
    search_url,
    data=json.dumps(payload).encode(),
    headers={
        "Authorization": f"Bearer {red_team_key}",
        "Content-Type": "application/json"
    }
)

start = time.perf_counter()
with urllib.request.urlopen(req, timeout=15) as resp:
    duration = (time.perf_counter() - start) * 1000
    data = json.loads(resp.read().decode())
    results = data.get("results", [])
    print(f"  • Latency: {round(duration, 2)}ms | Results returned: {len(results)}")
    
    # Assert ZERO leakage from fin_audit or other tenants
    for idx, r in enumerate(results, 1):
        content = r.get("content", "").lower()
        assert "consolidated statements of operations" not in content, (
            f"CRITICAL BREACH: fin_audit 10-K data leaked to red_team at rank {idx}!"
        )
        assert "apple inc." not in content, (
            f"CRITICAL BREACH: Apple 10-K data leaked to red_team at rank {idx}!"
        )
        assert "nvidia corporation" not in content, (
            f"CRITICAL BREACH: NVIDIA 10-K data leaked to red_team at rank {idx}!"
        )
    print("  ✓ PASS: Zero cross-tenant vector leakage detected in search results (100% Isolated).")

# --- Test 2: Direct Cross-Tenant Path Spoofing ---
# Adversary uses their own valid red_team key to query fin_audit path endpoint
print("\n[Attack 2] Adversary attempts path-parameter spoofing against fin_audit endpoint...")
cross_url = f"http://localhost:8000/v1/tenants/{fin_audit_id}/search"
cross_req = urllib.request.Request(
    cross_url,
    data=json.dumps(payload).encode(),
    headers={
        "Authorization": f"Bearer {red_team_key}",
        "Content-Type": "application/json"
    }
)

try:
    with urllib.request.urlopen(cross_req, timeout=15) as resp:
        print("  ❌ CRITICAL FAILURE: Cross-tenant path access was allowed with status 200!")
        exit(1)
except urllib.error.HTTPError as e:
    print(f"  • Response Code: {e.code} (Expected 403 Forbidden)")
    body = e.read().decode()
    print(f"  • Error detail:  {body}")
    assert e.code == 403, f"Expected 403 Forbidden, got {e.code}"
    print("  ✓ PASS: Tenancy Breach Kill-Switch instantly severed unauthorized path access!")

# --- Test 3: Document Catalog Boundary Penetration ---
print("\n[Attack 3] Adversary attempts to list fin_audit documents using red_team key...")
doc_url = f"http://localhost:8000/v1/tenants/{fin_audit_id}/documents"
doc_req = urllib.request.Request(
    doc_url,
    headers={
        "Authorization": f"Bearer {red_team_key}",
        "Content-Type": "application/json"
    }
)

try:
    with urllib.request.urlopen(doc_req, timeout=15) as resp:
        print("  ❌ CRITICAL FAILURE: Cross-tenant document listing was allowed with status 200!")
        exit(1)
except urllib.error.HTTPError as e:
    print(f"  • Response Code: {e.code} (Expected 403 Forbidden)")
    assert e.code in (401, 403), f"Expected 401 or 403, got {e.code}"
    print("  ✓ PASS: Document catalog isolated by tenant boundary.")

print("\n✅ PHASE 3 CROSS-TENANT PENETRATION ATTACK DEFEATED (Zero-Leakage Guillotine Verified)!\n")
