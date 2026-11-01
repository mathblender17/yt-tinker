from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SearchResult:
    source_id: str
    source_url: str
    title: str
    duration_seconds: float | None = None
    thumbnail_url: str | None = None
    channel: str | None = None
    view_count: int | None = None


@dataclass(frozen=True, slots=True)
class Preview:
    """What a pasted link points at. Playlists carry their videos in ``entries``."""

    source_url: str
    title: str
    thumbnail_url: str | None = None
    channel: str | None = None
    duration_seconds: float | None = None
    entries: tuple[SearchResult, ...] = ()
    video_url: str | None = None  # The playlist link also named this one video.


class SearchProvider(Protocol):
    def search(self, query: str, limit: int = 24) -> list[SearchResult]: ...

    def inspect(self, url: str) -> Preview: ...


class SearchService:
    _CACHE_SIZE = 64

    def __init__(self, provider: SearchProvider) -> None:
        self._provider = provider
        self._cache: dict[tuple[str, int], list[SearchResult]] = {}

    def search(self, query: str, limit: int = 24) -> list[SearchResult]:
        cleaned = query.strip()
        if not cleaned:
            return []
        key = (cleaned.casefold(), limit)
        if key not in self._cache:
            self._cache[key] = self._provider.search(cleaned, limit)
            if len(self._cache) > self._CACHE_SIZE:
                self._cache.pop(next(iter(self._cache)))
        return self._cache[key]

    def inspect(self, url: str) -> Preview:
        return self._provider.inspect(url)
