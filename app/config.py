"""Configuration settings for Entity API."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from utils_api.config import load_settings


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./entity.db"
    DB_ECHO: bool = False

    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Entity API"

    # Service
    SERVICE_NAME: str = "entity-api"
    LOG_LEVEL: str = "INFO"


settings = load_settings(Settings)
