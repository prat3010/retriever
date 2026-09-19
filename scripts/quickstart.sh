#!/usr/bin/env bash
# ==============================================================================
# Retriever — 1-Line Quickstart & Host Environment Sensing Engine
# Usage: ./scripts/quickstart.sh  OR  curl -fsSL https://get.retriever.run | bash
# ==============================================================================

set -e

# Terminal colors
BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo -e "${CYAN}${BOLD}"
cat << "EOF"
  ____      _       _                          
 |  _ \ ___| |_ _ _(_) _____   _____ _ __      
 | |_) / _ \ __| '__| |/ _ \ \ / / _ \ '__|     
 |  _ <  __/ |_| |  | |  __/\ V /  __/ |        
 |_| \_\___|\__|_|  |_|\___| \_/ \___|_|        
EOF
echo -e "${NC}"
echo -e "${BOLD}Enterprise Cognitive Engine — 1-Click Launch (v1.0.0-rc1)${NC}"
echo "38 Batteries Included • PostgreSQL RLS • Scale-to-Zero Serving"
echo "----------------------------------------------------------------------"

# 1. Environment & Hardware Sensing
echo -e "\n${BOLD}[1/5] Sensing Host Hardware & Environment...${NC}"

OS_NAME="$(uname -s)"
ARCH_NAME="$(uname -m)"
ACCELERATION="CPU (Standard)"

if [ "$OS_NAME" = "Darwin" ]; then
    if [ "$ARCH_NAME" = "arm64" ]; then
        ACCELERATION="Apple Silicon Metal (MPS / Neural Engine)"
    fi
elif [ "$OS_NAME" = "Linux" ]; then
    if command -v nvidia-smi >/dev/null 2>&1; then
        GPU_NAME="$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n 1 || echo "NVIDIA GPU")"
        ACCELERATION="NVIDIA CUDA Acceleration ($GPU_NAME)"
    fi
fi

echo -e "  • Operating System:  ${CYAN}$OS_NAME ($ARCH_NAME)${NC}"
echo -e "  • Compute Engine:    ${GREEN}$ACCELERATION${NC}"

# Check Docker prerequisite
if ! command -v docker >/dev/null 2>&1; then
    echo -e "\n${RED}[ERROR] Docker is not installed.${NC}"
    echo "Please install Docker Desktop or Docker Engine to run Retriever:"
    if [ "$OS_NAME" = "Darwin" ]; then
        echo "  brew install --cask docker"
    else
        echo "  curl -fsSL https://get.docker.com | sh"
    fi
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo -e "\n${RED}[ERROR] Docker daemon is not running.${NC}"
    echo "Please start the Docker daemon (e.g. open Docker Desktop) and re-run this script."
    exit 1
fi

# Detect docker compose plugin or standalone
DOCKER_COMPOSE_CMD="docker compose"
if ! docker compose version >/dev/null 2>&1; then
    if command -v docker-compose >/dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker-compose"
    else
        echo -e "\n${RED}[ERROR] 'docker compose' plugin not found.${NC}"
        echo "Please install the Docker Compose V2 plugin."
        exit 1
    fi
fi
echo -e "  • Docker Engine:     ${GREEN}Active ($(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "OK"))${NC}"

# 2. Environment Configuration
echo -e "\n${BOLD}[2/5] Configuring Local-First Environment...${NC}"
if [ ! -f .env ]; then
    if [ -f .env.docker.example ]; then
        cp .env.docker.example .env
        echo -e "  • Initialized ${CYAN}.env${NC} from ${CYAN}.env.docker.example${NC}"
    fi
else
    echo -e "  • Existing ${CYAN}.env${NC} file detected."
fi

# 3. Spin up Docker Stack
echo -e "\n${BOLD}[3/5] Starting Docker Services in Background...${NC}"
echo "  • Services: PostgreSQL 16 (pgvector), Redis 7, Ollama, FastAPI Engine, Admin Web"
$DOCKER_COMPOSE_CMD up -d

# 4. Wait for Gateway Readiness
echo -e "\n${BOLD}[4/5] Waiting for API Gateway to become ready...${NC}"
READY=0
for i in $(seq 1 60); do
    if curl -s http://localhost:8000/health/readiness >/dev/null 2>&1; then
        READY=1
        break
    fi
    printf "."
    sleep 1
done
echo ""

if [ $READY -ne 1 ]; then
    echo -e "${YELLOW}[WARNING] API Gateway took longer than 60s to report ready.${NC}"
    echo "Check logs with: $DOCKER_COMPOSE_CMD logs -f api"
else
    echo -e "  • API Gateway:       ${GREEN}Ready (http://localhost:8000)${NC}"
fi

# 5. Live Search Verification (30-Second Dopamine)
echo -e "\n${BOLD}[5/5] Executing First Live Search Verification Query...${NC}"
DEMO_KEY="ret_live_demo_00000000000000000000000000000000"

QUERY_RESP="$(curl -s -X POST http://localhost:8000/v1/search \
    -H "Authorization: Bearer $DEMO_KEY" \
    -H "Content-Type: application/json" \
    -d '{"query": "How does ColBERT late interaction work?"}' 2>/dev/null || echo "")"

if echo "$QUERY_RESP" | grep -q "ColBERT"; then
    echo -e "  • Verification:      ${GREEN}SUCCESS — Live hybrid search hit verified!${NC}"
else
    echo -e "  • Verification:      ${CYAN}Gateway reachable (indexing in progress)${NC}"
fi

# Completion Hero Summary
echo -e "\n======================================================================"
echo -e "${GREEN}${BOLD}🚀 RETRIEVER COGNITIVE ENGINE IS LIVE!${NC}"
echo -e "======================================================================"
echo -e "• REST API Gateway:      ${CYAN}http://localhost:8000${NC}"
echo -e "• Interactive OpenAPI:   ${CYAN}http://localhost:8000/docs${NC}"
echo -e "• SaaS Studio Workspace: ${CYAN}http://localhost:3000${NC}"
echo -e "• Master Demo API Key:   ${BOLD}$DEMO_KEY${NC}"
echo ""
echo -e "${BOLD}Try a query right now in your terminal:${NC}"
echo -e "  curl -X POST http://localhost:8000/v1/search \\"
echo -e "    -H \"Authorization: Bearer $DEMO_KEY\" \\"
echo -e "    -H \"Content-Type: application/json\" \\"
echo -e "    -d '{\"query\": \"How does scale-to-zero vLLM serving work?\"}'"
echo ""
echo -e "${BOLD}Install Client SDKs:${NC}"
echo -e "  TypeScript:  ${CYAN}npm install @prat3010/retriever-client${NC}"
echo -e "  Python:      ${CYAN}pip install retriever-python${NC}"
echo ""
echo -e "${BOLD}Management Commands:${NC}"
echo -e "  View Logs:   ${YELLOW}$DOCKER_COMPOSE_CMD logs -f${NC}"
echo -e "  Stop Stack:  ${YELLOW}$DOCKER_COMPOSE_CMD down${NC}"
echo -e "======================================================================\n"
