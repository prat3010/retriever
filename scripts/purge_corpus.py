#!/usr/bin/env python3
"""Purge stale indexed documents from Retriever tenants.

Deletes existing documents across specified tenants to enable a fresh,
layout-aware re-ingestion cycle.
"""

import json
import time
import urllib.error
import urllib.request

TARGET_URL = "https://rag.prateeq.in"

TENANTS = [
    {
        "name": "Prateeq Sharma — Portfolio AI Twin",
        "tenant_id": "6797e2c8-745a-4bd1-aa4c-3854b8d79c22",
        "api_key": "ret_live_TaaRP0w94H8.a3_CjGsoQY57Fy5bv9Kk40zfUOoH4ak2",
    },
    {
        "name": "Prateeq Scoping Engine",
        "tenant_id": "1f85286c-9d9a-4ebc-9c62-a99360a5ece4",
        "api_key": "ret_live_eae27a51db3b44ef81e16df59137eda7bcfdc987dc204d6bacb9db0089a7886a",
    },
]


def get_documents(tenant_id: str, api_key: str) -> list[dict]:
    url = f"{TARGET_URL}/v1/tenants/{tenant_id}/documents?limit=200"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("items", []) if isinstance(data, dict) else data
    except Exception as e:
        print(f"  ❌ Error fetching documents for {tenant_id}: {e}")
        return []


def delete_document(tenant_id: str, doc_id: str, api_key: str) -> bool:
    url = f"{TARGET_URL}/v1/tenants/{tenant_id}/documents/{doc_id}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        method="DELETE",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return resp.status in (200, 204)
    except urllib.error.HTTPError as e:
        print(f"  ❌ HTTP {e.code} deleting {doc_id}: {e.read().decode('utf-8', errors='ignore')}")
        return False
    except Exception as e:
        print(f"  ❌ Error deleting {doc_id}: {e}")
        return False


def purge_tenant(tenant: dict) -> None:
    t_id = tenant["tenant_id"]
    t_name = tenant["name"]
    api_key = tenant["api_key"]

    print(f"\n🗑️  Purging tenant: '{t_name}' ({t_id})...")
    docs = get_documents(t_id, api_key)
    print(f"   Found {len(docs)} documents to purge.")

    if not docs:
        print("   ✅ Tenant already clean.")
        return

    deleted = 0
    for idx, doc in enumerate(docs, start=1):
        d_id = doc.get("documentId") or doc.get("id")
        filename = doc.get("filename", "unnamed")
        print(f"   [{idx}/{len(docs)}] Deleting {filename} ({d_id})...", end="", flush=True)
        ok = delete_document(t_id, d_id, api_key)
        if ok:
            deleted += 1
            print(" ✓ Deleted")
        else:
            print(" ❌ Failed")
        time.sleep(0.5)

    print(f"   🎉 Tenant purge complete: {deleted}/{len(docs)} documents deleted.")


def main():
    print(f"🚀 Starting corpus purge on {TARGET_URL}...")
    for t in TENANTS:
        purge_tenant(t)
    print("\n✨ All target tenants successfully purged of stale indexed documents!")


if __name__ == "__main__":
    main()
