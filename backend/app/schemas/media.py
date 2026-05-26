from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.media import MediaStatus, MediaType, OperationType


class ScanRequest(BaseModel):
    path: str
    recursive: bool = False


class MediaItemRead(BaseModel):
    id: int
    source_path: str
    raw_name: str
    media_type: MediaType
    status: MediaStatus
    size: int
    file_count: int
    video_files: list[str]

    model_config = ConfigDict(from_attributes=True)


class ParsedResultRead(BaseModel):
    id: int
    media_item_id: int
    media_type: MediaType
    title: str
    original_title: str
    year: int | None
    season: int | None
    episodes: list[dict[str, Any]]
    quality: str
    source: str
    video_codec: str
    audio: str
    confidence: float

    model_config = ConfigDict(from_attributes=True)


class TmdbMatchRead(BaseModel):
    id: int
    media_item_id: int
    tmdb_id: int
    media_type: MediaType
    title: str
    original_title: str
    year: int | None
    poster_path: str | None
    overview: str
    score: float
    selected: bool

    model_config = ConfigDict(from_attributes=True)


class SelectMatchRequest(BaseModel):
    match_id: int


class RenamePlanRequest(BaseModel):
    operation: OperationType = OperationType.HARDLINK


class RenamePlanRead(BaseModel):
    id: int
    media_item_id: int
    operation: OperationType
    status: str
    plan: list[dict[str, Any]]

    model_config = ConfigDict(from_attributes=True)


class SettingsRead(BaseModel):
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


class SettingsUpdate(SettingsRead):
    pass


class LLMModelsRequest(BaseModel):
    api_base_url: str
    api_key: str = ""


class LLMModelRead(BaseModel):
    id: str
    owned_by: str | None = None


class LLMModelsRead(BaseModel):
    models: list[LLMModelRead]
