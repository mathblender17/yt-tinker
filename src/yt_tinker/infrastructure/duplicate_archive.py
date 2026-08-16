from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from yt_tinker.domain.models import DownloadFormat, MediaItem


class DownloadArchive:
    """Persistent completion index keyed by source ID, format, and selected root."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def find(
        self, source_id: str, media_format: DownloadFormat, destination: Path
    ) -> MediaItem | None:
        key = _key(source_id, media_format, destination)
        return next((item for item, stored_key in self._load() if stored_key == key), None)

    def add(self, item: MediaItem, destination: Path) -> None:
        entries = self._load()
        entries.append((item, _key_for(item, destination)))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([_serialize(item, key) for item, key in entries], indent=2), encoding="utf-8"
        )

    def _load(self) -> list[tuple[MediaItem, str]]:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
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


def _deserialize(payload: dict[str, object]) -> tuple[MediaItem, str]:
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
    return item, str(payload["key"])


def _optional_string(value: object) -> str | None:
    return str(value) if value is not None else None


def _optional_float(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None


def _optional_int(value: object) -> int | None:
    return int(value) if isinstance(value, int | float) else None
