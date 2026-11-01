from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from yt_tinker.domain.models import (
    DownloadError,
    DownloadProgress,
    DownloadRequest,
    DuplicateDownload,
    ErrorCategory,
    MediaItem,
    QueueStatus,
)


class DownloadCancelled(Exception):
    """Raised cooperatively by a downloader when the active job is cancelled."""


class FfmpegUnavailableError(Exception):
    """Raised before a task requiring FFmpeg is started."""


class DownloaderExecutionError(Exception):
    """Raised when a backend cannot complete a request."""


class Downloader(Protocol):
    """Infrastructure boundary for yt-dlp; it must never be implemented by the UI."""

    def download(
        self,
        request: DownloadRequest,
        on_progress: Callable[[DownloadProgress], None],
        on_status: Callable[[QueueStatus], None],
        is_cancelled: Callable[[], bool],
    ) -> list[MediaItem] | DuplicateDownload: ...

    def discard(self, request: DownloadRequest) -> None:
        """Delete the partial files of a request that will not be resumed."""


class DownloadService:
    """Application boundary that converts backend failures into domain errors."""

    def __init__(self, downloader: Downloader) -> None:
        self._downloader = downloader

    def execute(
        self,
        request: DownloadRequest,
        on_progress: Callable[[DownloadProgress], None],
        on_status: Callable[[QueueStatus], None],
        is_cancelled: Callable[[], bool],
    ) -> list[MediaItem] | DuplicateDownload | DownloadError:
        try:
            return self._downloader.download(request, on_progress, on_status, is_cancelled)
        except DownloadCancelled:
            return DownloadError(ErrorCategory.CANCELLED, "Download cancelled.")
        except FfmpegUnavailableError:
            return DownloadError(
                ErrorCategory.FFMPEG_MISSING,
                "FFmpeg is required for MP4 merging and MP3 conversion. Install FFmpeg and add it to PATH.",
            )
        except Exception as error:  # A backend must never crash the GUI thread.
            return map_error(error)

    def discard(self, request: DownloadRequest) -> None:
        self._downloader.discard(request)


_FRIENDLY_MESSAGES = {
    ErrorCategory.AUTHENTICATION: "YouTube wants a sign-in for this video, so it can't be downloaded.",
    ErrorCategory.UNSUPPORTED_URL: "This link isn't supported.",
    ErrorCategory.NETWORK: "The connection dropped. Check your network and retry.",
    ErrorCategory.RUNTIME_MISSING: "A JavaScript runtime is required. Install Deno or Node.js.",
    ErrorCategory.FILESYSTEM: "The file couldn't be saved. Check the download folder in Settings.",
    ErrorCategory.DISK_FULL: "The disk is full. Free some space and retry.",
}


def map_error(error: Exception) -> DownloadError:
    """Turn backend failures into user-meaningful categories without exposing tracebacks."""
    message = str(error) or "The download could not be completed."
    normalized = message.casefold()
    if "ffmpeg" in normalized and ("not found" in normalized or "missing" in normalized):
        category = ErrorCategory.FFMPEG_MISSING
    elif "javascript runtime" in normalized or "node" in normalized and "not found" in normalized:
        category = ErrorCategory.RUNTIME_MISSING
    elif "no space" in normalized or "disk full" in normalized:
        category = ErrorCategory.DISK_FULL
    elif "sign in" in normalized or "cookies" in normalized:
        category = ErrorCategory.AUTHENTICATION
    elif "unsupported url" in normalized:
        category = ErrorCategory.UNSUPPORTED_URL
    elif "network" in normalized or "timed out" in normalized or "connection" in normalized:
        category = ErrorCategory.NETWORK
    elif "permission" in normalized or "access is denied" in normalized:
        category = ErrorCategory.FILESYSTEM
    else:
        category = ErrorCategory.EXTRACTION
    friendly = _FRIENDLY_MESSAGES.get(category, message.removeprefix("ERROR: "))
    return DownloadError(category, friendly, technical_detail=repr(error))
