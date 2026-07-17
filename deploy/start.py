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

uvicorn = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", PORT]
)
uvicorn.wait()
