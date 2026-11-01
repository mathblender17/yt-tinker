from __future__ import annotations

import ctypes
import subprocess
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from platformdirs import user_downloads_path
from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
    QThreadPool,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QDesktopServices

from yt_tinker.application.download_service import DownloadService
from yt_tinker.application.queue_manager import InvalidQueueTransitionError, QueueManager
from yt_tinker.application.search_service import Preview, SearchResult, SearchService
from yt_tinker.application.settings_service import SettingsService
from yt_tinker.domain.models import (
    DownloadError,
    DownloadFormat,
    DownloadProgress,
    DownloadRequest,
    DuplicateDownload,
    ErrorCategory,
    MediaItem,
    QueueItem,
    QueueStatus,
    VideoQuality,
)
from yt_tinker.infrastructure.diagnostics import collect_dependency_status
from yt_tinker.infrastructure.duplicate_archive import DownloadArchive
from yt_tinker.infrastructure.filesystem import is_url, normalize_youtube_url
from yt_tinker.infrastructure.queue_json import QueueStore
from yt_tinker.ui.download_worker import DownloadWorker
from yt_tinker.ui.formatting import (
    human_duration,
    human_eta,
    human_size,
    human_speed,
    human_views,
)

_RUNNING = {QueueStatus.PREPARING, QueueStatus.DOWNLOADING, QueueStatus.PROCESSING}
_WAITING = _RUNNING | {QueueStatus.QUEUED, QueueStatus.PAUSED}
_SPI_GETCLIENTAREAANIMATION = 0x1042
_INDEX = QModelIndex | QPersistentModelIndex
_NO_INDEX = QModelIndex()


class ListModel(QAbstractListModel):
    """Exposes dict rows to QML; patch() repaints only the fields that changed."""

    def __init__(self, roles: list[str], parent: QObject | None = None) -> None:
        super().__init__(parent)
        first = int(Qt.ItemDataRole.UserRole) + 1
        self._ids = {name: first + offset for offset, name in enumerate(roles)}
        self._names = {role: name for name, role in self._ids.items()}
        self.rows: list[dict[str, Any]] = []

    def rowCount(self, parent: _INDEX = _NO_INDEX) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.rows)

    def data(self, index: _INDEX, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:
        return self.rows[index.row()].get(self._names.get(role, ""))

    def roleNames(self) -> dict[int, QByteArray]:  # noqa: N802
        return {role: QByteArray(name.encode()) for role, name in self._names.items()}

    def replace(self, rows: list[dict[str, Any]]) -> None:
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def append(self, row: dict[str, Any]) -> None:
        self.beginInsertRows(_NO_INDEX, len(self.rows), len(self.rows))
        self.rows.append(row)
        self.endInsertRows()

    def remove(self, row_index: int) -> None:
        self.beginRemoveRows(_NO_INDEX, row_index, row_index)
        del self.rows[row_index]
        self.endRemoveRows()

    def patch(self, row_index: int, row: dict[str, Any]) -> None:
        old = self.rows[row_index]
        changed = [self._ids[key] for key, value in row.items() if old.get(key) != value]
        if changed:
            self.rows[row_index] = row
            index = self.index(row_index)
            self.dataChanged.emit(index, index, changed)


class Bridge(QObject):
    """The one object QML talks to; it runs all slow work on background threads."""

    toast = Signal(str)
    duplicateFound = Signal(str, str, str)  # noqa: N815
    searchChanged = Signal()  # noqa: N815
    summaryChanged = Signal()  # noqa: N815
    settingsChanged = Signal()  # noqa: N815
    dependenciesChanged = Signal()  # noqa: N815
    _task_finished = Signal(object)

    def __init__(
        self,
        search: SearchService,
        downloads: DownloadService,
        archive: DownloadArchive,
        settings: SettingsService,
        store: QueueStore,
    ) -> None:
        super().__init__()
        self._search = search
        self._downloads = downloads
        self._archive = archive
        self._settings = settings
        self._store = store
        self._queue = QueueManager()
        self._workers: dict[UUID, DownloadWorker] = {}
        self._pausing: set[UUID] = set()
        self._duplicates: dict[str, tuple[DownloadRequest, MediaItem]] = {}
        self._query_token = 0
        self._searching = False
        self._search_error = ""
        self._preview: Preview | None = None
        self._results: list[SearchResult] = []
        self._dependencies: list[dict[str, Any]] = []
        self._library_filter = ("", "all")
        self._results_model = ListModel(
            ["sourceId", "title", "thumbnail", "duration", "meta", "downloaded"], self
        )
        self._downloads_model = ListModel(
            [
                "rowId",
                "title",
                "thumbnail",
                "status",
                "detail",
                "fraction",
                "audio",
                "path",
                "collection",
            ],
            self,
        )
        self._library_model = ListModel(
            ["key", "title", "thumbnail", "artist", "audio", "size", "date", "path", "missing"],
            self,
        )
        self._task_finished.connect(self._finish_task)
        for item in self._store.load():
            self._queue.add(item)
            self._downloads_model.append(self._row(item))
        self._refresh_library()
        self._pump()
        self._background(collect_dependency_status, self._show_dependencies)

    # Search

    @Slot(str)
    def query(self, text: str) -> None:
        self._query_token += 1
        token = self._query_token
        cleaned = text.strip()
        self._preview = None
        self._search_error = ""
        if not cleaned:
            self._searching = False
            self._show_results([])
            return
        self._searching = True
        if is_url(cleaned):
            url = normalize_youtube_url(cleaned)
            self._show_results([])
            self._background(
                lambda: self._search.inspect(url), lambda outcome: self._show(token, outcome)
            )
        else:
            self._background(
                lambda: self._search.search(cleaned), lambda outcome: self._show(token, outcome)
            )
        self.searchChanged.emit()

    def _show(self, token: int, outcome: list[SearchResult] | Preview | Exception) -> None:
        if token != self._query_token:  # The user has already typed something newer.
            return
        self._searching = False
        if isinstance(outcome, Exception):
            self._search_error = _short_error(outcome)
            self._show_results([])
        elif isinstance(outcome, Preview):
            self._preview = outcome
            self.searchChanged.emit()
        else:
            self._show_results(outcome)
            if not outcome:
                self._search_error = "No results."
                self.searchChanged.emit()

    def _show_results(self, results: list[SearchResult]) -> None:
        self._results = results
        downloaded = self._archive.source_ids()
        self._results_model.replace([_result_row(r, r.source_id in downloaded) for r in results])
        self.searchChanged.emit()

    @Slot(int, bool)
    def downloadResult(self, index: int, audio: bool) -> None:  # noqa: N802
        result = self._results[index]
        self._enqueue(result.source_url, result.title, result.thumbnail_url, audio)

    @Slot(bool)
    def downloadPreview(self, audio: bool) -> None:  # noqa: N802
        preview = self._preview
        if preview is None:
            return
        if not preview.entries:
            self._enqueue(preview.source_url, preview.title, preview.thumbnail_url, audio)
            return
        for position, entry in enumerate(preview.entries, start=1):
            self._enqueue(
                entry.source_url,
                entry.title,
                entry.thumbnail_url,
                audio,
                collection=preview.title,
                index=position,
            )
        self.toast.emit(f"Added {_video_count(len(preview.entries))} to Downloads")

    @Slot(bool)
    def downloadPreviewVideo(self, audio: bool) -> None:  # noqa: N802
        preview = self._preview
        if preview is not None and preview.video_url:
            self._enqueue(preview.video_url, None, preview.thumbnail_url, audio)

    # Queue

    def _enqueue(
        self,
        url: str,
        title: str | None,
        thumbnail: str | None,
        audio: bool,
        collection: str | None = None,
        index: int | None = None,
    ) -> None:
        media_format = DownloadFormat.AUDIO_MP3 if audio else DownloadFormat.VIDEO_MP4
        if any(
            item.request.source_url == url
            and item.request.media_format is media_format
            and item.status in _WAITING
            for item in self._queue.items
        ):
            self.toast.emit("Already in Downloads")
            return
        request = DownloadRequest(
            url,
            self._destination(),
            media_format,
            quality=self._settings.current.video_quality,
            collection=collection,
            index=index,
        )
        self._add(QueueItem(request, title=title, thumbnail_url=thumbnail))
        if collection is None:
            self.toast.emit("Added to Downloads")

    def _add(self, item: QueueItem) -> None:
        self._queue.add(item)
        self._downloads_model.append(self._row(item))
        self._pump()

    def _pump(self) -> None:
        while (item := self._queue.start_next()) is not None:
            # 16 connections saturated the line in benchmarks and 48 cut throughput in half,
            # so parallel downloads share a budget.
            connections = 16 if len(self._queue.active_items) == 1 else 8
            request = replace(item.request, connections=connections)
            worker = DownloadWorker(self._downloads, request, item.id)
            worker.progress_changed.connect(self._on_progress)
            worker.status_changed.connect(self._on_status)
            worker.completed.connect(self._on_completed)
            worker.duplicate_found.connect(self._on_duplicate)
            worker.failed.connect(self._on_failed)
            self._workers[item.id] = worker
            worker.start()
            self._update_row(item)
        self._store.save(self._queue.items)
        self.summaryChanged.emit()

    @Slot(object, object)
    def _on_progress(self, item_id: UUID, progress: DownloadProgress) -> None:
        item = self._queue.get(item_id)
        if item is None:
            return
        # A resumed download recounts from zero until it reaches its saved fragments.
        fraction = max(progress.fraction, item.progress.fraction)
        self._queue.update_progress(item_id, replace(progress, fraction=fraction))
        self._update_row(item)
        self.summaryChanged.emit()

    @Slot(object, object)
    def _on_status(self, item_id: UUID, status: QueueStatus) -> None:
        item = self._queue.get(item_id)
        if item is None or item.status is status:
            return
        try:
            self._queue.transition(item_id, status)
        except InvalidQueueTransitionError:
            return
        self._update_row(item)

    @Slot(object, object)
    def _on_completed(self, item_id: UUID, results: list[MediaItem]) -> None:
        item = self._release(item_id)
        if item is None:
            return
        item.results = results
        item.title = results[0].title if results else item.title
        self._queue.transition(item_id, QueueStatus.COMPLETED)
        self._update_row(item)
        self._refresh_library()
        self._show_results(self._results)
        self._pump()

    @Slot(object, object)
    def _on_duplicate(self, item_id: UUID, duplicate: DuplicateDownload) -> None:
        item = self._release(item_id)
        if item is None:
            return
        existing = duplicate.existing_item
        if item.request.collection:  # A playlist just skips what is already there.
            item.results = [existing]
            self._queue.transition(item_id, QueueStatus.COMPLETED)
            self._update_row(item)
        else:
            token = str(uuid4())
            self._duplicates[token] = (item.request, existing)
            self._queue.transition(item_id, QueueStatus.CANCELLED)
            self._drop(item)
            self.duplicateFound.emit(existing.title, str(existing.local_path), token)
        self._pump()

    @Slot(object, object)
    def _on_failed(self, item_id: UUID, error: DownloadError) -> None:
        item = self._release(item_id)
        if item is None:
            return
        if error.category is ErrorCategory.CANCELLED:
            if item_id in self._pausing:
                self._pausing.discard(item_id)
                self._queue.transition(item_id, QueueStatus.PAUSED)
                self._update_row(item)
            else:
                self._queue.transition(item_id, QueueStatus.CANCELLED)
                self._downloads.discard(item.request)
                self._drop(item)
        else:
            item.error = error
            self._queue.transition(item_id, QueueStatus.FAILED)
            self._update_row(item)
        self._pump()

    def _release(self, item_id: UUID) -> QueueItem | None:
        worker = self._workers.pop(item_id, None)
        if worker is not None:
            worker.wait()  # run() has returned; this only lets the thread object wind down.
        return self._queue.get(item_id)

    def _drop(self, item: QueueItem) -> None:
        self._downloads_model.remove(self._row_index(item.id))
        self._queue.remove(item.id)

    @Slot(str)
    def pause(self, row_id: str) -> None:
        item_id = UUID(row_id)
        worker = self._workers.get(item_id)
        item = self._queue.get(item_id)
        if worker is not None:
            self._pausing.add(item_id)
            worker.cancel()
        elif item is not None and item.status is QueueStatus.QUEUED:
            self._queue.transition(item_id, QueueStatus.PAUSED)
            self._update_row(item)
            self._store.save(self._queue.items)

    @Slot(str)
    def resume(self, row_id: str) -> None:
        self._requeue(UUID(row_id))

    @Slot(str)
    def retry(self, row_id: str) -> None:
        self._requeue(UUID(row_id))

    def _requeue(self, item_id: UUID) -> None:
        item = self._queue.get(item_id)
        if item is None:
            return
        self._queue.transition(item_id, QueueStatus.QUEUED)
        item.error = None
        self._update_row(item)
        self._pump()

    @Slot(str)
    def cancel(self, row_id: str) -> None:
        item_id = UUID(row_id)
        worker = self._workers.get(item_id)
        item = self._queue.get(item_id)
        self._pausing.discard(item_id)
        if worker is not None:
            worker.cancel()
        elif item is not None:
            self._downloads.discard(item.request)
            self._drop(item)
            self._pump()

    @Slot()
    def pauseAll(self) -> None:  # noqa: N802
        self._queue.pause()
        for item in self._queue.items:
            if item.status in _RUNNING or item.status is QueueStatus.QUEUED:
                self.pause(str(item.id))
        self.summaryChanged.emit()

    @Slot()
    def resumeAll(self) -> None:  # noqa: N802
        self._queue.resume()
        for item in self._queue.items:
            if item.status is QueueStatus.PAUSED:
                self._queue.transition(item.id, QueueStatus.QUEUED)
                self._update_row(item)
        self._pump()

    @Slot()
    def clearFinished(self) -> None:  # noqa: N802
        for item in self._queue.items:
            if item.status not in _WAITING:
                self._drop(item)
        self.summaryChanged.emit()

    @Slot(str)
    def downloadAgain(self, token: str) -> None:  # noqa: N802
        request, existing = self._duplicates.pop(token)
        self._add(
            QueueItem(
                replace(request, allow_duplicate=True),
                title=existing.title,
                thumbnail_url=existing.thumbnail_url,
            )
        )

    # Library, files and settings

    @Slot(str, str)
    def setLibraryFilter(self, text: str, kind: str) -> None:  # noqa: N802
        self._library_filter = (text.strip().casefold(), kind)
        self._refresh_library()

    def _refresh_library(self) -> None:
        text, kind = self._library_filter
        rows = []
        for key, item in self._archive.entries():
            audio = item.media_format is DownloadFormat.AUDIO_MP3
            if kind != "all" and audio != (kind == "audio"):
                continue
            if text and text not in f"{item.title} {item.artist or ''}".casefold():
                continue
            rows.append(
                {
                    "key": key,
                    "title": item.title,
                    "thumbnail": item.thumbnail_url or "",
                    "artist": item.artist or "",
                    "audio": audio,
                    "size": human_size(item.file_size_bytes),
                    "date": item.downloaded_at.astimezone().strftime("%d %b %Y"),
                    "path": str(item.local_path),
                    "missing": not item.local_path.exists(),
                }
            )
        self._library_model.replace(rows)

    @Slot(str)
    def removeFromLibrary(self, key: str) -> None:  # noqa: N802
        self._archive.remove(key)
        self._refresh_library()

    @Slot(str)
    def openPath(self, path: str) -> None:  # noqa: N802
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
            self.toast.emit("This file can't be opened")

    @Slot(str)
    def revealPath(self, path: str) -> None:  # noqa: N802
        # explorer needs this exact quoting, which a list argument can't produce.
        subprocess.Popen(f'explorer /select,"{Path(path)}"')

    @Slot(QUrl)
    def setDestination(self, url: QUrl) -> None:  # noqa: N802
        folder = Path(url.toLocalFile()).resolve()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.toast.emit("That folder can't be used")
            return
        self._settings.update(replace(self._settings.current, last_download_directory=folder))
        self.settingsChanged.emit()

    @Slot(str)
    def setQuality(self, quality: str) -> None:  # noqa: N802
        self._settings.update(replace(self._settings.current, video_quality=VideoQuality(quality)))
        self.settingsChanged.emit()

    def _destination(self) -> Path:
        chosen = self._settings.current.last_download_directory
        return chosen or (user_downloads_path() / "YT Tinker")

    def _show_dependencies(self, outcome: Any) -> None:
        if isinstance(outcome, Exception):
            return
        self._dependencies = [
            {"name": status.name, "available": status.available, "detail": status.detail}
            for status in outcome
        ]
        self.dependenciesChanged.emit()

    # Plumbing

    def shutdown(self) -> None:
        """Saves the queue and stops downloads; their partial files resume on the next launch."""
        self._store.save(self._queue.items)
        for worker in self._workers.values():
            worker.cancel()
        for worker in self._workers.values():
            worker.wait(3000)

    def _background(self, work: Callable[[], Any], done: Callable[[Any], None]) -> None:
        def run() -> None:
            try:
                outcome = work()
            except Exception as error:  # Reported to the UI through done().
                outcome = error
            self._task_finished.emit((done, outcome))

        QThreadPool.globalInstance().start(run)

    @Slot(object)
    def _finish_task(self, payload: tuple[Callable[[Any], None], Any]) -> None:
        done, outcome = payload
        done(outcome)

    def _row_index(self, item_id: UUID) -> int:
        target = str(item_id)
        return next(i for i, row in enumerate(self._downloads_model.rows) if row["rowId"] == target)

    def _update_row(self, item: QueueItem) -> None:
        self._downloads_model.patch(self._row_index(item.id), self._row(item))

    def _row(self, item: QueueItem) -> dict[str, Any]:
        result = item.results[0] if item.results else None
        return {
            "rowId": str(item.id),
            "title": item.title or item.request.source_url,
            "thumbnail": item.thumbnail_url or "",
            "status": item.status.value,
            "detail": _detail(item),
            "fraction": 1.0 if item.status is QueueStatus.COMPLETED else item.progress.fraction,
            "audio": item.request.media_format is DownloadFormat.AUDIO_MP3,
            "path": str(result.local_path) if result else "",
            "collection": item.request.collection or "",
        }

    # QML properties

    searching = Property(bool, lambda self: self._searching, notify=searchChanged)
    searchError = Property(str, lambda self: self._search_error, notify=searchChanged)  # noqa: N815
    hasPreview = Property(bool, lambda self: self._preview is not None, notify=searchChanged)  # noqa: N815
    preview = Property(
        "QVariantMap",  # type: ignore[arg-type]
        lambda self: _preview_map(self._preview),
        notify=searchChanged,
    )
    results = Property(QObject, lambda self: self._results_model, constant=True)
    downloads = Property(QObject, lambda self: self._downloads_model, constant=True)
    library = Property(QObject, lambda self: self._library_model, constant=True)
    destination = Property(str, lambda self: str(self._destination()), notify=settingsChanged)
    quality = Property(
        str, lambda self: self._settings.current.video_quality.value, notify=settingsChanged
    )
    dependencies = Property(
        "QVariantList",  # type: ignore[arg-type]
        lambda self: self._dependencies,
        notify=dependenciesChanged,
    )
    reduceMotion = Property(bool, lambda self: _reduce_motion(), constant=True)  # noqa: N815

    @Property(int, notify=summaryChanged)
    def activeCount(self) -> int:  # noqa: N802
        return sum(item.status in _WAITING - {QueueStatus.PAUSED} for item in self._queue.items)

    @Property(str, notify=summaryChanged)
    def speedText(self) -> str:  # noqa: N802
        speeds = [
            item.progress.speed_bytes_per_second or 0.0
            for item in self._queue.items
            if item.status is QueueStatus.DOWNLOADING
        ]
        return human_speed(sum(speeds)) if any(speeds) else ""

    @Property(float, notify=summaryChanged)
    def overallFraction(self) -> float:  # noqa: N802
        return self._queue.overall_progress()

    @Property(bool, notify=summaryChanged)
    def canClear(self) -> bool:  # noqa: N802
        return any(item.status not in _WAITING for item in self._queue.items)

    @Property(bool, notify=summaryChanged)
    def canPause(self) -> bool:  # noqa: N802
        return any(item.status in _WAITING - {QueueStatus.PAUSED} for item in self._queue.items)

    @Property(bool, notify=summaryChanged)
    def canResume(self) -> bool:  # noqa: N802
        return any(item.status is QueueStatus.PAUSED for item in self._queue.items)


def _result_row(result: SearchResult, downloaded: bool) -> dict[str, Any]:
    parts = [result.channel or "", human_views(result.view_count)]
    return {
        "sourceId": result.source_id,
        "title": result.title,
        "thumbnail": result.thumbnail_url or "",
        "duration": human_duration(result.duration_seconds),
        "meta": " · ".join(part for part in parts if part),
        "downloaded": downloaded,
    }


def _video_count(count: int) -> str:
    return "1 video" if count == 1 else f"{count} videos"


def _preview_map(preview: Preview | None) -> dict[str, Any]:
    if preview is None:
        return {}
    count = len(preview.entries)
    parts = [
        preview.channel or "",
        _video_count(count) if count else human_duration(preview.duration_seconds),
    ]
    return {
        "title": preview.title,
        "thumbnail": preview.thumbnail_url or "",
        "meta": " · ".join(part for part in parts if part),
        "isPlaylist": count > 0,
        "hasVideo": bool(preview.video_url),
    }


def _detail(item: QueueItem) -> str:
    progress = item.progress
    if item.status is QueueStatus.DOWNLOADING:
        parts = [f"{progress.percent}%"]
        if progress.speed_bytes_per_second:
            parts.append(human_speed(progress.speed_bytes_per_second))
        if progress.eta_seconds is not None:
            parts.append(human_eta(progress.eta_seconds))
        return " · ".join(parts)
    if item.status is QueueStatus.PAUSED:
        return f"Paused · {progress.percent}%"
    if item.status is QueueStatus.FAILED and item.error:
        return item.error.message
    if item.status is QueueStatus.COMPLETED and item.results:
        result = item.results[0]
        kind = "MP3" if result.media_format is DownloadFormat.AUDIO_MP3 else "MP4"
        return f"{kind} · {human_size(result.file_size_bytes)}"
    return {
        QueueStatus.QUEUED: "Waiting",
        QueueStatus.PREPARING: "Getting ready…",
        QueueStatus.PROCESSING: "Finishing up…",
    }.get(item.status, "")


def _short_error(error: Exception) -> str:
    text = str(error).removeprefix("ERROR: ")
    return text.split(";")[0][:160] or "That didn't work. Try again."


def _reduce_motion() -> bool:
    enabled = ctypes.c_int(1)
    ctypes.windll.user32.SystemParametersInfoW(
        _SPI_GETCLIENTAREAANIMATION, 0, ctypes.byref(enabled), 0
    )
    return not enabled.value
