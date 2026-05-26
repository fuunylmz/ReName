from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class MediaStatus(StrEnum):
    DISCOVERED = "discovered"
    PARSED = "parsed"
    MATCHED = "matched"
    NEEDS_REVIEW = "needs_review"
    PLANNED = "planned"
    COMPLETED = "completed"
    FAILED = "failed"
    IGNORED = "ignored"


class MediaType(StrEnum):
    MOVIE = "movie"
    TV = "tv"
    ANIME = "anime"
    UNKNOWN = "unknown"


class OperationType(StrEnum):
    HARDLINK = "hardlink"
    COPY = "copy"
    MOVE = "move"


class MediaItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    source_path: str = Field(index=True, unique=True)
    raw_name: str = Field(index=True)
    media_type: MediaType = Field(default=MediaType.UNKNOWN)
    status: MediaStatus = Field(default=MediaStatus.DISCOVERED)
    size: int = 0
    file_count: int = 0
    video_files: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ParsedResult(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    media_item_id: int = Field(foreign_key="mediaitem.id", index=True)
    media_type: MediaType = Field(default=MediaType.UNKNOWN)
    title: str = ""
    original_title: str = ""
    year: int | None = None
    season: int | None = None
    episodes: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    quality: str = ""
    source: str = ""
    video_codec: str = ""
    audio: str = ""
    confidence: float = 0.0
    raw_response: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TmdbMatch(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    media_item_id: int = Field(foreign_key="mediaitem.id", index=True)
    tmdb_id: int
    media_type: MediaType
    title: str
    original_title: str = ""
    year: int | None = None
    poster_path: str | None = None
    overview: str = ""
    score: float = 0.0
    selected: bool = False
    raw_response: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RenamePlan(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    media_item_id: int = Field(foreign_key="mediaitem.id", index=True)
    operation: OperationType = Field(default=OperationType.HARDLINK)
    status: str = "planned"
    plan: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    executed_at: datetime | None = None


class AppSetting(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: Any = Field(default=None, sa_column=Column(JSON))
