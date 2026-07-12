from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config import settings

app = FastAPI(
    title="Retriever Core Platform",
    description="Headless Multi-Tenant AI Knowledge Platform Memory Layer API",
    version="0.1.0",
)

# Configure CORS for reference applications and SDK access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to configured domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    environment: str


@app.get("/health/liveness", status_code=status.HTTP_200_OK, response_model=HealthResponse)
async def liveness_probe() -> HealthResponse:
    """Liveness probe to confirm the API server process is running."""
    return HealthResponse(status="alive", environment=settings.ENVIRONMENT)


@app.get("/health/readiness", status_code=status.HTTP_200_OK, response_model=HealthResponse)
async def readiness_probe() -> HealthResponse:
    """Readiness probe to confirm external infrastructure connections are active."""
    # Readiness checks for DB, Redis, and RabbitMQ will be added in subsequent milestones
    return HealthResponse(status="ready", environment=settings.ENVIRONMENT)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Retriever Core Platform API. Visit /docs for Swagger UI."}
