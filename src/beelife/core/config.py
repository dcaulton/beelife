"""Core settings for beelife."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Environment
    environment: str = "development"
    debug: bool = True

    # Service
    service_name: str = "beelife"
    host: str = "0.0.0.0"
    port: int = 8120

    # Database
    database_url: str = "postgresql+psycopg://beelife:beelife_dev@localhost:5434/beelife"


# Singleton instance
settings = Settings()
