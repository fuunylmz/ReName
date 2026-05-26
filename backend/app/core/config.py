from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ReName"
    database_url: str = "sqlite:///../data/app.db"
    cors_origins_text: str = ""
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    tmdb_api_key: str = ""
    tmdb_language: str = "zh-CN"
    llm_api_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    default_operation: str = "hardlink"
    movie_library_path: str = ""
    tv_library_path: str = ""
    anime_library_path: str = ""
    anime_movie_library_path: str = ""
    download_paths: list[str] = []

    @field_validator("download_paths", mode="before")
    @classmethod
    def parse_string_list(cls, value: Any) -> Any:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                return value
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    @property
    def allowed_cors_origins(self) -> list[str]:
        raw = self.cors_origins_text.strip()
        if not raw:
            return self.cors_origins
        return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
