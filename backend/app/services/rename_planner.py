from pathlib import Path
from typing import Any

from sqlmodel import Session

from app.core.config import get_settings
from app.models.media import AppSetting, MediaItem, MediaType, OperationType, ParsedResult, RenamePlan, TmdbMatch
from app.services.media_filter import is_extra_video

INVALID_CHARS = '<>:"/\\|?*'


class RenamePlannerService:
    def __init__(self, session: Session | None = None) -> None:
        self.settings = get_settings()
        self.runtime_settings = self._load_runtime_settings(session) if session else {}

    def _setting(self, key: str) -> str:
        value = self.runtime_settings.get(key, getattr(self.settings, key, ""))
        return str(value or "")

    def _load_runtime_settings(self, session: Session | None) -> dict[str, Any]:
        if not session:
            return {}
        keys = {"movie_library_path", "tv_library_path", "anime_library_path"}
        values: dict[str, Any] = {}
        for key in keys:
            setting = session.get(AppSetting, key)
            if setting and setting.value is not None:
                values[key] = setting.value
        return values

    def build_plan(
        self,
        item: MediaItem,
        parsed: ParsedResult,
        match: TmdbMatch,
        operation: OperationType,
    ) -> RenamePlan:
        if match.media_type == MediaType.MOVIE:
            plan = self._movie_plan(item, match)
        else:
            plan = self._tv_plan(item, parsed, match)
        return RenamePlan(media_item_id=item.id or 0, operation=operation, plan=plan)

    def _movie_plan(self, item: MediaItem, match: TmdbMatch) -> list[dict[str, str]]:
        root = Path(self._setting("movie_library_path") or "Movies")
        year = f" ({match.year})" if match.year else ""
        base_name = self._safe(f"{match.title}{year} [tmdbid-{match.tmdb_id}]")
        target_dir = root / base_name
        plans = []
        video_files = [source for source in item.video_files if not is_extra_video(source)]
        for index, source in enumerate(video_files, start=1):
            suffix = Path(source).suffix
            extra = f" - Part {index}" if len(video_files) > 1 else ""
            target = target_dir / f"{base_name}{extra}{suffix}"
            plans.append({"source": source, "target": str(target)})
        return plans

    def _tv_plan(self, item: MediaItem, parsed: ParsedResult, match: TmdbMatch) -> list[dict[str, str]]:
        library_path = (
            self._setting("anime_library_path")
            if parsed.media_type == MediaType.ANIME
            else None
        ) or self._setting("tv_library_path") or "TV Shows"
        root = Path(library_path)
        year = f" ({match.year})" if match.year else ""
        show_name = self._safe(f"{match.title}{year} [tmdbid-{match.tmdb_id}]")
        episodes_by_file = {
            str(episode.get("raw_file")): episode
            for episode in parsed.episodes
            if episode.get("raw_file") and not is_extra_video(str(episode.get("raw_file")))
        }
        plans = []
        video_files = [source for source in item.video_files if source in episodes_by_file]
        if not video_files:
            video_files = [source for source in item.video_files if not is_extra_video(source)]
        for index, source in enumerate(video_files, start=1):
            episode_data = episodes_by_file.get(source, {})
            season = int(episode_data.get("season") or parsed.season or 1)
            episode = int(episode_data.get("episode") or index)
            suffix = Path(source).suffix
            season_dir = root / show_name / f"Season {season:02d}"
            file_name = self._safe(f"{match.title} - S{season:02d}E{episode:02d}{suffix}")
            plans.append({"source": source, "target": str(season_dir / file_name)})
        return plans

    def _safe(self, value: str) -> str:
        return "".join("-" if char in INVALID_CHARS else char for char in value).strip()
