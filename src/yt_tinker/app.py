from __future__ import annotations

import ctypes
import importlib
import os
import sys
from pathlib import Path

from platformdirs import user_cache_path, user_data_path
from PySide6.QtCore import QObject, QThreadPool, QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkDiskCache
from PySide6.QtQml import QQmlApplicationEngine, QQmlNetworkAccessManagerFactory
from PySide6.QtQuick import QQuickWindow

from yt_tinker.application.download_service import DownloadService
from yt_tinker.application.search_service import SearchService
from yt_tinker.application.settings_service import SettingsService
from yt_tinker.infrastructure.duplicate_archive import DownloadArchive
from yt_tinker.infrastructure.queue_json import QueueStore
from yt_tinker.infrastructure.settings_json import JsonSettingsRepository
from yt_tinker.infrastructure.ytdlp_downloader import YtDlpDownloader
from yt_tinker.infrastructure.ytdlp_search import YtDlpSearchProvider
from yt_tinker.ui.bridge import Bridge

_QML = Path(__file__).parent / "ui" / "qml"
_APP_ID = "YTTinker.App"


class ThumbnailCacheFactory(QQmlNetworkAccessManagerFactory):
    """Keeps thumbnails on disk so a repeated search paints without the network."""

    def create(self, parent: QObject) -> QNetworkAccessManager:
        manager = QNetworkAccessManager(parent)
        cache = QNetworkDiskCache(manager)
        cache.setCacheDirectory(str(user_cache_path("YT Tinker", appauthor=False) / "thumbnails"))
        cache.setMaximumCacheSize(200 * 1024 * 1024)
        manager.setCache(cache)
        return manager


def main() -> int:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(_APP_ID)
    QQuickWindow.setTextRenderType(QQuickWindow.TextRenderType.NativeTextRendering)
    application = QGuiApplication(sys.argv)
    application.setApplicationName("YT Tinker")
    application.setWindowIcon(QIcon(str(_QML / "icon.svg")))
    # Importing yt-dlp takes over a second, so it happens before anyone needs it.
    QThreadPool.globalInstance().start(lambda: importlib.import_module("yt_dlp"))

    data = Path(user_data_path("YT Tinker", appauthor=False))
    archive = DownloadArchive(data / "download-archive.json")
    provider = YtDlpSearchProvider()
    downloader = YtDlpDownloader(archive=archive, prefetched=provider.take_prefetched)
    bridge = Bridge(
        SearchService(provider),
        DownloadService(downloader),
        archive,
        SettingsService(JsonSettingsRepository()),
        QueueStore(data / "queue.json"),
    )

    engine = QQmlApplicationEngine()
    thumbnail_cache = ThumbnailCacheFactory()
    engine.setNetworkAccessManagerFactory(thumbnail_cache)
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.load(QUrl.fromLocalFile(str(_QML / "Main.qml")))
    if not engine.rootObjects():
        return 1
    code = application.exec()
    bridge.shutdown()
    # Skips Qt teardown, which would wait on background searches and stalled connections.
    os._exit(code)


if __name__ == "__main__":
    raise SystemExit(main())
