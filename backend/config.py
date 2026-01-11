"""
BloxPulse Configuration

Loads environment variables and provides configuration settings.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    environment: str = "development"

    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 7860

    # Database
    database_url: str = "sqlite+aiosqlite:///./bloxpulse.db"

    # HuggingFace
    hf_token: str = ""
    hf_space_name: str = "bloxpulse"
    hf_dataset_name: str = "bloxpulse-data"

    # External APIs (Phase 2)
    youtube_api_key: str = ""
    twitter_bearer_token: str = ""

    # Data Collection
    collection_interval_hours: int = 6
    sync_interval_hours: int = 6

    # Cache
    cache_ttl_seconds: int = 86400  # 24 hours

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Export settings instance
settings = get_settings()


# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)
