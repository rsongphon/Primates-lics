"""
LICS Backend Configuration

Pydantic Settings-based configuration management for environment variables
and application settings. Follows Documentation.md Section 5.1 patterns.
"""

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings using Pydantic BaseSettings for environment management.
    Automatically reads from environment variables and .env files.
    """

    # ===== Application Configuration =====
    APP_NAME: str = "LICS Backend"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # API Configuration
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ===== Database Configuration =====
    # PostgreSQL with TimescaleDB (using asyncpg driver)
    DATABASE_URL: str = "postgresql+asyncpg://lics:lics123@localhost:5432/lics"
    DATABASE_POOLED_URL: Optional[str] = None  # PgBouncer pooled connection
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False
    DATABASE_CONNECT_TIMEOUT: int = 30
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str]) -> Any:
        """Validate database URL format."""
        if isinstance(v, str):
            return v
        return "postgresql+asyncpg://lics:lics123@localhost:5432/lics"

    # ===== Redis Configuration =====
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    REDIS_MAX_CONNECTIONS: int = 20
    REDIS_RETRY_ON_TIMEOUT: bool = True
    REDIS_SOCKET_KEEPALIVE: bool = True
    REDIS_SOCKET_KEEPALIVE_OPTIONS: Dict[str, int] = {}

    # Celery Configuration (Redis-based)
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: List[str] = ["json"]
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_TIMEZONE: str = "UTC"

    # ===== InfluxDB Configuration =====
    INFLUXDB_URL: str = "http://localhost:8086"
    INFLUXDB_TOKEN: str = "lics-admin-token-change-in-production"
    INFLUXDB_ORG: str = "lics"
    INFLUXDB_BUCKET: str = "telemetry"

    # ===== MQTT Configuration =====
    MQTT_BROKER_URL: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: Optional[str] = "lics"
    MQTT_PASSWORD: Optional[str] = None
    MQTT_QOS: int = 1
    MQTT_KEEP_ALIVE: int = 60
    MQTT_CLEAN_SESSION: bool = True

    # ===== Object Storage (MinIO) Configuration =====
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_REGION: str = "us-east-1"

    # Default buckets for different data types
    MINIO_BUCKETS: Dict[str, str] = {
        "videos": "videos",
        "data": "data",
        "exports": "exports",
        "uploads": "uploads",
        "config": "config",
        "backups": "backups",
        "temp": "temp",
        "assets": "assets",
        "logs": "logs",
        "ml": "ml"
    }

    # ===== CORS Configuration =====
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",  # Frontend development
        "https://localhost:3000", # Frontend development HTTPS
        "http://localhost:8080",  # Alternative frontend port
        "https://localhost:8080"  # Alternative frontend port HTTPS
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """Parse CORS origins from environment variable."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # ===== Security Configuration =====
    ALLOWED_HOSTS: List[str] = ["*"]  # Configure properly for production

    # JWT Configuration
    JWT_ALGORITHM: str = "HS256"
    JWT_AUDIENCE: str = "lics:users"
    JWT_ISSUER: str = "lics:backend"

    # Password Configuration
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_NUMBERS: bool = True
    PASSWORD_REQUIRE_SYMBOLS: bool = False

    # ===== WebSocket Configuration =====
    WEBSOCKET_HOST: str = "0.0.0.0"
    WEBSOCKET_PORT: int = 8001
    WEBSOCKET_PING_INTERVAL: int = 30
    WEBSOCKET_PING_TIMEOUT: int = 10
    WEBSOCKET_MAX_CONNECTIONS: int = 1000

    # ===== Logging Configuration =====
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text
    LOG_FILE: Optional[str] = None
    LOG_MAX_SIZE: int = 100 * 1024 * 1024  # 100MB
    LOG_BACKUP_COUNT: int = 5

    # ===== Monitoring Configuration =====
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_METRICS_PATH: str = "/metrics"

    # Health Check Configuration
    HEALTH_CHECK_INTERVAL: int = 30
    HEALTH_CHECK_TIMEOUT: int = 10
    HEALTH_CHECK_CACHE_TTL: int = 60

    # ===== Rate Limiting Configuration =====
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 100
    RATE_LIMIT_BURST: int = 10

    # ===== Development Configuration =====
    RELOAD: bool = False  # Auto-reload for development

    # ===== Feature Flags =====
    FEATURE_WEBSOCKET_ENABLED: bool = True
    FEATURE_CELERY_ENABLED: bool = True
    FEATURE_MQTT_ENABLED: bool = True
    FEATURE_VIDEO_STREAMING_ENABLED: bool = False  # Not implemented yet
    FEATURE_ML_ENABLED: bool = False  # Not implemented yet

    # ===== Performance Configuration =====
    MAX_REQUEST_SIZE: int = 100 * 1024 * 1024  # 100MB
    REQUEST_TIMEOUT: int = 300  # 5 minutes

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_database_url(self, use_pooled: bool = False) -> str:
        """
        Get the appropriate database URL.

        Args:
            use_pooled: Whether to use pooled connection (PgBouncer)

        Returns:
            Database connection URL
        """
        if use_pooled and self.DATABASE_POOLED_URL:
            return self.DATABASE_POOLED_URL
        return self.DATABASE_URL

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"

    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.ENVIRONMENT.lower() == "testing"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.

    Uses LRU cache to avoid re-reading environment variables repeatedly.
    In testing, you can clear the cache with get_settings.cache_clear().

    Returns:
        Application settings instance
    """
    return Settings()


# Global settings instance
settings = get_settings()


# Export commonly used settings for convenience
DATABASE_URL = settings.DATABASE_URL
REDIS_URL = settings.REDIS_URL
SECRET_KEY = settings.SECRET_KEY
API_V1_STR = settings.API_V1_STR