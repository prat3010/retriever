import logging
import os
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("api")


class InfraCapabilities:
    """Auto-detect server specs and decide which infra services to enable.

    Checks total RAM and CPU cores at startup. Set override env vars
    (REDIS_ENABLED, BROKER_ENABLED, WORKERS_ENABLED) to 'true' or 'false'
    to bypass auto-detection.
    """

    def __init__(self) -> None:
        self.ram_gb = 0.0
        self.cpu_cores = 1
        try:
            import psutil
            self.ram_gb = psutil.virtual_memory().total / (1024 ** 3)
            self.cpu_cores = os.cpu_count() or 1
        except ImportError:
            logger.warning("psutil not installed; infra auto-detection disabled")

    @property
    def redis_viable(self) -> bool:
        return self.ram_gb >= 2.0

    @property
    def broker_viable(self) -> bool:
        return self.ram_gb >= 2.0

    @property
    def workers_viable(self) -> bool:
        return self.ram_gb >= 4.0 and self.cpu_cores >= 2

    def log_boot_status(self) -> None:
        mode = "LEAN (synchronous processing)" if not self.workers_viable else "FULL (async workers available)"
        logger.info("Server specs: %.1f GB RAM, %d CPU core(s)", self.ram_gb, self.cpu_cores)
        logger.info("Redis: %s (need >=2 GB RAM)", "ENABLED" if self.redis_viable else "DISABLED")
        logger.info("RabbitMQ: %s (need >=2 GB RAM)", "ENABLED" if self.broker_viable else "DISABLED")
        logger.info("Celery workers: %s (need >=4 GB RAM, >=2 cores)", "ENABLED" if self.workers_viable else "DISABLED")
        logger.info("Running in %s mode", mode)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Core environment details
    ENVIRONMENT: Literal["development", "production", "testing"] = "development"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    ADMIN_MASTER_KEY: str = "dev-admin-master-key-change-in-production"

    @model_validator(mode="after")
    def detect_render(self):
        if self.ENVIRONMENT == "development" and os.environ.get("RENDER"):
            self.ENVIRONMENT = "production"
        return self

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.ENVIRONMENT == "production":
            if self.ADMIN_MASTER_KEY == "dev-admin-master-key-change-in-production":
                raise ValueError(
                    "ADMIN_MASTER_KEY must be changed from the default in production. "
                    "Set ADMIN_MASTER_KEY env var to a secure random value."
                )
            if self.KEY_ENCRYPTION_KEY.startswith("dev-key"):
                raise ValueError(
                    "KEY_ENCRYPTION_KEY must be set to a secure 32-byte key in production. "
                    "Set KEY_ENCRYPTION_KEY env var to a base64 or hex-encoded 32-byte value."
                )
        return self

    # Infrastructure connection strings
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/retriever"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    REDIS_URL: str = "redis://localhost:6379/0"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672//"

    # Infra auto-detection (auto/true/false — auto detects from server specs)
    REDIS_ENABLED: str = "auto"
    BROKER_ENABLED: str = "auto"
    WORKERS_ENABLED: str = "auto"

    # Storage Settings
    STORAGE_PROVIDER: Literal["local", "s3"] = "local"
    STORAGE_BUCKET: str = "retriever-documents"
    S3_ENDPOINT_URL: str | None = None
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str | None = None

    # Cryptography
    KEY_ENCRYPTION_KEY: str = "dev-key-encryption-key-must-be-32-bytes-long="

    # Cognitive Provider Keys
    COHERE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    TAVILY_API_KEY: str = ""
    BRAVE_API_KEY: str = ""
    VISION_MODEL: str = "gpt-4o"

    # CORS
    CORS_ORIGINS: str = "*"

    # Observability & Telemetry
    OTLP_ENDPOINT: str = ""
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_MAX_REQUESTS: int = 100

    # Error Tracking
    SENTRY_DSN: str = ""

    # Remote Storage Fallback
    REMOTE_STORAGE_FALLBACK_URL: str = ""
    INTERNAL_API_KEY: str = ""

    # OIDC Settings
    OIDC_ISSUER_URL: str = ""
    OIDC_JWKS_URI: str = ""
    OIDC_AUDIENCE: str = ""


settings = Settings()
infra = InfraCapabilities()
infra.log_boot_status()
