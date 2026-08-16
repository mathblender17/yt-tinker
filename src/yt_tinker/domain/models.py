from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from uuid import UUID, uuid4


class DownloadFormat(StrEnum):
    VIDEO_MP4 = "video_mp4"
    AUDIO_MP3 = "audio_mp3"


class DownloadMode(StrEnum):
    SINGLE = "single"
    PLAYLIST = "playlist"


class QueueStatus(StrEnum):
    QUEUED = "queued"
    PREPARING = "preparing"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ErrorCategory(StrEnum):
    INVALID_URL = "invalid_url"
    UNSUPPORTED_URL = "unsupported_url"
    NETWORK = "network"
    EXTRACTION = "extraction"
    AUTHENTICATION = "authentication"
    FFMPEG_MISSING = "ffmpeg_missing"
    RUNTIME_MISSING = "runtime_missing"
    FILESYSTEM = "filesystem"
    DISK_FULL = "disk_full"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DownloadRequest:
    source_url: str
    destination: Path
    media_format: DownloadFormat
    mode: DownloadMode
    allow_duplicate: bool = False


@dataclass(frozen=True, slots=True)
class DownloadProgress:
    fraction: float = 0.0
    speed_bytes_per_second: float | None = None
    eta_seconds: int | None = None
    completed_children: int = 0
    total_children: int | None = None

    @property
    def percent(self) -> int:
        return round(max(0.0, min(1.0, self.fraction)) * 100)


@dataclass(frozen=True, slots=True)
class DownloadError:
    category: ErrorCategory
    message: str
    technical_detail: str | None = None


@dataclass(frozen=True, slots=True)
class MediaItem:
    source_id: str
    source_url: str
    title: str
    media_format: DownloadFormat
    local_path: Path
    downloaded_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    duration_seconds: float | None = None
    thumbnail_url: str | None = None
    artist: str | None = None
    album: str | None = None
    playlist_title: str | None = None
    file_size_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class DuplicateDownload:
    """A completed local item matching a source, format, and selected destination."""

    existing_item: MediaItem


@dataclass(slots=True)
class QueueItem:
    request: DownloadRequest
    id: UUID = field(default_factory=uuid4)
    status: QueueStatus = QueueStatus.QUEUED
    title: str | None = None
    progress: DownloadProgress = field(default_factory=DownloadProgress)
    error: DownloadError | None = None
    results: list[MediaItem] = field(default_factory=list)
