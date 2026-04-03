"""Application configuration from environment variables."""

from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# ✅ Correct placement
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    app_name: str = "NDVI Vegetation Monitor"
    debug: bool = False
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Google Earth Engine
    gee_project: Optional[str] = None
    gee_service_account_json: Optional[str] = None

    # Database
    database_url: str = "sqlite:///./ndvi_local.db"

    # Cache
    cache_dir: str = ".cache_ndvi"

    # Cloud filter
    max_cloud_pct: float = 20.0


@lru_cache
def get_settings() -> Settings:
    return Settings()