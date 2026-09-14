#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "🚀 Initializing Retriever Enterprise Cognitive Engine..."
echo "=========================================================="

# Wait for database connection
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for database to become available..."
    for i in $(seq 1 30); do
        python3 -c "
import asyncio, os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
async def check():
    url = os.environ.get('DATABASE_URL')
    engine = create_async_engine(url)
    async with engine.connect() as conn:
        await conn.execute(text('SELECT 1'))
    await engine.dispose()
try:
    asyncio.run(check())
    exit(0)
except Exception:
    exit(1)
" 2>/dev/null && break
        echo "Database unavailable, waiting 2s ($i/30)..."
        sleep 2
    done
fi

echo "Running database schema migrations..."
cd /app/apps/api
alembic upgrade head || {
    echo "Warning: Alembic migration encountered an issue, proceeding with fallback..."
}

echo "Seeding demo tenant and master demo key..."
python3 /app/scripts/seed_demo_tenant.py || {
    echo "Warning: Demo seeding warning, proceeding to start service..."
}

echo "Starting Uvicorn HTTP server on :8000..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --log-level info
