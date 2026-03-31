"""Configuración central de la aplicación usando pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación cargada desde variables de entorno o .env."""

    # Base de datos
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/openclinica"

    # Seguridad JWT
    SECRET_KEY: str = "changeme-secret-key-for-development-only"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""

    # OpenAI / Whisper
    OPENAI_API_KEY: str = ""
    WHISPER_MODEL: str = "whisper-1"

    # Telegram + n8n (MOD_06)
    TELEGRAM_BOT_TOKEN: str = ""
    N8N_WEBHOOK_SECRET: str = ""
    N8N_BASE_URL: str = "http://n8n:5678"
    INTERNAL_API_TOKEN: str = ""

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Entorno
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()
