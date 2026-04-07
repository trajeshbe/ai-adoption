"""12-factor configuration via Pydantic Settings.

All configuration is loaded from environment variables. No config files.
Each service can extend this base with service-specific settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Base settings shared across all services."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Service Identity ───────────────────────────────────────────────
    service_name: str = "agent-platform"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # ── Database (Postgres + pgvector) ─────────────────────────────────
    database_url: str = "postgresql://agent_platform:agent_platform@localhost:5432/agent_platform"

    # ── Redis ──────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── MinIO ──────────────────────────────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False

    # ── LLM Runtime ───────────────────────────────────────────────────
    llm_primary_url: str = "http://localhost:11434/v1"
    llm_fallback_url: str = "http://localhost:8080/v1"
    llm_model: str = "llama3.1:8b"
    openai_api_key: str = ""  # Set to enable OpenAI as LLM provider

    # ── Observability ──────────────────────────────────────────────────
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_enabled: bool = True

    # ── Auth ───────────────────────────────────────────────────────────
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"

    # ── Service URLs (internal mesh communication) ─────────────────────
    agent_engine_url: str = "http://localhost:8003"
    document_service_url: str = "http://localhost:8001"
    cache_service_url: str = "http://localhost:8002"
    cost_tracker_url: str = "http://localhost:8004"
