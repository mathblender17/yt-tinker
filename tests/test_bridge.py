from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from threading import Event

import pytest
from PySide6.QtCore import QCoreApplication, QElapsedTimer

from yt_tinker.application.download_service import DownloadCancelled, DownloadService
from yt_tinker.application.search_service import Preview, SearchResult, SearchService
from yt_tinker.application.settings_service import AppSettings, SettingsRepository, SettingsService
from yt_tinker.domain.models import (
    DownloadFormat,
    DownloadProgress,
    DownloadRequest,
    DuplicateDownload,
    MediaItem,
    QueueStatus,
)
from yt_tinker.infrastructure.duplicate_archive import DownloadArchive
from yt_tinker.infrastructure.queue_json import QueueStore
from yt_tinker.ui.bridge import Bridge


@pytest.fixture(scope="module")
def qt_app() -> QCoreApplication:
    return QCoreApplication.instance() or QCoreApplication([])


class Provider:
    def search(self, query: str, limit: int = 24) -> list[SearchResult]:
        return []

    def inspect(self, url: str) -> Preview:
        return Preview(url, "Title")


class Settings(SettingsRepository):
    def __init__(self, folder: Path) -> None:
        self.folder = folder

    def load(self) -> AppSettings:
        return AppSettings(self.folder)

    def save(self, settings: AppSettings) -> None: ...


class FakeDownloader:
    def __init__(self) -> None:
        self.release = Event()
        self.discarded: list[DownloadRequest] = []

    def download(
        self,
        request: DownloadRequest,
        on_progress: Callable[[DownloadProgress], None],
        on_status: Callable[[QueueStatus], None],
        is_cancelled: Callable[[], bool],
    ) -> list[MediaItem] | DuplicateDownload:
        on_status(QueueStatus.DOWNLOADING)
        on_progress(DownloadProgress(fraction=0.5))
        while not self.release.wait(0.01):
            if is_cancelled():
                raise DownloadCancelled()
        return [MediaItem("id", request.source_url, "Done", request.media_format, Path("x.mp4"))]

    def discard(self, request: DownloadRequest) -> None:
        self.discarded.append(request)


def _bridge(tmp_path: Path, downloader: FakeDownloader) -> Bridge:
    return Bridge(
        SearchService(Provider()),
        DownloadService(downloader),
        DownloadArchive(tmp_path / "archive.json"),
        SettingsService(Settings(tmp_path)),
        QueueStore(tmp_path / "queue.json"),
    )


def _wait_until(condition: Callable[[], bool]) -> None:
    timer = QElapsedTimer()
    timer.start()
    while not condition():
        QCoreApplication.processEvents()
        assert timer.elapsed() < 3000, "timed out"


def _status(bridge: Bridge) -> list[str]:
    return [row["status"] for row in bridge.downloads.rows]


def test_download_runs_to_completion_and_lands_in_the_library(
    qt_app: QCoreApplication, tmp_path: Path
) -> None:
    downloader = FakeDownloader()
    bridge = _bridge(tmp_path, downloader)
    bridge._enqueue("https://youtu.be/a", "A", None, False)
    _wait_until(lambda: _status(bridge) == ["downloading"])
    assert bridge.activeCount == 1

    downloader.release.set()
    _wait_until(lambda: _status(bridge) == ["completed"])
    assert bridge.downloads.rows[0]["title"] == "Done"
    assert bridge.activeCount == 0


def test_pause_keeps_partial_files_and_cancel_removes_them(
    qt_app: QCoreApplication, tmp_path: Path
) -> None:
    downloader = FakeDownloader()
    bridge = _bridge(tmp_path, downloader)
    bridge._enqueue("https://youtu.be/a", "A", None, False)
    _wait_until(lambda: _status(bridge) == ["downloading"])

    bridge.pause(bridge.downloads.rows[0]["rowId"])
    _wait_until(lambda: _status(bridge) == ["paused"])
    assert downloader.discarded == []

    bridge.resume(bridge.downloads.rows[0]["rowId"])
    _wait_until(lambda: _status(bridge) == ["downloading"])
    bridge.cancel(bridge.downloads.rows[0]["rowId"])
    _wait_until(lambda: _status(bridge) == [])
    assert len(downloader.discarded) == 1


def test_the_same_link_and_format_is_only_queued_once(
    qt_app: QCoreApplication, tmp_path: Path
) -> None:
    downloader = FakeDownloader()
    bridge = _bridge(tmp_path, downloader)
    bridge._enqueue("https://youtu.be/a", "A", None, False)
    bridge._enqueue("https://youtu.be/a", "A", None, False)
    bridge._enqueue("https://youtu.be/a", "A", None, True)

    assert [row["audio"] for row in bridge.downloads.rows] == [False, True]
    assert bridge._queue.items[1].request.media_format is DownloadFormat.AUDIO_MP3
    downloader.release.set()
    _wait_until(lambda: _status(bridge) == ["completed", "completed"])


def test_saved_queue_starts_again_on_launch(qt_app: QCoreApplication, tmp_path: Path) -> None:
    first = FakeDownloader()
    bridge = _bridge(tmp_path, first)
    bridge._enqueue("https://youtu.be/a", "A", None, False)
    _wait_until(lambda: _status(bridge) == ["downloading"])
    bridge.shutdown()

    relaunched = FakeDownloader()
    relaunched.release.set()
    restored = _bridge(tmp_path, relaunched)
    _wait_until(lambda: _status(restored) == ["completed"])
