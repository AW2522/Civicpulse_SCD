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

    # Database settings
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


settings = Settings()
