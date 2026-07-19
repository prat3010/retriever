import asyncio

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from src.adapters.database.connection import engine
from src.adapters.cache.config_cache import redis_client
from src.config import settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    environment: str


@router.get("/health/liveness", status_code=status.HTTP_200_OK, response_model=HealthResponse)
async def liveness_probe() -> HealthResponse:
    return HealthResponse(status="alive", environment=settings.ENVIRONMENT)


@router.get("/health/readiness", status_code=status.HTTP_200_OK, response_model=HealthResponse)
async def readiness_probe() -> HealthResponse:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        if redis_client is not None:
            try:
                await redis_client.ping()
            except Exception:
                pass

        return HealthResponse(status="ready", environment=settings.ENVIRONMENT)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Readiness check failed: {e!s}",
        ) from e
