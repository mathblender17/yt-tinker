from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from yt_tinker.domain.models import (
    DownloadFormat,
    DownloadRequest,
    QueueItem,
    QueueStatus,
    VideoQuality,
)


class QueueStore:
    """Keeps unfinished downloads across restarts; partial files stay on disk to resume from."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> list[QueueItem]:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return [_deserialize(entry) for entry in raw]
        except (OSError, ValueError, TypeError, KeyError):
            return []

    def save(self, items: Iterable[QueueItem]) -> None:
        unfinished = [
            _serialize(item)
            for item in items
            if item.status not in {QueueStatus.COMPLETED, QueueStatus.FAILED, QueueStatus.CANCELLED}
        ]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        temporary.write_text(json.dumps(unfinished, indent=2), encoding="utf-8")
        temporary.replace(self._path)


def _serialize(item: QueueItem) -> dict[str, object]:
    request = item.request
    return {
        "source_url": request.source_url,
        "destination": str(request.destination),
        "media_format": request.media_format,
        "allow_duplicate": request.allow_duplicate,
        "quality": request.quality,
        "collection": request.collection,
        "index": request.index,
        "paused": item.status is QueueStatus.PAUSED,
        "title": item.title,
        "thumbnail_url": item.thumbnail_url,
    }


def _deserialize(entry: dict[str, object]) -> QueueItem:
    request = DownloadRequest(
        source_url=str(entry["source_url"]),
        destination=Path(str(entry["destination"])),
        media_format=DownloadFormat(str(entry["media_format"])),
        allow_duplicate=bool(entry.get("allow_duplicate")),
        quality=VideoQuality(str(entry.get("quality", VideoQuality.STANDARD))),
        collection=str(entry["collection"]) if entry.get("collection") else None,
        index=int(str(entry["index"])) if entry.get("index") else None,
    )
    return QueueItem(
        request,
        status=QueueStatus.PAUSED if entry.get("paused") else QueueStatus.QUEUED,
        title=str(entry["title"]) if entry.get("title") else None,
        thumbnail_url=str(entry["thumbnail_url"]) if entry.get("thumbnail_url") else None,
    )
