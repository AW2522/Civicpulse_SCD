import os
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application settings
    APP_NAME: str = "CivicPulse API"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Individual Postgres environment variables (from Docker Compose / K8s ConfigMap & Secret)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "civicpulse"
    POSTGRES_USER: str = "civicpulse"
    POSTGRES_PASSWORD: str = "postgres"

    # Redis settings
    REDIS_URL: str = "redis://localhost:6379/0"

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 5
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # AI Triage Layer Settings
    TRIAGE_PROVIDER: Literal["simulated", "rules", "llm"] = "simulated"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TIMEOUT_SECONDS: float = 10.0
    CACHE_TRIAGE_TTL_SECONDS: int = 86400  # 24 hours

    @property
    def DATABASE_URL(self) -> str:
        """
        Dynamically constructs PostgreSQL connection string from individual POSTGRES_* env vars.
        If DATABASE_URL environment variable is explicitly set, uses that instead.
        """
        explicit_url = os.environ.get("DATABASE_URL")
        if explicit_url:
            return explicit_url
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
