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
    REDIS_URL: str = "redis://localhost:6379/0"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672//"

    # Storage Settings
    STORAGE_BUCKET: str = "retriever-documents"

    # Cognitive Provider Keys
    COHERE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""

    # CORS
    CORS_ORIGINS: str = "*"

    # Observability & Telemetry
    OTLP_ENDPOINT: str = ""
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_MAX_REQUESTS: int = 100

    # Error Tracking
    SENTRY_DSN: str = ""


settings = Settings()
