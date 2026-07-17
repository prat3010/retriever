# Build phase using official Python slim image
FROM python:3.11-slim as base

# Set env policies
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

# Install system dependencies (including Ollama)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama binary directly (no install script - avoids systemd/GPU detection issues)
RUN curl -fsSL https://github.com/ollama/ollama/releases/download/v0.5.4/ollama-linux-amd64.tgz | tar xz -C /usr/local/

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin/:$PATH"

# Copy package locks and install requirements
COPY apps/api/pyproject.toml ./pyproject.toml
RUN uv pip compile pyproject.toml -o requirements.txt && uv pip install --system -r requirements.txt

# Pre-download the embedding model during build (build env has more RAM, less OOM risk)
# GPU detection forced off to avoid build failures in headless CI
ENV CUDA_VISIBLE_DEVICES=-1
RUN ollama serve > /dev/null 2>&1 & sleep 3 && ollama pull nomic-embed-text && kill %1 2>/dev/null; true

# Copy application source
COPY deploy/start.py ./deploy/start.py
COPY apps/api/src/ ./src/

# Copy shared processing-core package
COPY packages/processing-core /app/packages/processing-core
ENV PYTHONPATH="/app/packages/processing-core/src:${PYTHONPATH}"

ENV EMBEDDING_PROVIDER=ollama

EXPOSE 8000

# Start both Ollama and uvicorn
CMD python /app/deploy/start.py
