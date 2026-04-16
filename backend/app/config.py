from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://caddy:changeme@localhost:5432/caddypanel"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = Field(min_length=32)
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = Field(min_length=8)
    CADDY_ADMIN_URL: str = "http://127.0.0.1:2019"
    PANEL_DOMAIN: str = "localhost"
    ALLOWED_IPS: str = ""
    CLOUDFLARE_API_TOKEN: str = ""
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "info"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 1440

    HEALTH_CHECK_INTERVAL_SEC: int = 30
    CERT_CHECK_INTERVAL_HOURS: int = 6
    CERT_EXPIRY_WARNING_DAYS: int = 14

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
