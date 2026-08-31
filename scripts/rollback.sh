#!/usr/bin/env bash
# Instant Rollback to Previous Release Directory
# Usage: rollback.sh

set -euo pipefail

BASE_DIR="/opt/retriever"
RELEASES_DIR="$BASE_DIR/releases"
CURRENT_LINK="$BASE_DIR/current"

echo "======================================================"
echo "⏮️ Initiating Instant Rollback"
echo "======================================================"

[ -d "$RELEASES_DIR" ] || { echo "❌ Releases directory not found at $RELEASES_DIR"; exit 1; }

CURRENT_TARGET=""
if [ -L "$CURRENT_LINK" ]; then
    CURRENT_TARGET="$(readlink -f "$CURRENT_LINK" || true)"
    echo "📌 Active target: $CURRENT_TARGET"
fi

# Find the second most recent release directory
PREV_RELEASE="$(ls -dt "$RELEASES_DIR"/*/ 2>/dev/null | sed -e 's/\/$//' | grep -v "^${CURRENT_TARGET}$" | head -n 1 || true)"

if [ -z "$PREV_RELEASE" ] || [ ! -d "$PREV_RELEASE" ]; then
    echo "❌ No previous release found to rollback to!"
    exit 1
fi

echo "🔄 Switching symlink $CURRENT_LINK -> $PREV_RELEASE"
ln -sfn "$PREV_RELEASE" "$CURRENT_LINK"

echo "⚡ Restarting systemd services..."
sudo systemctl daemon-reload
sudo systemctl restart retriever-api retriever-worker

echo "🩺 Verifying health of rolled-back service..."
sleep 3
if curl -sSf http://localhost:8000/health/liveness > /dev/null 2>&1; then
    echo "✅ Service successfully restored to $PREV_RELEASE and responding healthy."
else
    echo "⚠️ Warning: Service restarted but liveness check did not return 200 immediately."
fi

echo "======================================================"
echo "🎉 Rollback complete"
echo "======================================================"
