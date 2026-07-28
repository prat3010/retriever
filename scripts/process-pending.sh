#!/usr/bin/env bash
set -e

# Resolve repository root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Retriever Batch Ingestion: Processing PENDING Documents ==="
PYTHONPATH="$ROOT_DIR/apps/api:$ROOT_DIR/packages/processing-core/src" \
  uv run python -m src.scripts.process_pending "$@"
