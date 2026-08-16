from __future__ import annotations

from typing import Any

from yt_tinker.application.search_service import SearchResult


class YtDlpSearchProvider:
    """Initial provider adapter; it is used by services, never directly by widgets."""

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        import yt_dlp

        options: dict[str, Any] = {"quiet": True, "skip_download": True, "extract_flat": True}
        with yt_dlp.YoutubeDL(options) as client:
            result = client.extract_info(f"ytsearch{limit}:{query}", download=False)
        entries = result.get("entries", []) if result else []
        return [
            SearchResult(
                source_id=str(entry.get("id", "")),
                source_url=entry.get("url") or entry.get("webpage_url", ""),
                title=entry.get("title", "Untitled"),
                duration_seconds=entry.get("duration"),
                thumbnail_url=entry.get("thumbnail"),
                channel=entry.get("channel") or entry.get("uploader"),
            )
            for entry in entries
            if entry
        ]
