from difflib import SequenceMatcher
from typing import Any

import httpx
from sqlmodel import Session

from app.core.config import get_settings
from app.models.media import AppSetting, MediaType, ParsedResult, TmdbMatch


class TMDBService:
    def __init__(self, session: Session | None = None) -> None:
        self.settings = get_settings()
        self.runtime_settings = self._load_runtime_settings(session) if session else {}
        self.base_url = "https://api.themoviedb.org/3"

    def _setting(self, key: str) -> str:
        value = self.runtime_settings.get(key, getattr(self.settings, key, ""))
        return str(value or "")

    def _load_runtime_settings(self, session: Session | None) -> dict[str, Any]:
        if not session:
            return {}
        keys = {"tmdb_api_key", "tmdb_language"}
        values: dict[str, Any] = {}
        for key in keys:
            setting = session.get(AppSetting, key)
            if setting and setting.value is not None:
                values[key] = setting.value
        return values

    async def search(self, media_item_id: int, parsed: ParsedResult) -> list[TmdbMatch]:
        api_key = self._setting("tmdb_api_key")
        if not api_key:
            return []
        endpoint = "tv" if parsed.media_type in {MediaType.TV, MediaType.ANIME} else "movie"
        params: dict[str, Any] = {
            "api_key": api_key,
            "query": parsed.title,
            "language": self._setting("tmdb_language") or "zh-CN",
            "include_adult": "false",
        }
        if parsed.year:
            params["first_air_date_year" if endpoint == "tv" else "year"] = parsed.year
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self.base_url}/search/{endpoint}", params=params)
            response.raise_for_status()
            results = response.json().get("results", [])
        return [self._to_match(media_item_id, parsed, item, endpoint) for item in results[:8]]

    def _to_match(
        self,
        media_item_id: int,
        parsed: ParsedResult,
        item: dict[str, Any],
        endpoint: str,
    ) -> TmdbMatch:
        title = item.get("name") if endpoint == "tv" else item.get("title")
        original_title = item.get("original_name") if endpoint == "tv" else item.get("original_title")
        date = item.get("first_air_date") if endpoint == "tv" else item.get("release_date")
        year = int(date[:4]) if isinstance(date, str) and len(date) >= 4 and date[:4].isdigit() else None
        title_score = SequenceMatcher(None, parsed.title.lower(), str(title or "").lower()).ratio()
        year_score = 1.0 if parsed.year and year == parsed.year else 0.0 if parsed.year else 0.5
        score = round(title_score * 0.75 + year_score * 0.25, 4)
        media_type = MediaType.TV if endpoint == "tv" else MediaType.MOVIE
        if parsed.media_type == MediaType.ANIME_MOVIE:
            media_type = MediaType.ANIME_MOVIE
        return TmdbMatch(
            media_item_id=media_item_id,
            tmdb_id=item["id"],
            media_type=media_type,
            title=title or "",
            original_title=original_title or "",
            year=year,
            poster_path=item.get("poster_path"),
            overview=item.get("overview") or "",
            score=score,
            raw_response=item,
        )
