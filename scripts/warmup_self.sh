#!/usr/bin/env bash
# Keep the local Retriever API and embedding path warm from a systemd timer.
# Credentials live in a root/ubuntu-readable env file, never in this script.
set -euo pipefail

ENV_FILE="${RETRIEVER_WARMUP_ENV_FILE:-/etc/retriever-warmup.env}"
API_URL="${RETRIEVER_WARMUP_API_URL:-http://127.0.0.1:8000}"

if [ ! -r "$ENV_FILE" ]; then
    echo "warmup: env file is not readable: $ENV_FILE" >&2
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${WARMUP_TENANT_ID:?WARMUP_TENANT_ID is required}"
: "${WARMUP_API_KEY:?WARMUP_API_KEY is required}"

echo "warmup: probing tenant ${WARMUP_TENANT_ID} via ${API_URL}"
curl --fail --silent --show-error --max-time 60 \
    --request POST \
    --header "Authorization: Bearer ${WARMUP_API_KEY}" \
    --header "Content-Type: application/json" \
    --data '{}' \
    "${API_URL%/}/v1/tenants/${WARMUP_TENANT_ID}/warmup"
echo
