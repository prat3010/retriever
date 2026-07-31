#!/usr/bin/env bash
# LLM key quota alerting for the platform's own provider key(s).
#
# The platform routes LLM traffic through OpenRouter (OPENAI_BASE_URL), so the
# key is checked against OpenRouter's /auth/key usage endpoint. Alerts fire
# when remaining credit < 20% and again < 10%.
#
# Alert channels (both optional):
#   NTFY_TOPIC   — ntfy.sh push topic (subscribe in the ntfy app, no account)
#   ALERT_WEBHOOK — generic webhook (Slack/Discord incoming webhook URL)
#
# Usage: quota-alert.sh [/path/to/.env]   (default /opt/retriever/.env)
set -euo pipefail

ENV_FILE="${1:-/opt/retriever/.env}"
LOGDIR="$(dirname "$ENV_FILE")/logs"
mkdir -p "$LOGDIR"
LOG="$LOGDIR/quota-alert.log"

[ -f "$ENV_FILE" ] || { echo "env file not found: $ENV_FILE"; exit 1; }

KEY="$(grep '^OPENAI_API_KEY=' "$ENV_FILE" | cut -d= -f2- || true)"
BASE="$(grep '^OPENAI_BASE_URL=' "$ENV_FILE" | cut -d= -f2- || true)"
if [ -z "${KEY:-}" ]; then
    echo "$(date -u +%FT%TZ) no platform LLM key (BYOK mode) — nothing to monitor" >> "$LOG"
    exit 0
fi

notify() {
    local msg="$1"
    echo "$(date -u +%FT%TZ) $msg" >> "$LOG"
    local topic="${NTFY_TOPIC:-}"
    if [ -n "$topic" ]; then
        curl -s -m 10 -d "$msg" "https://ntfy.sh/$topic" > /dev/null 2>&1 || true
    fi
    local webhook="${ALERT_WEBHOOK:-}"
    if [ -n "$webhook" ]; then
        curl -s -m 10 -H 'Content-Type: application/json' \
            -d "{\"text\": \"$msg\"}" "$webhook" > /dev/null 2>&1 || true
    fi
}

# OpenRouter key usage endpoint; falls back to OpenAI billing API otherwise
if [[ "$BASE" == *openrouter* ]]; then
    RESP="$(curl -s -m 15 -H "Authorization: Bearer $KEY" https://openrouter.ai/api/v1/auth/key)"
    USAGE="$(echo "$RESP" | python3 -c "import sys,json;d=json.load(sys.stdin).get('data',{});print(d.get('usage') or 0)" 2>/dev/null || echo 0)"
    LIMIT="$(echo "$RESP" | python3 -c "import sys,json;d=json.load(sys.stdin).get('data',{});print(d.get('limit') or 0)" 2>/dev/null || echo 0)"
else
    RESP="$(curl -s -m 15 -H "Authorization: Bearer $KEY" https://api.openai.com/v1/dashboard/billing/subscription)"
    LIMIT="$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('hard_limit_usd') or 0)" 2>/dev/null || echo 0)"
    USAGE="$(curl -s -m 15 -H "Authorization: Bearer $KEY" "https://api.openai.com/v1/dashboard/billing/usage?start_date=$(date -u -d '-30 days' +%Y-%m-%d 2>/dev/null || date -v-30d -u +%Y-%m-%d)" | python3 -c "import sys,json;print(json.load(sys.stdin).get('total_usage') or 0)" 2>/dev/null || echo 0)"
    USAGE="$(echo "$USAGE / 100" | bc -l 2>/dev/null || echo "$USAGE")"
fi

LIMIT_F="$(echo "$LIMIT" | python3 -c "import sys;print(float(sys.stdin.read()))" 2>/dev/null || echo 0)"
if [ "$(echo "$LIMIT_F > 0" | bc 2>/dev/null || echo 0)" != "1" ]; then
    notify "Retriever: LLM key is free-tier or unlimited — quota not monitorable, consider prepaid key"
    exit 0
fi

PCT="$(echo "scale=1; $USAGE * 100 / $LIMIT" | bc 2>/dev/null || echo 0)"
echo "$(date -u +%FT%TZ) usage \$$USAGE / limit \$$LIMIT ($PCT%)" >> "$LOG"
if [ "$(echo "$PCT >= 90" | bc 2>/dev/null || echo 0)" = "1" ]; then
    notify "CRITICAL: Retriever LLM credit ${PCT}% used (\$$USAGE/\$$LIMIT)"
elif [ "$(echo "$PCT >= 80" | bc 2>/dev/null || echo 0)" = "1" ]; then
    notify "WARNING: Retriever LLM credit ${PCT}% used (\$$USAGE/\$$LIMIT) — top up soon"
fi
