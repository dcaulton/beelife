"""Core settings for beelife."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlmodel import Field


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

    # Ollama
    ollama_model: str = Field(default="qwen2.5:32b", validation_alias="OLLAMA_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434", validation_alias="OLLAMA_BASE_URL")

    analysis_save_graph_files: bool = Field(default=False, validation_alias="ANALYSIS_SAVE_GRAPH_FILES")


# Singleton instance
settings = Settings()
