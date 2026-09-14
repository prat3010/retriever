#!/usr/bin/env bash
# ==============================================================================
# Retriever — Root 1-Line Remote Installer
# Usage: curl -fsSL https://get.retriever.run | bash
# ==============================================================================

set -e

REPO_URL="https://github.com/prat3010/retriever.git"
TARGET_DIR="retriever"

# If already inside a retriever repo with scripts/quickstart.sh
if [ -f "./scripts/quickstart.sh" ]; then
    chmod +x ./scripts/quickstart.sh
    exec ./scripts/quickstart.sh "$@"
fi

# Otherwise, clone and launch
echo "Cloning Retriever Enterprise Cognitive Engine repository..."
if [ -d "$TARGET_DIR" ]; then
    echo "Directory '$TARGET_DIR' already exists. Entering directory..."
    cd "$TARGET_DIR"
else
    git clone "$REPO_URL" "$TARGET_DIR"
    cd "$TARGET_DIR"
fi

chmod +x ./scripts/quickstart.sh
exec ./scripts/quickstart.sh "$@"
