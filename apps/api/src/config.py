import logging
import os
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("api")


class InfraCapabilities:
    """Auto-detect server specs and decide which infra services to enable.

    Checks total physical RAM, Swap memory, and CPU cores at startup.
    Set override env vars (REDIS_ENABLED, BROKER_ENABLED, WORKERS_ENABLED)
    to 'true' or 'false' to bypass auto-detection.
    """

    def __init__(self) -> None:
        self.ram_gb = 0.0
        self.swap_gb = 0.0
        self.total_memory_gb = 0.0
        self.cpu_cores = 1
        try:
            import psutil

            vmem = psutil.virtual_memory()
            smem = psutil.swap_memory()
            self.ram_gb = vmem.total / (1024**3)
            self.swap_gb = smem.total / (1024**3)
            self.total_memory_gb = (vmem.total + smem.total) / (1024**3)
            self.cpu_cores = os.cpu_count() or 1
        except ImportError:
            logger.warning("psutil not installed; infra auto-detection disabled")

    @classmethod
    def detect(cls) -> "InfraCapabilities":
        return cls()

    @property
    def effective_memory_gb(self) -> float:
        return self.ram_gb + self.swap_gb

    @property
    def lean_mode(self) -> bool:
        return self.effective_memory_gb < 2.0

    @property
    def redis_viable(self) -> bool:
        override = os.environ.get("REDIS_ENABLED", "").lower()
        if override in ("true", "1", "yes"):
            return True
        if override in ("false", "0", "no"):
            return False
        return self.effective_memory_gb >= 2.0

    @property
    def broker_viable(self) -> bool:
        override = os.environ.get("BROKER_ENABLED", "").lower()
        if override in ("true", "1", "yes"):
            return True
        if override in ("false", "0", "no"):
            return False
        return self.effective_memory_gb >= 2.0

    @property
    def workers_viable(self) -> bool:
        override = os.environ.get("WORKERS_ENABLED", "").lower()
        if override in ("true", "1", "yes"):
            return True
        if override in ("false", "0", "no"):
            return False
        return self.effective_memory_gb >= 4.0 and self.cpu_cores >= 1

    def log_boot_status(self) -> None:
        mode = (
            "LEAN (synchronous processing)"
            if not self.workers_viable
            else "FULL (async workers available)"
        )
        logger.info(
            "Server specs: %.1f GB physical RAM + %.1f GB Swap (%.1f GB total memory pool), %d CPU core(s)",
            self.ram_gb,
            self.swap_gb,
            self.effective_memory_gb,
            self.cpu_cores,
        )
        logger.info(
            "Redis: %s (need >=2 GB memory pool)",
            "ENABLED" if self.redis_viable else "DISABLED",
        )
        logger.info(
            "RabbitMQ: %s (need >=2 GB memory pool)",
            "ENABLED" if self.broker_viable else "DISABLED",
        )
        logger.info(
            "Celery/Background workers: %s (need >=4 GB memory pool)",
            "ENABLED" if self.workers_viable else "DISABLED",
        )
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
            if self.CORS_ORIGINS == "*":
                logger.warning(
                    "CORS_ORIGINS is set to '*' in production. "
                    "Set CORS_ORIGINS to a comma-separated list of allowed origins."
                )
            if (
                not self.SECRET_KEY
                or len(self.SECRET_KEY) < 32
                or self.SECRET_KEY.startswith("dev-")
            ):
                raise ValueError(
                    "SECRET_KEY must be set to a secure random value of at least 32 characters "
                    "in production. Set SECRET_KEY env var."
                )
            if self.STORAGE_HMAC_KEY == "local-storage-presign-key":
                raise ValueError(
                    "STORAGE_HMAC_KEY must be changed from the default in production. "
                    "Set STORAGE_HMAC_KEY env var to a secure random value."
                )
            if not self.OIDC_AUDIENCE:
                raise ValueError(
                    "OIDC_AUDIENCE must be set to your Google OAuth client ID in production "
                    "so ID tokens are scoped to your app."
                )
            if not self.RATE_LIMIT_ENABLED:
                logger.warning(
                    "RATE_LIMIT_ENABLED is False in production. Set RATE_LIMIT_ENABLED=true "
                    "to protect public endpoints from abuse."
                )
        return self

    # Infrastructure connection strings
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/retriever"
    )
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
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
    S3_ENDPOINT_URL: str | None = None
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str | None = None
    REMOTE_STORAGE_API_URL: str = "https://rag.prateeq.in"

    # Cryptography
    KEY_ENCRYPTION_KEY: str = "dev-key-encryption-key-must-be-32-bytes-long="
    # Session JWT signing secret. Development-only default; production requires a
    # secure random value (enforced by validate_production_secrets).
    SECRET_KEY: str = "dev-retriever-jwt-secret-change-me"

    # Cognitive Provider Keys
    COHERE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    TAVILY_API_KEY: str = ""
    BRAVE_API_KEY: str = ""
    VISION_MODEL: str = "nvidia/nemotron-nano-12b-v2-vl:free"
    DEFAULT_OCR_PROVIDER: str = "rapidocr"
    TEI_RERANK_URL: str | None = None
    SPARSE_SEARCH_PROVIDER: str = "bm25"

    # CORS
    CORS_ORIGINS: str = "https://prateeq.in,https://admin.rag.prateeq.in,http://localhost:3000,http://127.0.0.1:3000,*"

    # Observability & Telemetry
    OTLP_ENDPOINT: str = ""
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_MAX_REQUESTS: int = 100

    # Error Tracking
    SENTRY_DSN: str = ""

    # Storage HMAC signing key for local presigned URLs
    STORAGE_HMAC_KEY: str = "local-storage-presign-key"

    # Remote Storage Fallback
    REMOTE_STORAGE_FALLBACK_URL: str = ""
    INTERNAL_API_KEY: str = ""

    # OIDC & Supabase Auth Settings
    SUPABASE_URL: str = ""
    SUPABASE_JWT_SECRET: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    OIDC_ISSUER_URL: str = ""
    OIDC_JWKS_URI: str = ""
    OIDC_AUDIENCE: str = ""

    # Payment webhooks are deliberately disabled until each provider secret is
    # configured.  Empty values are safer than a development fallback: payment
    # events must never provision a tenant without cryptographic verification.
    STRIPE_WEBHOOK_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    PHONEPE_WEBHOOK_SECRET: str = ""

    @model_validator(mode="after")
    def resolve_supabase_oidc(self):
        if self.SUPABASE_URL:
            base_url = self.SUPABASE_URL.rstrip("/")
            if not self.OIDC_JWKS_URI:
                self.OIDC_JWKS_URI = f"{base_url}/auth/v1/.well-known/jwks.json"
            if not self.OIDC_ISSUER_URL:
                self.OIDC_ISSUER_URL = f"{base_url}/auth/v1"
        return self


settings = Settings()
infra = InfraCapabilities()
infra.log_boot_status()
