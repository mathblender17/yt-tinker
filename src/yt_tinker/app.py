from __future__ import annotations

import sys
from pathlib import Path

from platformdirs import user_data_path
from PySide6.QtWidgets import QApplication

from yt_tinker.application.download_service import DownloadService
from yt_tinker.infrastructure.duplicate_archive import DownloadArchive
from yt_tinker.infrastructure.ytdlp_downloader import YtDlpDownloader
from yt_tinker.ui.main_window import MainWindow


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("YT Tinker")
    archive_path = Path(user_data_path("YT Tinker", appauthor=False)) / "download-archive.json"
    downloader = YtDlpDownloader(archive=DownloadArchive(archive_path))
    window = MainWindow(DownloadService(downloader))
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
