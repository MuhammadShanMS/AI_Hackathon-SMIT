from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "HCM Lite"
    DATABASE_URL: str = "sqlite:///./hcm_lite.db"
    SECRET_KEY: str = "change-this-in-production-secret-key-32-chars-min"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Optional first-run bootstrap
    COMPANY_NAME: Optional[str] = None
    ADMIN_EMAIL: Optional[str] = None
    ADMIN_PASSWORD: Optional[str] = None

    # CORS configuration
    CORS_ORIGINS: str = "*"

    # AI Integration (Google Gemini)
    AI_API_KEY: Optional[str] = None
    AI_MODEL: str = "gemini-1.5-flash"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
