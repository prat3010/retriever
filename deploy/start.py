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

# Model is pre-downloaded during Docker build — pull not needed at startup.

# Start uvicorn first so health checks pass within Render's startup window
uvicorn = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", PORT]
)

# Give uvicorn a moment to bind, then pre-warm the model in foreground
time.sleep(3)
try:
    req = urllib.request.Request(
        "http://localhost:11434/api/embeddings",
        data=b'{"model":"nomic-embed-text","prompt":"ping"}',
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=120)
except Exception:
    pass  # pre-warm is best-effort; search can trigger model load too

uvicorn.wait()
