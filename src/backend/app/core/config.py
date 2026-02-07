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
    mqtt_broker_host: str = ""  # Empty = disabled
    mqtt_broker_port: int = 1883
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_topic_prefix: str = "fundamentum/alerts"

    # MQTT (Vigilia IoT Broker)
    mqtt_enabled: bool = False                      # Master switch for Vigilia MQTT service
    mqtt_vigilia_broker_host: str = "mosquitto"     # Docker service name
    mqtt_vigilia_broker_port: int = 8883            # TLS port
    mqtt_vigilia_ca_cert: str = "/mosquitto/certs/ca.crt"
    mqtt_vigilia_client_cert: str = "/mosquitto/certs/internal-client.crt"
    mqtt_vigilia_client_key: str = "/mosquitto/certs/internal-client.key"
    mqtt_vigilia_client_id: str = "vigilia-backend"
    mqtt_vigilia_reconnect_interval: int = 5        # Initial reconnect delay in seconds
    mqtt_vigilia_max_reconnect_interval: int = 60   # Max reconnect delay in seconds

    # Telemetry Worker
    telemetry_worker_enabled: bool = True
    telemetry_worker_batch_size: int = 1000
    telemetry_worker_batch_timeout: float = 5.0
    telemetry_worker_num_workers: int = 2
    telemetry_worker_stream_maxlen: int = 100000

    # Certificate Authority (for device X.509 certificate generation)
    ca_cert_path: str = "/mosquitto/certs/ca.crt"   # CA certificate (reuse Phase 18 CA)
    ca_key_path: str = "/mosquitto/certs/ca.key"    # CA private key for signing

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

    # Metrics
    metrics_enabled: bool = True

    # Notification Services
    sendgrid_api_key: str = ""          # Empty = email disabled
    sendgrid_from_email: str = "alerts@eriop.com"

    twilio_account_sid: str = ""        # Empty = SMS disabled
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    vapid_private_key: str = ""         # Empty = push disabled
    vapid_public_key: str = ""
    vapid_mailto: str = "mailto:alerts@eriop.com"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
