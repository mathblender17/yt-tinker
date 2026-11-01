from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

_INVALID_WINDOWS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_WINDOWS_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_VIDEO_ID = re.compile(r"^[\w-]{11}$")
_SCHEMELESS_URL = re.compile(r"^((www|m|music)\.)?(youtube\.com|youtu\.be)/", re.IGNORECASE)


def sanitize_windows_filename(value: str, fallback: str = "Untitled") -> str:
    sanitized = _INVALID_WINDOWS_CHARS.sub("_", value).strip().rstrip(". ")
    if not sanitized:
        return fallback
    if sanitized.upper() in _RESERVED_WINDOWS_NAMES:
        return f"_{sanitized}"
    return sanitized[:180].rstrip(". ")


def playlist_destination(base_directory: Path, playlist_title: str) -> Path:
    return base_directory / sanitize_windows_filename(playlist_title)


def normalize_youtube_url(value: str) -> str:
    url = value.strip()
    return f"https://{url}" if _SCHEMELESS_URL.match(url) else url


def is_url(value: str) -> bool:
    url = value.strip()
    return bool(_SCHEMELESS_URL.match(url)) or url.casefold().startswith(("http://", "https://"))


def youtube_video_id(url: str) -> str | None:
    """Reads the video id without a network call; None for anything else."""
    parts = urlsplit(normalize_youtube_url(url))
    host = (parts.hostname or "").removeprefix("www.").removeprefix("m.").removeprefix("music.")
    segments = [segment for segment in parts.path.split("/") if segment]
    if host == "youtu.be" and segments:
        candidate = segments[0]
    elif host == "youtube.com" and segments[:1] == ["watch"]:
        candidate = parse_qs(parts.query).get("v", [""])[0]
    elif host == "youtube.com" and len(segments) > 1 and segments[0] in {"shorts", "embed", "live"}:
        candidate = segments[1]
    else:
        return None
    return candidate if _VIDEO_ID.match(candidate) else None


def youtube_playlist_id(url: str) -> str | None:
    """Playlist id of a link; radio mixes (RD…) are endless, so they don't count."""
    parts = urlsplit(normalize_youtube_url(url))
    if not (parts.hostname or "").endswith(("youtube.com", "youtu.be")):
        return None
    playlist = parse_qs(parts.query).get("list", [""])[0]
    return playlist if playlist and not playlist.startswith("RD") else None
