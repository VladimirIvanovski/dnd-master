from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "D&D Master"
    debug: bool = False
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://dnd:dnd@localhost:5432/dnd_master"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Allow Tailscale Funnel / Serve HTTPS origins (same machine can also serve SPA same-origin).
    cors_origin_regex: str | None = r"https://.*\.ts\.net"
    host: str = "0.0.0.0"
    port: int = 8000
    serve_frontend: bool = True
    # Relative to backend/ cwd when starting via start-game scripts
    frontend_dist: str = "../frontend/dist"
    jwt_secret: str = "change-me-in-production"
    jwt_expire_minutes: int = 60 * 24 * 7
    rate_limit_default: str = "120/minute"
    rate_limit_auth: str = "10/minute"
    rate_limit_gameplay: str = "30/minute"
    llm_provider: str = "mock"
    embedding_dimensions: int = 1536
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_fallback_model: str = "openai/gpt-oss-20b"
    groq_fallback_model_2: str = "llama-3.3-70b-versatile"
    groq_fallback_model_3: str = "qwen/qwen3.6-27b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    cerebras_api_key: str | None = None
    cerebras_model: str = "gpt-oss-120b"
    cerebras_fallback_model: str = "gpt-oss-20b"
    cerebras_base_url: str = "https://api.cerebras.ai/v1"
    image_generation_enabled: bool = True
    image_model: str = "mock"
    image_model_path: str = "storage/models/sd-turbo"
    image_device: str = "cpu"
    image_width: int = 512
    image_height: int = 512
    image_steps: int = 1
    image_max_concurrent: int = 1
    asset_storage_path: str = "storage/assets"
    rate_limit_asset_regen: str = "5/minute"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
