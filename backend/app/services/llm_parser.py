import json
import re
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import httpx
from sqlmodel import Session

from app.core.config import get_settings
from app.models.media import AppSetting, MediaItem, MediaType, ParsedResult
from app.services.media_filter import is_extra_video

YEAR_PATTERN = re.compile(r"(?:19|20)\d{2}")
SEASON_PATTERN = re.compile(r"S(?P<season>\d{1,2})(?:E(?P<episode>\d{1,3}))?", re.IGNORECASE)
EPISODE_PATTERN = re.compile(r"(?:E|EP|第)(?P<episode>\d{1,3})(?:集)?", re.IGNORECASE)
QUALITY_PATTERN = re.compile(r"(2160p|1080p|720p|480p|4k)", re.IGNORECASE)
SOURCE_PATTERN = re.compile(r"(WEB-DL|WEBRip|BluRay|UHD|HDTV|DVDRip)", re.IGNORECASE)
ANIME_HINTS = ("番剧", "动漫", "动画", "anime", "bangumi", "bdrip")


class LLMParserService:
    def __init__(self, session: Session | None = None) -> None:
        self.settings = get_settings()
        self.runtime_settings = self._load_runtime_settings(session) if session else {}

    async def parse(self, item: MediaItem) -> ParsedResult:
        api_base_url = self._setting("llm_api_base_url")
        model = self._setting("llm_model")
        if api_base_url and model:
            parsed = await self._parse_with_llm(item)
        else:
            parsed = self._parse_with_rules(item)
        return ParsedResult(media_item_id=item.id or 0, **parsed)

    def can_use_llm(self) -> bool:
        return bool(self._setting("llm_api_base_url") and self._setting("llm_model"))

    def _setting(self, key: str) -> str:
        value = self.runtime_settings.get(key, getattr(self.settings, key, ""))
        return str(value or "")

    def _load_runtime_settings(self, session: Session | None) -> dict[str, Any]:
        if not session:
            return {}
        keys = {"llm_api_base_url", "llm_api_key", "llm_model"}
        values: dict[str, Any] = {}
        for key in keys:
            setting = session.get(AppSetting, key)
            if setting and setting.value is not None:
                values[key] = setting.value
        return values

    async def _parse_with_llm(self, item: MediaItem) -> dict[str, Any]:
        content = ""
        async for chunk in self.stream_llm_content(item):
            content += chunk
        parsed = json.loads(content)
        return self._normalize(parsed, item)

    async def stream_llm_content(self, item: MediaItem) -> AsyncGenerator[str, None]:
        prompt = self._build_prompt(item)
        headers = {"Content-Type": "application/json"}
        api_key = self._setting("llm_api_key")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": self._setting("llm_model"),
            "messages": [
                {"role": "system", "content": "你是影视文件名解析器，只输出 JSON。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self._setting('llm_api_base_url').rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if not data or data == "[DONE]":
                        continue
                    payload_chunk = json.loads(data)
                    delta = payload_chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield str(content)

    def normalize_llm_content(self, content: str, item: MediaItem) -> ParsedResult:
        parsed = json.loads(content)
        normalized = self._normalize(parsed, item)
        return ParsedResult(media_item_id=item.id or 0, **normalized)

    def _parse_with_rules(self, item: MediaItem) -> dict[str, Any]:
        raw = item.raw_name
        cleaned = re.sub(r"[._\[\](){}]+", " ", raw).strip()
        year_match = YEAR_PATTERN.search(cleaned)
        season_match = SEASON_PATTERN.search(cleaned)
        quality_match = QUALITY_PATTERN.search(cleaned)
        source_match = SOURCE_PATTERN.search(cleaned)
        title_end = len(cleaned)
        for match in [year_match, season_match, quality_match, source_match]:
            if match:
                title_end = min(title_end, match.start())
        title = cleaned[:title_end].strip(" -") or cleaned
        episodes = self._episodes_from_files(item.video_files)
        media_type = MediaType.TV if season_match or len(episodes) > 1 else MediaType.MOVIE
        return {
            "media_type": media_type,
            "title": title,
            "original_title": raw,
            "year": int(year_match.group()) if year_match else None,
            "season": int(season_match.group("season")) if season_match else (1 if episodes else None),
            "episodes": episodes,
            "quality": quality_match.group() if quality_match else "",
            "source": source_match.group() if source_match else "",
            "video_codec": "",
            "audio": "",
            "confidence": 0.55,
            "raw_response": {"provider": "rules"},
        }

    def _episodes_from_files(self, files: list[str]) -> list[dict[str, Any]]:
        episodes: list[dict[str, Any]] = []
        for file in files:
            if is_extra_video(file):
                continue
            name = Path(file).stem
            season_match = SEASON_PATTERN.search(name)
            episode_match = EPISODE_PATTERN.search(name)
            episode = None
            season = None
            if season_match:
                season = int(season_match.group("season"))
                if season_match.group("episode"):
                    episode = int(season_match.group("episode"))
            elif episode_match:
                episode = int(episode_match.group("episode"))
            elif len(files) > 1:
                leading_number = re.search(r"(?:^|\D)(\d{1,3})(?:\D|$)", name)
                episode = int(leading_number.group(1)) if leading_number else None
            if episode is not None:
                episodes.append({"season": season, "episode": episode, "raw_file": file})
        return episodes

    def _normalize(self, parsed: dict[str, Any], item: MediaItem) -> dict[str, Any]:
        media_type = parsed.get("media_type", "unknown")
        if media_type not in {"movie", "tv", "anime", "unknown"}:
            media_type = "unknown"
        if media_type == "tv" and self._looks_like_anime(item, parsed):
            media_type = "anime"
        return {
            "media_type": MediaType(media_type),
            "title": str(parsed.get("title") or item.raw_name),
            "original_title": str(parsed.get("original_title") or item.raw_name),
            "year": parsed.get("year"),
            "season": parsed.get("season"),
            "episodes": parsed.get("episodes") or [],
            "quality": str(parsed.get("quality") or ""),
            "source": str(parsed.get("source") or ""),
            "video_codec": str(parsed.get("video_codec") or ""),
            "audio": str(parsed.get("audio") or ""),
            "confidence": float(parsed.get("confidence") or 0.0),
            "raw_response": parsed,
        }

    def _looks_like_anime(self, item: MediaItem, parsed: dict[str, Any]) -> bool:
        values = [
            item.raw_name,
            item.source_path,
            str(parsed.get("title") or ""),
            str(parsed.get("original_title") or ""),
        ]
        values.extend(item.video_files[:5])
        content = " ".join(values).lower()
        return any(hint in content for hint in ANIME_HINTS)

    def _build_prompt(self, item: MediaItem) -> str:
        filtered_files = [file for file in item.video_files if not is_extra_video(file)]
        ignored_files = [file for file in item.video_files if is_extra_video(file)]
        return json.dumps(
            {
                "task": "解析 BT 下载影视资源名称，返回结构化 JSON",
                "rules": [
                    "只识别正片电影或正片剧集。",
                    "如果资源路径、下载分类或标题显示这是番剧、动漫、动画、Anime、Bangumi，"
                    "media_type 必须输出 anime，不能输出 tv。",
                    "普通真人电视剧才输出 tv；日本/中文动画番剧即使 TMDB 类型是 tv，也要输出 anime。",
                    "episodes 字段只能包含正片集数文件，绝对不要包含非正片内容。",
                    "不要把 menu、BDMenu、PV、CM、NCOP、NCED、特典、特典映像、Tokuten、OVA "
                    "等内容识别为正片剧集。",
                    "不要把 Fonts、MANGA、sample、trailer 等内容识别为正片剧集。",
                    "如果文件名或路径包含上述非正片标记，应放入 ignored_files，不能放入 episodes。",
                    "如果一个目录包含 01-12 正片和 menu/PV/NCOP/NCED/特典等附加内容，episodes 只能输出 01-12。",
                    "如果 OVA 是独立特别篇，不要把它顺延编号为 TV 正片集数。",
                    "raw_file 必须使用输入 files 中的原始完整路径。",
                    "只输出 JSON，不要输出解释性文本。",
                ],
                "schema": {
                    "media_type": "movie|tv|anime|unknown",
                    "title": "影视标题",
                    "original_title": "原始标题",
                    "year": "年份或 null",
                    "season": "季号或 null",
                    "episodes": [{"season": "季号或 null", "episode": "集号", "raw_file": "正片原文件路径"}],
                    "ignored_files": [{"raw_file": "被忽略的非正片文件路径", "reason": "忽略原因"}],
                    "quality": "分辨率",
                    "source": "片源",
                    "video_codec": "视频编码",
                    "audio": "音频信息",
                    "confidence": "0 到 1",
                },
                "raw_name": item.raw_name,
                "files": filtered_files,
                "known_ignored_files": ignored_files,
            },
            ensure_ascii=False,
        )
