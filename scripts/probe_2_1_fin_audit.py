#!/usr/bin/env python3
"""Probe 2.1: Financial Tabular Accuracy & REPL Math (fin_audit)"""
import urllib.request
import json
import time

with open("data/test_tenants.json") as f:
    tenants = json.load(f)

fin_tenant = tenants["fin_audit"]
tenant_id = fin_tenant["tenant_id"]
api_key = fin_tenant["api_key"]

url = "http://localhost:8000/v1/tenants/fin_audit/chat/completions"
payload = {
    "messages": [
        {"role": "user", "content": "What was the total net sales in the most recent fiscal year, and calculate the exact percentage difference compared to the previous year?"}
    ],
    "stream": False,
    "use_repl": True
}

req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode(),
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
)

start = time.perf_counter()
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        duration = (time.perf_counter() - start) * 1000
        data = json.loads(resp.read().decode())
        print(f"✅ Probe 2.1 PASSED ({round(duration, 2)}ms)")
        summary = data.get("analysis_summary", "")
        code_execs = data.get("code_executions", [])
        subcalls = data.get("subcalls_count", 0)
        print(f"  • Summary: {summary[:250]}...")
        print(f"  • Code Executions: {len(code_execs)}")
        for idx, ce in enumerate(code_execs, 1):
            code_snippet = ce.get("code", "")
            ret_val = ce.get("result")
            stdout_val = ce.get("stdout")
            print(f"    [{idx}] Code:\n{code_snippet}\n    -> Result: {ret_val}\n    -> Stdout: {stdout_val}")
        print(f"  • Subcalls: {subcalls}")
except Exception as e:
    duration = (time.perf_counter() - start) * 1000
    print(f"❌ Probe 2.1 FAILED ({round(duration, 2)}ms): {e}")
    if hasattr(e, "read"):
        print(e.read().decode())
