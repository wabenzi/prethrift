"""Configuration management for the Prethrift backend."""

import os
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation and environment variable support."""

    # Application settings
    service_name: str = "prethrift-backend"
    service_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False

    # Database settings (default to Docker development setup)
    database_url: Optional[str] = None
    db_host: str = "localhost"
    db_port: int = 5433  # Docker mapped port
    db_name: str = "prethrift"
    db_user: str = "prethrift"  # Docker username
    db_password: str = "prethrift_dev"  # Docker password
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # CORS settings
    allowed_origins: str = "http://localhost:5173"
    allowed_methods: str = "*"
    allowed_headers: str = "*"

    # Authentication
    api_key: Optional[str] = None
    cognito_user_pool_id: Optional[str] = None
    cognito_region: Optional[str] = None

    # AWS settings
    aws_region: str = "us-east-1"
    images_bucket: Optional[str] = None
    max_upload_bytes: int = 5242880  # 5MB

    # OpenAI settings
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"

    # Observability settings
    log_level: str = "INFO"
    structured_logging: bool = True

    # OpenTelemetry settings
    otlp_endpoint: Optional[str] = None
    otlp_api_key: Optional[str] = None
    jaeger_endpoint: Optional[str] = None
    trace_sample_rate: float = 0.1

    # Sentry settings
    sentry_dsn: Optional[str] = None
    sentry_traces_sample_rate: float = 0.1
    sentry_profiles_sample_rate: float = 0.1

    # Performance settings
    request_timeout: int = 30
    embedding_batch_size: int = 32
    embedding_cache_ttl: int = 3600  # 1 hour

    # Search settings
    max_search_results: int = 100
    default_search_limit: int = 20
    similarity_threshold: float = 0.7

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse comma-separated origins string."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def allowed_methods_list(self) -> List[str]:
        """Parse comma-separated methods string."""
        return [method.strip() for method in self.allowed_methods.split(",")]

    @property
    def allowed_headers_list(self) -> List[str]:
        """Parse comma-separated headers string."""
        return [header.strip() for header in self.allowed_headers.split(",")]

    @property
    def database_url_computed(self) -> str:
        """Compute database URL if not provided."""
        if self.database_url:
            return self.database_url
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings


# Environment-specific configurations
class DevelopmentSettings(Settings):
    """Development-specific settings."""

    debug: bool = True
    log_level: str = "DEBUG"
    trace_sample_rate: float = 1.0
    sentry_traces_sample_rate: float = 1.0


class ProductionSettings(Settings):
    """Production-specific settings."""

    debug: bool = False
    log_level: str = "INFO"
    trace_sample_rate: float = 0.1
    sentry_traces_sample_rate: float = 0.1


class TestSettings(Settings):
    """Settings for testing environment."""

    environment: str = "test"
    debug: bool = True
    database_url: str = "postgresql://prethrift:prethrift_dev@localhost:5433/prethrift_test"
    redis_url: str = "redis://localhost:6380/1"  # Use different Redis DB for tests

    # Test-specific overrides
    log_level: str = "INFO"  # Reduce noise in tests
    enable_tracing: bool = False  # Disable tracing in tests for performance


def get_environment_settings() -> Settings:
    """Get environment-specific settings."""
    env = os.getenv("ENVIRONMENT", "development").lower()

    if env == "production":
        return ProductionSettings()
    elif env == "test":
        return TestSettings()
    else:
        return DevelopmentSettings()


# Export commonly used settings
__all__ = [
    "Settings",
    "settings",
    "get_settings",
    "get_environment_settings",
    "DevelopmentSettings",
    "ProductionSettings",
    "TestSettings",
]
