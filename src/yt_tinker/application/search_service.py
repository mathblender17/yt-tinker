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


class SearchProvider(Protocol):
    def search(self, query: str, limit: int = 10) -> list[SearchResult]: ...


class SearchService:
    def __init__(self, provider: SearchProvider) -> None:
        self._provider = provider

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        cleaned = query.strip()
        return self._provider.search(cleaned, limit) if cleaned else []
