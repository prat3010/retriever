import json
import os
import subprocess
import sys
import time
import urllib.request

PORT = os.environ.get("PORT", "8000")

ollama = subprocess.Popen(["ollama", "serve"])

for _ in range(60):
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        break
    except Exception:
        time.sleep(1)
else:
    print("Ollama failed to start", flush=True)
    ollama.kill()
    sys.exit(1)

subprocess.run(["ollama", "pull", "nomic-embed-text"], capture_output=True, timeout=180)

# pre-warm: force model load into memory before uvicorn starts
for _ in range(30):
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/embeddings",
            data=json.dumps({"model": "nomic-embed-text", "prompt": "ping"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
        break
    except Exception:
        time.sleep(2)

uvicorn = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", PORT]
)
uvicorn.wait()
