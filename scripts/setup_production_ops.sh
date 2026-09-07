#!/usr/bin/env bash
# ==============================================================================
# Retriever Production Operations & Go-Live Server Hardening Script
# Target: Oracle Cloud VPS (Ubuntu 24.04, IP: 130.210.35.134)
# Run as root or with sudo: sudo bash scripts/setup_production_ops.sh
# ==============================================================================

set -euo pipefail

echo "======================================================================"
echo "⚡ RETRIEVER PRODUCTION VPS GO-LIVE HARDENING"
echo "======================================================================"

# 1. Ollama Daemon & nomic-embed-text Weights
echo "▶️ Checking Ollama Local Embedding Daemon..."
if command -v ollama >/dev/null 2>&1; then
    echo "✓ Ollama binary found."
    if systemctl is-active --quiet ollama; then
        echo "✓ Ollama service is active."
    else
        echo "⚠️ Starting Ollama service..."
        systemctl start ollama || true
    fi
    echo "⬇️ Ensuring nomic-embed-text model is cached locally..."
    ollama pull nomic-embed-text || echo "⚠️ Warning: Ollama pull encountered an issue. Verify network."
else
    echo "ℹ️ Ollama not installed globally. Checking if local Docker Ollama is present..."
fi

# 2. Scale Nginx Rate-Limiting Configuration
echo "▶️ Scaling Nginx Rate-Limiter (120 req/min -> 1,000 req/min)..."
NGINX_CONF_DIR="/etc/nginx"
if [ -d "$NGINX_CONF_DIR" ]; then
    # Search for limit_req_zone configurations
    MATCHES=$(grep -rn "limit_req_zone" "$NGINX_CONF_DIR" || true)
    if [ -n "$MATCHES" ]; then
        echo "Found rate-limiting rules in Nginx. Updating zone rates..."
        # Update 120r/m or similar to 1000r/m
        find "$NGINX_CONF_DIR" -type f -name "*.conf" -exec sed -i 's/rate=120r\/m/rate=1000r\/m/g' {} +
        find "$NGINX_CONF_DIR" -type f -name "*.conf" -exec sed -i 's/rate=2r\/s/rate=50r\/s/g' {} +
    fi
    if nginx -t 2>/dev/null; then
        systemctl reload nginx
        echo "✓ Nginx reloaded successfully with scaled rate limits."
    else
        echo "⚠️ Nginx test failed. Manual inspection required in /etc/nginx."
    fi
else
    echo "ℹ️ Nginx configuration directory not found at /etc/nginx."
fi

# 3. Automated Daily PostgreSQL Backup Cron
echo "▶️ Installing Automated Daily PostgreSQL Backup Cron (02:00 UTC)..."
BACKUP_SCRIPT="/opt/retriever/current/scripts/backup-db.sh"
CRON_FILE="/etc/cron.d/retriever-backup"

if [ -f "$BACKUP_SCRIPT" ]; then
    chmod +x "$BACKUP_SCRIPT"
    cat <<EOF > "$CRON_FILE"
# Automated Nightly Logical Database Backup
0 2 * * * root /bin/bash /opt/retriever/current/scripts/backup-db.sh /opt/retriever/.env >> /var/log/retriever-backup.log 2>&1
EOF
    chmod 644 "$CRON_FILE"
    echo "✓ Daily cron registered at $CRON_FILE (Runs 02:00 UTC daily)."
else
    echo "⚠️ Backup script not found at $BACKUP_SCRIPT. Skipped cron registration."
fi

# 4. Celery / Background Ingestion Worker Status
echo "▶️ Inspecting Background Ingestion Worker..."
if systemctl list-unit-files | grep -q "retriever-worker"; then
    if systemctl is-active --quiet retriever-worker; then
        echo "✓ retriever-worker.service is active (running)."
    else
        echo "⚠️ Starting retriever-worker.service..."
        systemctl restart retriever-worker || true
    fi
else
    echo "ℹ️ Background worker unit retriever-worker.service not registered in systemd."
fi

echo "======================================================================"
echo "🎉 VPS Production Hardening Completed!"
echo "======================================================================"
