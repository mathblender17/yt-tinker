from __future__ import annotations

from threading import Event

from PySide6.QtCore import QThread, Signal

from yt_tinker.application.download_service import DownloadService
from yt_tinker.domain.models import (
    DownloadError,
    DownloadProgress,
    DownloadRequest,
    DuplicateDownload,
    QueueStatus,
)


class DownloadWorker(QThread):
    """Runs one service request outside the Qt GUI thread."""

    progress_changed = Signal(object)
    status_changed = Signal(object)
    completed = Signal(object)
    duplicate_found = Signal(object)
    failed = Signal(object)

    def __init__(self, service: DownloadService, request: DownloadRequest) -> None:
        super().__init__()
        self._service = service
        self._request = request
        self._cancel_requested = Event()

    def cancel(self) -> None:
        self._cancel_requested.set()

    def run(self) -> None:
        result = self._service.execute(
            self._request,
            self._emit_progress,
            self._emit_status,
            self._cancel_requested.is_set,
        )
        if isinstance(result, DownloadError):
            self.failed.emit(result)
        elif isinstance(result, DuplicateDownload):
            self.duplicate_found.emit(result)
        else:
            self.completed.emit(result)

    def _emit_progress(self, progress: DownloadProgress) -> None:
        self.progress_changed.emit(progress)

    def _emit_status(self, status: QueueStatus) -> None:
        self.status_changed.emit(status)
