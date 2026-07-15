from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Core environment details
    ENVIRONMENT: Literal["development", "production", "testing"] = "development"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    ADMIN_MASTER_KEY: str = "dev-admin-master-key-change-in-production"

    # Infrastructure connection strings
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/retriever"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    REDIS_URL: str = "redis://localhost:6379/0"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672//"

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

    # OIDC Settings
    OIDC_ISSUER_URL: str = ""
    OIDC_JWKS_URI: str = ""
    OIDC_AUDIENCE: str = ""


settings = Settings()
