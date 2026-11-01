from __future__ import annotations

import time
from threading import Lock
from typing import Any

from yt_tinker.application.download_service import DownloaderExecutionError
from yt_tinker.application.search_service import Preview, SearchResult
from yt_tinker.infrastructure.filesystem import (
    youtube_playlist_id,
    youtube_video_id,
)
from yt_tinker.infrastructure.ytdlp_downloader import BASE_OPTIONS

_UNAVAILABLE = {"is_live", "is_upcoming", "post_live"}
_PREFETCH_LIFETIME = 3600.0  # Media URLs in the metadata expire after a few hours.


class YtDlpSearchProvider:
    """Initial provider adapter; it is used by services, never directly by widgets."""

    def __init__(self) -> None:
        self._search_client: Any = None
        self._search_lock = Lock()
        self._prefetched: dict[str, tuple[float, dict[str, Any]]] = {}

    def search(self, query: str, limit: int = 24) -> list[SearchResult]:
        with self._search_lock:  # A YoutubeDL client isn't thread-safe, but reuse keeps its connection.
            if self._search_client is None:
                import yt_dlp

                self._search_client = yt_dlp.YoutubeDL({**BASE_OPTIONS, "extract_flat": True})
            result = self._search_client.extract_info(f"ytsearch{limit}:{query}", download=False)
        entries = result.get("entries", []) if result else []
        return [
            _search_result(entry)
            for entry in entries
            if entry and entry.get("live_status") not in _UNAVAILABLE
        ]

    def inspect(self, url: str) -> Preview:
        import yt_dlp

        playlist_id = youtube_playlist_id(url)
        video_id = youtube_video_id(url)
        if playlist_id or not video_id:
            target = (
                f"https://www.youtube.com/playlist?list={playlist_id}" if playlist_id else url
            )
            options = {**BASE_OPTIONS, "extract_flat": "in_playlist", "noplaylist": False}
            with yt_dlp.YoutubeDL(options) as client:
                info = client.extract_info(target, download=False)
            if info and info.get("_type") == "playlist":
                entries = tuple(
                    _search_result(entry) for entry in info.get("entries") or [] if entry
                )
                return Preview(
                    source_url=target,
                    title=info.get("title") or "Playlist",
                    thumbnail_url=entries[0].thumbnail_url if entries else None,
                    channel=info.get("channel") or info.get("uploader"),
                    entries=entries,
                    video_url=f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
                )

        with yt_dlp.YoutubeDL({**BASE_OPTIONS, "noplaylist": True}) as client:
            info = client.extract_info(url, download=False, process=False)
        if not info:
            raise DownloaderExecutionError("Nothing was found at this link.")
        if info.get("live_status") in _UNAVAILABLE:
            raise DownloaderExecutionError("Live streams can't be downloaded.")
        self._prefetched[url] = (time.monotonic(), info)
        return Preview(
            source_url=url,
            title=info.get("title") or "Untitled",
            thumbnail_url=info.get("thumbnail"),
            channel=info.get("channel") or info.get("uploader"),
            duration_seconds=info.get("duration"),
        )

    def take_prefetched(self, url: str) -> dict[str, Any] | None:
        """Hands a preview's metadata to the downloader so it isn't fetched a second time."""
        created, info = self._prefetched.pop(url, (0.0, None))
        return info if time.monotonic() - created < _PREFETCH_LIFETIME else None


def _search_result(entry: dict[str, Any]) -> SearchResult:
    source_id = str(entry.get("id", ""))
    thumbnails = entry.get("thumbnails") or []
    return SearchResult(
        source_id=source_id,
        source_url=f"https://www.youtube.com/watch?v={source_id}",
        title=entry.get("title") or "Untitled",
        duration_seconds=entry.get("duration"),
        thumbnail_url=thumbnails[-1].get("url")
        if thumbnails
        else f"https://i.ytimg.com/vi/{source_id}/mqdefault.jpg",
        channel=entry.get("channel") or entry.get("uploader"),
        view_count=entry.get("view_count"),
    )
