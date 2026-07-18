#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# Check for DATABASE_URL in .env
if ! grep -q "^DATABASE_URL=" .env 2>/dev/null; then
    echo "ERROR: DATABASE_URL not found in .env"
    echo "Add: DATABASE_URL=postgresql+asyncpg://..."
    exit 1
fi

# 1. Start Ollama if not running
OLLAMA_PID=""
if ! pgrep -x ollama > /dev/null; then
    echo "Starting Ollama..."
    ollama serve &
    OLLAMA_PID=$!
    sleep 2
else
    echo "Ollama already running"
fi

# 2. Start API on :8000
echo "Starting API on :8000..."
source "$ROOT_DIR/apps/api/.venv/bin/activate"
export EMBEDDING_PROVIDER=ollama
export OLLAMA_BASE_URL=http://localhost:11434
PYTHONPATH="$ROOT_DIR/apps/api:$ROOT_DIR/packages/processing-core/src" \
    uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload &
API_PID=$!

# 3. Start dashboard on :3000
echo "Starting dashboard on :3000..."
npm --prefix "$ROOT_DIR/apps/web" run dev &
DASHBOARD_PID=$!

trap '
    echo "Shutting down...";
    kill $API_PID $DASHBOARD_PID 2>/dev/null;
    [ -n "$OLLAMA_PID" ] && kill $OLLAMA_PID 2>/dev/null;
    echo "Done.";
' EXIT INT TERM

echo ""
echo "  API:       http://localhost:8000"
echo "  Dashboard: http://localhost:3000"
echo "  Ctrl+C to stop all"
echo ""

wait
