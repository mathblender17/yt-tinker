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
        except DownloaderExecutionError as error:
            return _map_error(error)
        except Exception as error:  # A backend must never crash the GUI thread.
            return _map_error(error)


def _map_error(error: Exception) -> DownloadError:
    message = str(error) or "The download could not be completed."
    normalized = message.casefold()
    if "sign in" in normalized or "cookies" in normalized:
        category = ErrorCategory.AUTHENTICATION
    elif "unsupported url" in normalized:
        category = ErrorCategory.UNSUPPORTED_URL
    elif "network" in normalized or "timed out" in normalized or "connection" in normalized:
        category = ErrorCategory.NETWORK
    elif "permission" in normalized or "disk" in normalized or "no space" in normalized:
        category = ErrorCategory.FILESYSTEM
    else:
        category = ErrorCategory.EXTRACTION
    return DownloadError(category, message, technical_detail=repr(error))
