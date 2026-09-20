#!/usr/bin/env python3
"""Probe 2.3: Multi-Hop Knowledge Graph Reasoning (graph_research)"""
import urllib.request
import json
import time

with open("data/test_tenants.json") as f:
    tenants = json.load(f)

graph_tenant = tenants["graph_research"]
api_key = graph_tenant["api_key"]

print("🔬 Running Probe 2.3: Multi-Hop Knowledge Graph Reasoning Verification...")

# 1. Summary Check
summary_url = "http://localhost:8000/v1/tenants/graph_research/graph"
req_sum = urllib.request.Request(
    summary_url,
    headers={"Authorization": f"Bearer {api_key}"}
)

start = time.perf_counter()
with urllib.request.urlopen(req_sum, timeout=15) as resp:
    duration_sum = (time.perf_counter() - start) * 1000
    data_sum = json.loads(resp.read().decode())
    print(f"\n[Test 1] Graph Summary completed in {round(duration_sum, 2)}ms")
    print(f"  • Storage Engine: {data_sum.get('storage_engine')}")
    print(f"  • Neo4j Status:   {data_sum.get('neo4j_status')}")
    print(f"  • Total Triples:  {data_sum.get('total_triples')}")
    assert data_sum.get("storage_engine") == "neo4j", "Storage engine must be neo4j"
    assert data_sum.get("neo4j_status") == "online", "Neo4j status must be online"
    assert data_sum.get("total_triples", 0) > 0, "Total triples must be > 0"
    print("  ✓ PASS: Neo4j Knowledge Graph summary verified online with active triples!")

# 2. Multi-Hop Query Check
query_url = "http://localhost:8000/v1/tenants/graph_research/graph/query"
payload = {
    "entity": "index sharding",
    "max_hops": 2
}

req_query = urllib.request.Request(
    query_url,
    data=json.dumps(payload).encode(),
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
)

start = time.perf_counter()
with urllib.request.urlopen(req_query, timeout=15) as resp:
    duration_query = (time.perf_counter() - start) * 1000
    data_query = json.loads(resp.read().decode())
    triples = data_query.get("triples", [])
    connected = data_query.get("connected_entities", [])
    print(f"\n[Test 2] Multi-Hop Graph Query completed in {round(duration_query, 2)}ms")
    print(f"  • Root Entity:        {data_query.get('root_entity')}")
    print(f"  • Triples Found:      {len(triples)}")
    print(f"  • Connected Entities: {connected}")
    assert len(triples) > 0, "Must return at least 1 triple"
    for t in triples:
        print(f"    - ({t['subject']}) -[{t['predicate']}]-> ({t['object']}) [conf: {t.get('confidence')}]")
    print("  ✓ PASS: Multi-hop graph query successfully traversed entity relationships!")

print("\n✅ PROBE 2.3 ALL ASSERTIONS PASSED (100% Green)!\n")
