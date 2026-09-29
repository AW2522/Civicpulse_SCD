from typing import Literal

from pydantic import model_validator
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

    # Database settings
    POSTGRES_HOST: str | None = None
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_DB: str | None = None
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/civicpulse"
    
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

    @model_validator(mode="after")
    def assemble_db_connection(self) -> "Settings":
        if self.POSTGRES_HOST and self.POSTGRES_USER and self.POSTGRES_DB:
            password = f":{self.POSTGRES_PASSWORD}" if self.POSTGRES_PASSWORD else ""
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}{password}@"
                f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return self


settings = Settings()
