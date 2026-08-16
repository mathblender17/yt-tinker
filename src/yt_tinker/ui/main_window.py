from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import UUID

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from yt_tinker.application.download_service import DownloadService
from yt_tinker.application.queue_manager import InvalidQueueTransitionError, QueueManager
from yt_tinker.domain.models import (
    DownloadError,
    DownloadFormat,
    DownloadMode,
    DownloadProgress,
    DownloadRequest,
    DuplicateDownload,
    MediaItem,
    QueueItem,
    QueueStatus,
)
from yt_tinker.infrastructure.diagnostics import collect_dependency_status
from yt_tinker.infrastructure.filesystem import normalize_youtube_url
from yt_tinker.ui.download_worker import DownloadWorker


class MainWindow(QMainWindow):
    def __init__(self, download_service: DownloadService) -> None:
        super().__init__()
        self._download_service = download_service
        self._queue = QueueManager()
        self._active_item: QueueItem | None = None
        self._worker: DownloadWorker | None = None
        self._pending_duplicate: tuple[DuplicateDownload, DownloadRequest] | None = None
        self.setWindowTitle("YT Tinker")
        self.setMinimumSize(920, 640)
        self.resize(1100, 760)
        self._build_ui()
        self._apply_theme()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)
        layout.addWidget(self._header())
        tabs = QTabWidget()
        tabs.addTab(self._download_page(), "Download")
        tabs.addTab(self._search_page(), "Search")
        tabs.addTab(self._diagnostics_page(), "Diagnostics")
        layout.addWidget(tabs, 1)
        self.status_label = QLabel("Ready — add a URL to begin building your queue.")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)
        self.setCentralWidget(root)

    def _header(self) -> QWidget:
        frame = QFrame()
        header = QVBoxLayout(frame)
        header.setContentsMargins(0, 0, 0, 0)
        title = QLabel("YT TINKER")
        title.setObjectName("appTitle")
        subtitle = QLabel("A personal media downloader")
        subtitle.setObjectName("subtitle")
        header.addWidget(title)
        header.addWidget(subtitle)
        return frame

    def _download_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste a YouTube video URL")
        form.addRow("Source URL", self.url_input)
        selectors = QWidget()
        selector_layout = QHBoxLayout(selectors)
        selector_layout.setContentsMargins(0, 0, 0, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Video · MP4", "Audio · MP3"])
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Single video", "Full playlist"])
        selector_layout.addWidget(QLabel("Format"))
        selector_layout.addWidget(self.format_combo)
        selector_layout.addSpacing(12)
        selector_layout.addWidget(QLabel("Mode"))
        selector_layout.addWidget(self.mode_combo)
        selector_layout.addStretch()
        form.addRow("Download options", selectors)
        self.destination_input = QLineEdit()
        self.destination_input.setPlaceholderText("Choose a download folder")
        destination_row = QWidget()
        destination_layout = QHBoxLayout(destination_row)
        destination_layout.setContentsMargins(0, 0, 0, 0)
        destination_layout.addWidget(self.destination_input, 1)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._choose_destination)
        destination_layout.addWidget(browse_button)
        form.addRow("Save to", destination_row)
        layout.addLayout(form)
        controls = QHBoxLayout()
        self.add_button = QPushButton("Add to queue")
        self.add_button.clicked.connect(self._start_from_inputs)
        self.pause_button = QPushButton("Pause queue")
        self.pause_button.setEnabled(False)
        self.cancel_button = QPushButton("Cancel current")
        self.cancel_button.clicked.connect(self._cancel_current)
        self.cancel_button.setEnabled(False)
        controls.addWidget(self.add_button)
        controls.addWidget(self.pause_button)
        controls.addWidget(self.cancel_button)
        controls.addStretch()
        layout.addLayout(controls)
        layout.addWidget(QLabel("Queue"))
        self.queue_tree = QTreeWidget()
        self.queue_tree.setHeaderLabels(
            ["Status", "Title / URL", "Format", "Mode", "Progress", "Output"]
        )
        self.queue_tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.queue_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.queue_tree.setRootIsDecorated(False)
        self.queue_tree.itemSelectionChanged.connect(self._show_selected_details)
        self.queue_tree.setMinimumHeight(190)
        layout.addWidget(self.queue_tree, 1)
        detail_box = QFrame()
        detail_box.setObjectName("detailsBox")
        details = QFormLayout(detail_box)
        self.detail_title = QLabel("Select a queue item to see its details.")
        self.detail_format = QLabel("—")
        self.detail_status = QLabel("—")
        self.detail_url = QLabel("—")
        self.detail_path = QLabel("—")
        self.detail_size = QLabel("—")
        details.addRow("Title", self.detail_title)
        details.addRow("Format", self.detail_format)
        details.addRow("Status", self.detail_status)
        details.addRow("Source", self.detail_url)
        details.addRow("Output", self.detail_path)
        details.addRow("Size / completed", self.detail_size)
        detail_actions = QHBoxLayout()
        self.open_file_button = QPushButton("Open file")
        self.open_folder_button = QPushButton("Open folder")
        self.remove_button = QPushButton("Remove item")
        self.open_file_button.clicked.connect(self._open_selected_file)
        self.open_folder_button.clicked.connect(self._open_selected_folder)
        self.remove_button.clicked.connect(self._remove_selected)
        for button in (self.open_file_button, self.open_folder_button, self.remove_button):
            button.setEnabled(False)
            detail_actions.addWidget(button)
        detail_actions.addStretch()
        details.addRow(detail_actions)
        layout.addWidget(detail_box)
        self.queue_progress = QProgressBar()
        self.queue_progress.setValue(0)
        self.queue_progress.setFormat("Current item · waiting")
        layout.addWidget(self.queue_progress)
        self.url_input.textChanged.connect(self._update_download_controls)
        self.destination_input.textChanged.connect(self._update_download_controls)
        self.mode_combo.currentIndexChanged.connect(self._update_download_controls)
        self._refresh_queue()
        self._update_download_controls()
        return page

    def _choose_destination(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Choose download folder")
        if selected:
            self.destination_input.setText(selected)

    def _update_download_controls(self) -> None:
        valid = bool(self.url_input.text().strip() and self.destination_input.text().strip())
        single_mode = self.mode_combo.currentIndex() == 0
        self.add_button.setEnabled(self._worker is None and single_mode and valid)
        if not single_mode and self._worker is None:
            self.status_label.setText(
                "Playlist downloads are intentionally unavailable until Phase 4."
            )

    def _start_from_inputs(self) -> None:
        media_format = (
            DownloadFormat.VIDEO_MP4
            if self.format_combo.currentIndex() == 0
            else DownloadFormat.AUDIO_MP3
        )
        request = DownloadRequest(
            normalize_youtube_url(self.url_input.text()),
            Path(self.destination_input.text()),
            media_format,
            DownloadMode.SINGLE,
        )
        self._begin_download(request)

    def _begin_download(self, request: DownloadRequest) -> None:
        if self._worker is not None:
            return
        item = QueueItem(request)
        self._queue.add(item)
        self._active_item = self._queue.start_next()
        if self._active_item is None:
            return
        self._worker = DownloadWorker(self._download_service, request)
        self._worker.progress_changed.connect(self._on_progress)
        self._worker.status_changed.connect(self._on_status)
        self._worker.completed.connect(self._on_completed)
        self._worker.duplicate_found.connect(self._on_duplicate)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._on_worker_finished)
        self.add_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status_label.setText("Preparing media information…")
        self._refresh_queue()
        self._worker.start()

    def _cancel_current(self) -> None:
        if self._worker:
            self._worker.cancel()
            self.cancel_button.setEnabled(False)
            self.status_label.setText("Cancelling current download…")

    def _on_status(self, status: QueueStatus) -> None:
        if not self._active_item:
            return
        try:
            if status is not self._active_item.status:
                self._queue.transition(self._active_item.id, status)
        except InvalidQueueTransitionError:
            return
        self.status_label.setText(
            {
                QueueStatus.PREPARING: "Preparing media information…",
                QueueStatus.DOWNLOADING: "Downloading…",
                QueueStatus.PROCESSING: "Processing with FFmpeg…",
            }.get(status, "Working…")
        )
        self._refresh_queue()

    def _on_progress(self, progress: DownloadProgress) -> None:
        if not self._active_item:
            return
        self._queue.update_progress(self._active_item.id, progress)
        self.queue_progress.setValue(progress.percent)
        self.queue_progress.setFormat(f"Current item · {progress.percent}%")
        self._refresh_queue()

    def _on_completed(self, results: list[MediaItem]) -> None:
        if not self._active_item:
            return
        self._active_item.results = results
        self._active_item.title = results[0].title if results else self._active_item.title
        self._queue.transition(self._active_item.id, QueueStatus.COMPLETED)
        self.queue_progress.setValue(100)
        self.queue_progress.setFormat("Current item · completed")
        self.status_label.setText("Completed.")
        self.cancel_button.setEnabled(False)
        self._active_item = None
        self._refresh_queue()

    def _on_duplicate(self, duplicate: DuplicateDownload) -> None:
        if self._active_item:
            request = self._active_item.request
            self._active_item.title = duplicate.existing_item.title
            self._active_item.results = [duplicate.existing_item]
            self._queue.transition(self._active_item.id, QueueStatus.CANCELLED)
            self._active_item = None
            self._pending_duplicate = (duplicate, request)
        self.cancel_button.setEnabled(False)
        self._refresh_queue()

    def _show_duplicate_dialog(self, duplicate: DuplicateDownload, request: DownloadRequest) -> None:
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Already downloaded")
        dialog.setText("This video has already been downloaded in the selected folder and format.")
        dialog.setInformativeText(str(duplicate.existing_item.local_path))
        open_button = dialog.addButton("Open existing file", QMessageBox.ButtonRole.ActionRole)
        again_button = dialog.addButton("Download again", QMessageBox.ButtonRole.AcceptRole)
        dialog.addButton(QMessageBox.StandardButton.Cancel)
        dialog.buttonClicked.connect(
            lambda button: self._handle_duplicate_choice(
                button,
                open_button,
                again_button,
                duplicate.existing_item,
                request,
            )
        )
        dialog.open()

    def _handle_duplicate_choice(
        self,
        clicked: QPushButton,
        open_button: QPushButton,
        again_button: QPushButton,
        item: MediaItem,
        request: DownloadRequest,
    ) -> None:
        if clicked is open_button:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(item.local_path)))
        elif clicked is again_button:
            self._begin_download(replace(request, allow_duplicate=True))
        else:
            self.status_label.setText("Already downloaded.")

    def _on_failed(self, error: DownloadError) -> None:
        if not self._active_item:
            return
        self._active_item.error = error
        target = (
            QueueStatus.CANCELLED if error.category.value == "cancelled" else QueueStatus.FAILED
        )
        self._queue.transition(self._active_item.id, target)
        self.status_label.setText(
            "Cancelled." if target is QueueStatus.CANCELLED else "Download failed."
        )
        self.cancel_button.setEnabled(False)
        self._active_item = None
        self._refresh_queue()

    def _on_worker_finished(self) -> None:
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
        self._update_download_controls()
        if self._pending_duplicate:
            duplicate, request = self._pending_duplicate
            self._pending_duplicate = None
            self._show_duplicate_dialog(duplicate, request)

    def _refresh_queue(self) -> None:
        self.queue_tree.clear()
        for item in self._queue.items:
            result = item.results[0] if item.results else None
            title = item.title or (result.title if result else _short_url(item.request.source_url))
            row = QTreeWidgetItem(
                [
                    _status_label(item.status),
                    title,
                    _format_label(item.request.media_format),
                    item.request.mode.replace("_", " ").title(),
                    f"{item.progress.percent}%",
                    str(result.local_path) if result else "—",
                ]
            )
            row.setData(0, Qt.ItemDataRole.UserRole, str(item.id))
            self.queue_tree.addTopLevelItem(row)
        self.queue_tree.setVisible(bool(self._queue.items))

    def _selected_item(self) -> QueueItem | None:
        selected = self.queue_tree.selectedItems()
        if not selected:
            return None
        return self._queue.get(UUID(selected[0].data(0, Qt.ItemDataRole.UserRole)))

    def _show_selected_details(self) -> None:
        item = self._selected_item()
        result = item.results[0] if item and item.results else None
        self.open_file_button.setEnabled(bool(result and result.local_path.exists()))
        self.open_folder_button.setEnabled(bool(result and result.local_path.parent.exists()))
        self.remove_button.setEnabled(bool(item and item is not self._active_item))
        if not item:
            return
        self.detail_title.setText(
            item.title or (result.title if result else _short_url(item.request.source_url))
        )
        self.detail_format.setText(_format_label(item.request.media_format))
        self.detail_status.setText(_status_label(item.status))
        self.detail_url.setText(item.request.source_url)
        self.detail_path.setText(str(result.local_path) if result else "—")
        completed = result.downloaded_at.strftime("%Y-%m-%d %H:%M") if result else "—"
        self.detail_size.setText(
            f"{_file_size(result.file_size_bytes) if result else '—'} · {completed}"
        )

    def _open_selected_file(self) -> None:
        item = self._selected_item()
        if item and item.results:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(item.results[0].local_path)))

    def _open_selected_folder(self) -> None:
        item = self._selected_item()
        if item and item.results:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(item.results[0].local_path.parent)))

    def _remove_selected(self) -> None:
        item = self._selected_item()
        if item:
            self._queue.remove(item.id)
            self._refresh_queue()
            self._show_selected_details()

    def _search_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Search is intentionally scheduled for a later phase."), 1)
        return page

    def _diagnostics_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Dependency diagnostics"))
        self.diagnostics_list = QListWidget()
        layout.addWidget(self.diagnostics_list, 1)
        refresh = QPushButton("Refresh diagnostics")
        refresh.clicked.connect(self._refresh_diagnostics)
        layout.addWidget(refresh, 0, Qt.AlignmentFlag.AlignLeft)
        self._refresh_diagnostics()
        return page

    def _refresh_diagnostics(self) -> None:
        self.diagnostics_list.clear()
        for status in collect_dependency_status():
            marker = "✓" if status.available else "✗"
            self.diagnostics_list.addItem(f"{marker}  {status.name}: {status.detail}")

    def _apply_theme(self) -> None:
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #100d22; color: #f1efff; font-size: 14px; }
            #appTitle { font-size: 25px; font-weight: 800; letter-spacing: 3px; color: #b59cff; }
            #subtitle, #statusLabel { color: #aaa4c6; }
            QTabBar::tab { background: #1c1736; padding: 10px 22px; margin-right: 4px; }
            QTabBar::tab:selected { background: #6d4bd2; color: white; }
            QLineEdit, QComboBox, QListWidget, QTreeWidget { background: #1b1731; border: 1px solid #4a4171; border-radius: 6px; padding: 7px; }
            QTreeWidget::item { padding: 7px; } QTreeWidget::item:selected { background: #41336f; }
            QHeaderView::section { background: #241d43; padding: 7px; border: none; }
            #detailsBox { background: #17132a; border: 1px solid #39315c; border-radius: 7px; padding: 8px; }
            QPushButton { background: #6d4bd2; border: none; border-radius: 6px; padding: 10px 16px; font-weight: 600; }
            QPushButton:hover:!disabled { background: #8162e1; } QPushButton:disabled { background: #292440; color: #88819f; }
            QProgressBar { background: #211c3a; border: 1px solid #4a4171; border-radius: 5px; text-align: center; }
            QProgressBar::chunk { background: #7b5ce0; border-radius: 4px; }
        """)


def _status_label(status: QueueStatus) -> str:
    return {
        QueueStatus.COMPLETED: "✓ Completed",
        QueueStatus.FAILED: "✗ Failed",
        QueueStatus.CANCELLED: "⊘ Cancelled",
    }.get(status, status.replace("_", " ").title())


def _format_label(media_format: DownloadFormat) -> str:
    return "VIDEO · MP4" if media_format is DownloadFormat.VIDEO_MP4 else "AUDIO · MP3"


def _short_url(url: str) -> str:
    return url if len(url) <= 52 else f"{url[:49]}…"


def _file_size(size: int | None) -> str:
    if size is None:
        return "Size unavailable"
    return f"{size / (1024 * 1024):.1f} MiB"
