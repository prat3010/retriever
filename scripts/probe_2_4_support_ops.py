#!/usr/bin/env python3
"""Probe 2.4: Conversational Long-Horizon Memory (support_ops)"""
import urllib.request
import json
import time

with open("data/test_tenants.json") as f:
    tenants = json.load(f)

support_tenant = tenants["support_ops"]
api_key = support_tenant["api_key"]

print("🔬 Running Probe 2.4: Conversational Long-Horizon Memory Verification...")

# 1. Create a persistent chat session
create_session_url = "http://localhost:8000/v1/tenants/support_ops/chat/sessions"
req_session = urllib.request.Request(
    create_session_url,
    data=b"{}",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
)

with urllib.request.urlopen(req_session, timeout=15) as resp:
    sess_data = json.loads(resp.read().decode())
    session_id = sess_data["sessionId"]
    print(f"  • Created Session: {session_id}")

msg_url = f"http://localhost:8000/v1/tenants/support_ops/chat/sessions/{session_id}/messages"

turns = [
    ("Turn 1 (State Tracking ID)", "My tracking ID is TRK-88192 and my package was damaged."),
    ("Turn 2 (Distractor Query)", "What is your standard return window policy?"),
    ("Turn 3 (Recall & RMA Request)", "Can you initiate an RMA for my order?")
]

for turn_label, turn_content in turns:
    payload = {
        "query": turn_content,
        "stream": False
    }
    req_msg = urllib.request.Request(
        msg_url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req_msg, timeout=45) as resp:
        duration = (time.perf_counter() - start) * 1000
        data = json.loads(resp.read().decode())
        content = data.get("content", "")
        snippet = content[:200].replace("\n", " ")
        print(f"\n[{turn_label}] ({round(duration, 2)}ms)")
        print(f"  • User: {turn_content}")
        print(f"  • Assistant: {snippet}...")
        
        if "Turn 3" in turn_label:
            assert "TRK-88192" in content or "88192" in content, (
                f"Expected tracking ID 'TRK-88192' in Turn 3 response, but got: {content}"
            )
            print("  ✓ PASS: Agent automatically recalled 'TRK-88192' from episodic memory!")

print("\n✅ PROBE 2.4 ALL ASSERTIONS PASSED (100% Green)!\n")
