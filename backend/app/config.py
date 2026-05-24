"""SmartMail AI+ — Application configuration.

All settings are loaded from environment variables via pydantic-settings.
Never hardcode strings, URLs, or thresholds — always use ``settings``.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/smartmail"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Auth ──────────────────────────────────────────────────────────────
    API_SECRET_KEY: str = "your-secret-key-here"

    # ── Gemini API ────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    LLM_MAX_TOKENS: int = 1000
    LLM_MONTHLY_TOKEN_BUDGET: int = 5_000_000

    # ── Email ─────────────────────────────────────────────────────────────
    EMAIL_PROVIDER: str = "sendgrid"
    SENDGRID_API_KEY: str = ""
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    EMAIL_FROM_ADDRESS: str = ""
    EMAIL_FROM_NAME: str = "SmartMail AI+"

    # ── ML Thresholds (tunable) ───────────────────────────────────────────
    CHURN_RISK_THRESHOLD: float = 0.7
    PURCHASE_PROB_THRESHOLD: float = 0.6
    TOP_SPENDER_THRESHOLD: float = 500.0
    CART_ABANDON_HOURS: int = 24
    EMAIL_COOLDOWN_HOURS: int = 24

    # ── App ───────────────────────────────────────────────────────────────
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    DEBUG: bool = True


settings = Settings()
