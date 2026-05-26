from pathlib import Path

EXTRA_PATH_PARTS = {
    "4k bd",
    "bdmenu",
    "bd menu",
    "bonus",
    "cd",
    "cm",
    "extra",
    "extras",
    "font",
    "fonts",
    "menu",
    "manga",
    "nced",
    "ncop",
    "ncop&nced",
    "ova",
    "pv",
    "sample",
    "special",
    "specials",
    "sp",
    "tokuten",
    "trailer",
    "特典",
    "特典cd",
    "特典映像",
}

EXTRA_NAME_TOKENS = {
    "bdmenu",
    "bd menu",
    "cm",
    "menu",
    "nced",
    "ncop",
    "ova",
    "pv",
    "sample",
    "tokuten",
    "trailer",
    "特典",
}


def is_extra_video(path: str | Path) -> bool:
    video_path = Path(path)
    parent_parts = {part.lower() for part in video_path.parts[:-1]}
    if parent_parts & EXTRA_PATH_PARTS:
        return True

    name = video_path.stem.lower()
    return any(token in name for token in EXTRA_NAME_TOKENS)
