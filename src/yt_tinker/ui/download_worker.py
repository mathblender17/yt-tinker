from __future__ import annotations

from threading import Event
from uuid import UUID

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

    progress_changed = Signal(object, object)
    status_changed = Signal(object, object)
    completed = Signal(object, object)
    duplicate_found = Signal(object, object)
    failed = Signal(object, object)

    def __init__(self, service: DownloadService, request: DownloadRequest, item_id: UUID) -> None:
        super().__init__()
        self._service = service
        self._request = request
        self._item_id = item_id
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
            self.failed.emit(self._item_id, result)
        elif isinstance(result, DuplicateDownload):
            self.duplicate_found.emit(self._item_id, result)
        else:
            self.completed.emit(self._item_id, result)

    def _emit_progress(self, progress: DownloadProgress) -> None:
        self.progress_changed.emit(self._item_id, progress)

    def _emit_status(self, status: QueueStatus) -> None:
        self.status_changed.emit(self._item_id, status)
