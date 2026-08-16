from __future__ import annotations

import re
from pathlib import Path

_INVALID_WINDOWS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_WINDOWS_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def sanitize_windows_filename(value: str, fallback: str = "Untitled") -> str:
    sanitized = _INVALID_WINDOWS_CHARS.sub("_", value).strip().rstrip(". ")
    if not sanitized:
        return fallback
    if sanitized.upper() in _RESERVED_WINDOWS_NAMES:
        return f"_{sanitized}"
    return sanitized[:180]


def playlist_destination(base_directory: Path, playlist_title: str) -> Path:
    return base_directory / sanitize_windows_filename(playlist_title)


def normalize_youtube_url(value: str) -> str:
    url = value.strip()
    if url.startswith("youtu.be/"):
        return f"https://{url}"
    if url.startswith("youtube.com/"):
        return f"https://www.{url}"
    return url
