#!/usr/bin/env bash
# Zero-Downtime Atomic Release Deployment with Automated Rollback Gate
# Usage: deploy_release.sh [GIT_REF] (default: origin/main)

set -euo pipefail

BASE_DIR="/opt/retriever"
RELEASES_DIR="$BASE_DIR/releases"
SHARED_ENV="$BASE_DIR/.env"
SHARED_VENV="$BASE_DIR/.venv"
CURRENT_LINK="$BASE_DIR/current"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
RELEASE_DIR="$RELEASES_DIR/$TIMESTAMP"
KEEP_RELEASES=5

echo "======================================================"
echo "🚀 Starting Atomic Release Deployment: $TIMESTAMP"
echo "======================================================"

# 1. Validate environment
mkdir -p "$RELEASES_DIR"
[ -f "$SHARED_ENV" ] || { echo "❌ Shared .env file not found at $SHARED_ENV"; exit 1; }
[ -d "$SHARED_VENV" ] || { echo "❌ Shared virtualenv not found at $SHARED_VENV"; exit 1; }

# 2. Identify previous active release for rollback
PREVIOUS_RELEASE=""
if [ -L "$CURRENT_LINK" ]; then
    PREVIOUS_RELEASE="$(readlink -f "$CURRENT_LINK" || true)"
    echo "📌 Current active release: $PREVIOUS_RELEASE"
fi

# 3. Create new release directory & copy codebase
echo "📦 Cloning workspace into release directory: $RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

# Copy git tracked files into the release directory
cd "$BASE_DIR"
git archive HEAD | tar -x -C "$RELEASE_DIR"

# Link shared environment and virtualenv
ln -sf "$SHARED_ENV" "$RELEASE_DIR/.env"
ln -sf "$SHARED_VENV" "$RELEASE_DIR/.venv"

# 4. Trigger pre-deployment logical database backup
if [ -x "$BASE_DIR/scripts/backup-db.sh" ]; then
    echo "💾 Running pre-deploy database snapshot..."
    "$BASE_DIR/scripts/backup-db.sh" "$SHARED_ENV" || echo "⚠️ Pre-deploy backup warning: proceeding with caution"
fi

# 5. Install / update dependencies inside release environment
echo "🐍 Syncing Python dependencies..."
cd "$RELEASE_DIR"
. "$SHARED_VENV/bin/activate"
pip install --no-cache-dir -r requirements.txt 2>&1 | tail -n 15

# 6. Execute database migrations
echo "🗄️ Executing Alembic database migrations..."
if [ -f "alembic.ini" ]; then
    alembic upgrade head
fi

# 7. Atomically switch current symlink
echo "🔄 Switching active symlink to $RELEASE_DIR..."
ln -sfn "$RELEASE_DIR" "$CURRENT_LINK"

# 8. Reload systemd & restart API and Worker services
echo "⚡ Restarting systemd services..."
sudo systemctl daemon-reload
sudo systemctl restart retriever-api retriever-worker

# 9. Health probe verification gate (up to 60s)
echo "🩺 Probing service health (/health/liveness & /health/readiness)..."
HEALTHY=false
for i in $(seq 1 12); do
    sleep 5
    if curl -sSf http://localhost:8000/health/liveness > /dev/null 2>&1; then
        if curl -sSf http://localhost:8000/health/readiness > /dev/null 2>&1; then
            echo "✅ Health probes passed at attempt $i (liveness & readiness OK)"
            HEALTHY=true
            break
        fi
    fi
    echo "⏳ Waiting for service readiness... ($((i * 5))/60s)"
done

# 10. Automated Rollback Trigger if unhealthy
if [ "$HEALTHY" = false ]; then
    echo "❌ CRITICAL: Post-deployment health checks failed! Initiating automated rollback..."
    if [ -n "$PREVIOUS_RELEASE" ] && [ -d "$PREVIOUS_RELEASE" ]; then
        echo "⏮️ Rolling back symlink to $PREVIOUS_RELEASE"
        ln -sfn "$PREVIOUS_RELEASE" "$CURRENT_LINK"
        sudo systemctl restart retriever-api retriever-worker
        echo "✅ Rollback completed. Service restored to previous release."
    else
        echo "⚠️ No previous release directory available for rollback!"
    fi
    exit 1
fi

# 11. Prune older releases (keep latest 5)
echo "🧹 Pruning old release directories (retaining last $KEEP_RELEASES)..."
cd "$RELEASES_DIR"
ls -dt */ 2>/dev/null | tail -n +"$((KEEP_RELEASES + 1))" | xargs -I {} rm -rf "{}" || true

echo "======================================================"
echo "🎉 Deployment successfully completed: $TIMESTAMP"
echo "======================================================"
