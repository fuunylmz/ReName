from pathlib import Path

from sqlmodel import Session, select

from app.models.media import MediaItem
from app.services.media_filter import is_extra_video

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".ts", ".m2ts", ".mov", ".wmv", ".flv", ".webm"}
IGNORED_PARTS = {"sample", "trailer", "extras", "featurette"}


class ScannerService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def scan(self, path: str, recursive: bool = False) -> list[MediaItem]:
        root = Path(path).expanduser().resolve()
        if not root.exists():
            raise FileNotFoundError(f"路径不存在：{root}")
        if root.is_file():
            return [self._upsert_item(root)] if self._is_video(root) else []

        candidates = self._collect_candidates(root, recursive)
        items = [self._upsert_item(candidate) for candidate in candidates]
        self.session.commit()
        return items

    def _collect_candidates(self, root: Path, recursive: bool) -> list[Path]:
        candidates: list[Path] = []
        direct_videos = [file for file in root.iterdir() if file.is_file() and self._is_video(file)]
        if direct_videos:
            candidates.append(root)

        directories = root.rglob("*") if recursive else root.iterdir()
        for child in directories:
            if child.is_dir() and self._directory_has_video(child):
                candidates.append(child)
        return sorted(set(candidates))

    def _upsert_item(self, path: Path) -> MediaItem:
        video_files = self._video_files_for(path)
        size = sum(file.stat().st_size for file in video_files if file.exists())
        existing = self.session.exec(
            select(MediaItem).where(MediaItem.source_path == str(path))
        ).first()
        if existing:
            existing.raw_name = path.name
            existing.size = size
            existing.file_count = len(video_files)
            existing.video_files = [str(file) for file in video_files]
            self.session.add(existing)
            return existing

        item = MediaItem(
            source_path=str(path),
            raw_name=path.name,
            size=size,
            file_count=len(video_files),
            video_files=[str(file) for file in video_files],
        )
        self.session.add(item)
        self.session.flush()
        return item

    def _video_files_for(self, path: Path) -> list[Path]:
        if path.is_file():
            return [path] if self._is_video(path) else []
        return sorted(file for file in path.rglob("*") if file.is_file() and self._is_video(file))

    def _directory_has_video(self, path: Path) -> bool:
        return any(file.is_file() and self._is_video(file) for file in path.rglob("*"))

    def _is_video(self, path: Path) -> bool:
        name = path.stem.lower()
        return (
            path.suffix.lower() in VIDEO_EXTENSIONS
            and not any(part in name for part in IGNORED_PARTS)
            and not is_extra_video(path)
        )
