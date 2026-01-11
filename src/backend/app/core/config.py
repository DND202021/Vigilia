"""Application configuration using Pydantic Settings."""

import os
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "ERIOP"
    debug: bool = False
    environment: str = "development"
    port: int = 8000

    # Security
    secret_key: str = "CHANGE-THIS-IN-PRODUCTION"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Database - Railway provides DATABASE_URL
    database_url: str = "postgresql+asyncpg://eriop:eriop@localhost:5432/eriop"

    # Redis - Railway provides REDIS_URL
    redis_url: str = "redis://localhost:6379/0"

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        """Convert standard postgres:// URL to asyncpg format."""
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://") and "+asyncpg" not in v:
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # MQTT (Fundamentum)
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_username: str = ""
    mqtt_password: str = ""

    # CORS - accepts comma-separated string or JSON array
    cors_origins_str: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        value = self.cors_origins_str
        if value.startswith("["):
            import json
            return json.loads(value)
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    # Logging
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
