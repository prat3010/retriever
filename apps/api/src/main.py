import hashlib
import logging
import os
import sys
import traceback
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text

from src.adapters.database.connection import engine
from src.adapters.telemetry.setup import init_telemetry
from src.config import settings
from src.domain.abstractions.exceptions import (
    AuthenticationError,
    TenantIsolationViolationError,
)




@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger = logging.getLogger("api")
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Eagerly warmed up database connection pool.")
    except Exception as e:
        logger.error(f"Failed to warm up database connection pool: {e}")

    if settings.SENTRY_DSN:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.opentelemetry import OpenTelemetryIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
            send_default_pii=False,
            integrations=[
                FastApiIntegration(),
                OpenTelemetryIntegration(),
            ],
        )
    yield
    # Flush pending telemetry on shutdown
    if settings.SENTRY_DSN:
        import sentry_sdk
        sentry_sdk.flush()
    try:
        from src.adapters.telemetry.setup import get_tracer
        tracer = get_tracer()
        if tracer:
            tracer.force_flush()
    except Exception:
        pass


app = FastAPI(
    title="Retriever Core Platform",
    description="Headless Multi-Tenant AI Knowledge Platform Memory Layer API",
    version="0.1.0",
    lifespan=lifespan,
)

# Initialise telemetry subsystems at import time
init_telemetry(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
from src.container import *


@app.exception_handler(Exception)
async def handle_unhandled(request, exc):
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    print(f"Unhandled exception: {exc}\n{tb}", file=sys.stderr)
    return JSONResponse(status_code=500, content={"detail": str(exc), "traceback": tb})

@app.exception_handler(TenantIsolationViolationError)
async def handle_isolation_violation(request, exc):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=str(exc),
    )

@app.exception_handler(AuthenticationError)
async def handle_auth_error(request, exc):
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=str(exc),
    )



# --- Router Includes ---

from src.routers.admin import router as admin_router
from src.routers.chat import router as chat_router
from src.routers.document import router as document_router
from src.routers.health import router as health_router
from src.routers.search import router as search_router
from src.routers.tenant import router as tenant_router

app.include_router(health_router)
app.include_router(admin_router)
app.include_router(chat_router)
app.include_router(document_router)
app.include_router(search_router)
app.include_router(tenant_router)

@app.get(
    "/v1/local-downloads/{tenantId}/{filename}",
    status_code=status.HTTP_200_OK,
)
async def serve_local_download(
    tenantId: str,
    filename: str,
    expires: int,
    signature: str,
) -> Any:
    """Securely serve local document files after validating temporary HMAC signature (Local dev only)."""
    import hmac
    import time

    from src.adapters.storage.local_storage import LocalStorage

    # 1. Check expiration
    if int(time.time()) > expires:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="This download link has expired.")

    # 2. Verify signature
    relative_path = f"{tenantId}/{filename}"
    secret_key = settings.STORAGE_HMAC_KEY.encode()
    msg = f"{relative_path}:{expires}".encode()
    expected_sig = hmac.new(secret_key, msg=msg, digestmod=hashlib.sha256).hexdigest()

    if not hmac.compare_digest(signature, expected_sig):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature.")

    # 3. Serve file from local storage directory
    if not isinstance(local_storage, LocalStorage):
        raise HTTPException(status_code=500, detail="Local downloads are only supported in local storage mode.")

    file_path = os.path.join(local_storage.storage_dir, tenantId, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk.")

    return FileResponse(file_path, media_type="application/octet-stream", filename=filename)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Retriever Core Platform API. Visit /docs for Swagger UI."}


