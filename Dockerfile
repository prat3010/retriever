FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin/:$PATH"

COPY apps/api/pyproject.toml ./pyproject.toml
RUN uv pip compile pyproject.toml -o requirements.txt && uv pip install --system -r requirements.txt

COPY apps/api/src/ ./src/
COPY packages/processing-core /app/packages/processing-core
ENV PYTHONPATH="/app/packages/processing-core/src:${PYTHONPATH}"

EXPOSE 8000
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}
