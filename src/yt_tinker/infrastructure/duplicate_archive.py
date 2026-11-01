from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from threading import Lock

from yt_tinker.domain.models import DownloadFormat, MediaItem


class DownloadArchive:
    """Persistent completion index keyed by source ID, format, and selected root."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = Lock()
        self._entries = dict(_load(path))

    def find(
        self, source_id: str, media_format: DownloadFormat, destination: Path
    ) -> MediaItem | None:
        item = self._entries.get(_key(source_id, media_format, destination))
        return item if item is not None and item.local_path.exists() else None

    def add(self, item: MediaItem, destination: Path) -> None:
        with self._lock:
            self._entries[_key_for(item, destination)] = item
            self._save()

    def remove(self, key: str) -> None:
        with self._lock:
            self._entries.pop(key, None)
            self._save()

    def entries(self) -> list[tuple[str, MediaItem]]:
        """Most recent first."""
        with self._lock:
            pairs = list(self._entries.items())
        return sorted(pairs, key=lambda pair: pair[1].downloaded_at, reverse=True)

    def source_ids(self) -> set[str]:
        with self._lock:
            return {item.source_id for item in self._entries.values()}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps([_serialize(item, key) for key, item in self._entries.items()], indent=2),
            encoding="utf-8",
        )
        temporary.replace(self._path)


def _load(path: Path) -> list[tuple[str, MediaItem]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [_deserialize(entry) for entry in raw]
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return []


def _key(source_id: str, media_format: DownloadFormat, destination: Path) -> str:
    return "|".join((source_id, media_format.value, str(destination.resolve()).casefold()))


def _key_for(item: MediaItem, destination: Path) -> str:
    return _key(item.source_id, item.media_format, destination)


def _serialize(item: MediaItem, key: str) -> dict[str, object]:
    payload = asdict(item)
    payload["local_path"] = str(item.local_path)
    payload["downloaded_at"] = item.downloaded_at.isoformat()
    payload["media_format"] = item.media_format.value
    payload["key"] = key
    return payload


def _deserialize(payload: dict[str, object]) -> tuple[str, MediaItem]:
    item = MediaItem(
        source_id=str(payload["source_id"]),
        source_url=str(payload["source_url"]),
        title=str(payload["title"]),
        media_format=DownloadFormat(str(payload["media_format"])),
        local_path=Path(str(payload["local_path"])),
        downloaded_at=datetime.fromisoformat(str(payload["downloaded_at"])),
        duration_seconds=_optional_float(payload.get("duration_seconds")),
        thumbnail_url=_optional_string(payload.get("thumbnail_url")),
        artist=_optional_string(payload.get("artist")),
        album=_optional_string(payload.get("album")),
        playlist_title=_optional_string(payload.get("playlist_title")),
        file_size_bytes=_optional_int(payload.get("file_size_bytes")),
    )
    return str(payload["key"]), item


def _optional_string(value: object) -> str | None:
    return str(value) if value is not None else None


def _optional_float(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None


def _optional_int(value: object) -> int | None:
    return int(value) if isinstance(value, int | float) else None
