from __future__ import annotations

import shutil
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol, cast

from yt_tinker.application.download_service import (
    DownloadCancelled,
    DownloaderExecutionError,
    FfmpegUnavailableError,
)
from yt_tinker.domain.models import (
    DownloadFormat,
    DownloadMode,
    DownloadProgress,
    DownloadRequest,
    DuplicateDownload,
    MediaItem,
    QueueStatus,
)
from yt_tinker.infrastructure.duplicate_archive import DownloadArchive
from yt_tinker.infrastructure.filesystem import sanitize_windows_filename


class YoutubeDlClient(Protocol):
    def __enter__(self) -> YoutubeDlClient: ...

    def __exit__(self, *args: object) -> None: ...

    def extract_info(self, url: str, download: bool) -> dict[str, Any] | None: ...


YoutubeDlFactory = Callable[[dict[str, Any]], YoutubeDlClient]


class YtDlpDownloader:
    """yt-dlp adapter. It is the only layer that knows yt-dlp option names."""

    def __init__(
        self,
        client_factory: YoutubeDlFactory | None = None,
        ffmpeg_locator: Callable[[], str | None] = lambda: shutil.which("ffmpeg"),
        monotonic: Callable[[], float] = time.monotonic,
        archive: DownloadArchive | None = None,
    ) -> None:
        self._client_factory = client_factory or _default_client_factory
        self._ffmpeg_locator = ffmpeg_locator
        self._monotonic = monotonic
        self._archive = archive

    def download(
        self,
        request: DownloadRequest,
        on_progress: Callable[[DownloadProgress], None],
        on_status: Callable[[QueueStatus], None],
        is_cancelled: Callable[[], bool],
    ) -> list[MediaItem] | DuplicateDownload:
        if request.mode is not DownloadMode.SINGLE:
            raise DownloaderExecutionError("Playlist downloads are not available in this phase.")
        if is_cancelled():
            raise DownloadCancelled()
        ffmpeg = self._ffmpeg_locator()
        if not ffmpeg:
            raise FfmpegUnavailableError()

        latest_path: Path | None = None
        last_update = 0.0

        def report_progress(payload: dict[str, Any]) -> None:
            nonlocal last_update
            if is_cancelled():
                raise DownloadCancelled()
            status = payload.get("status")
            if status == "downloading":
                now = self._monotonic()
                if now - last_update < 0.2:
                    return
                last_update = now
                on_status(QueueStatus.DOWNLOADING)
                total = payload.get("total_bytes") or payload.get("total_bytes_estimate")
                fraction = float(payload.get("downloaded_bytes", 0)) / total if total else 0.0
                on_progress(
                    DownloadProgress(
                        fraction=fraction,
                        speed_bytes_per_second=_number(payload.get("speed")),
                        eta_seconds=_integer(payload.get("eta")),
                    )
                )
            elif status == "finished":
                on_status(QueueStatus.PROCESSING)
                on_progress(DownloadProgress(fraction=1.0))

        def report_postprocess(payload: dict[str, Any]) -> None:
            nonlocal latest_path
            if is_cancelled():
                raise DownloadCancelled()
            if payload.get("status") == "started":
                on_status(QueueStatus.PROCESSING)
            info = payload.get("info_dict") or {}
            if payload.get("status") == "finished" and info.get("filepath"):
                latest_path = Path(info["filepath"])

        on_status(QueueStatus.PREPARING)
        metadata_options = self._options(request, ffmpeg, report_progress, report_postprocess)
        try:
            with self._client_factory(metadata_options) as client:
                metadata = client.extract_info(request.source_url, download=False)
                if not metadata:
                    raise DownloaderExecutionError("yt-dlp returned no media information.")
                duplicate = self._find_duplicate(metadata, request)
                if duplicate is not None and not request.allow_duplicate:
                    return DuplicateDownload(duplicate)
            options = self._options(
                request, ffmpeg, report_progress, report_postprocess, metadata=metadata
            )
            with self._client_factory(options) as client:
                info = client.extract_info(request.source_url, download=True)
        except DownloadCancelled:
            raise
        except Exception as error:
            raise DownloaderExecutionError(str(error)) from error
        if is_cancelled():
            raise DownloadCancelled()
        if not info:
            raise DownloaderExecutionError("yt-dlp returned no media information.")
        output = latest_path or _output_path(info, request)
        item = _media_item(info, request, output)
        if self._archive:
            self._archive.add(item, request.destination)
        return [item]

    @staticmethod
    def _options(
        request: DownloadRequest,
        ffmpeg: str,
        progress_hook: Callable[[dict[str, Any]], None],
        postprocessor_hook: Callable[[dict[str, Any]], None],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        options: dict[str, Any] = {
            "noplaylist": True,
            "continuedl": True,
            "nopart": False,
            "overwrites": False,
            "retries": 3,
            "fragment_retries": 3,
            "windowsfilenames": True,
            "trim_file_name": 180,
            "paths": {"home": str(_output_root(request))},
            "outtmpl": _output_template(request, metadata),
            "ffmpeg_location": str(Path(ffmpeg).parent),
            "progress_hooks": [progress_hook],
            "postprocessor_hooks": [postprocessor_hook],
            "quiet": True,
            "no_warnings": False,
        }
        if request.media_format is DownloadFormat.VIDEO_MP4:
            options["format"] = "bv*+ba/b"
            options["merge_output_format"] = "mp4"
        else:
            options["format"] = "bestaudio/best"
            options["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
            ]
        return options

    def _find_duplicate(
        self, metadata: dict[str, Any], request: DownloadRequest
    ) -> MediaItem | None:
        if self._archive is None:
            return None
        source_id = str(metadata.get("id", ""))
        return (
            self._archive.find(source_id, request.media_format, request.destination)
            if source_id
            else None
        )


def _default_client_factory(options: dict[str, Any]) -> YoutubeDlClient:
    import yt_dlp

    return cast(YoutubeDlClient, yt_dlp.YoutubeDL(options))


def _number(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None


def _integer(value: object) -> int | None:
    return int(value) if isinstance(value, int | float) else None


def _output_path(info: dict[str, Any], request: DownloadRequest) -> Path:
    filename = info.get("filepath") or info.get("_filename")
    if filename:
        path = Path(filename)
        return (
            path.with_suffix(".mp3") if request.media_format is DownloadFormat.AUDIO_MP3 else path
        )
    extension = "mp3" if request.media_format is DownloadFormat.AUDIO_MP3 else "mp4"
    return (
        _output_root(request)
        / f"{info.get('title', 'Untitled')} [{info.get('id', 'unknown')}].{extension}"
    )


def _output_root(request: DownloadRequest) -> Path:
    folder = "Video" if request.media_format is DownloadFormat.VIDEO_MP4 else "Audio"
    return request.destination / folder


def _output_template(request: DownloadRequest, metadata: dict[str, Any] | None = None) -> str:
    if request.allow_duplicate:
        if metadata is None:
            return "%(title).180B [%(id)s] (redownload %(epoch)s).%(ext)s"
        stem = _next_redownload_stem(request, metadata)
        return f"{stem}.%(ext)s"
    return "%(title).180B [%(id)s].%(ext)s"


def _next_redownload_stem(request: DownloadRequest, metadata: dict[str, Any]) -> str:
    title = sanitize_windows_filename(str(metadata.get("title", "Untitled")))
    source_id = sanitize_windows_filename(str(metadata.get("id", "unknown")))
    extension = "mp4" if request.media_format is DownloadFormat.VIDEO_MP4 else "mp3"
    prefix = f"{title} [{source_id}]"
    number = 1
    while (_output_root(request) / f"{prefix} (redownload {number}).{extension}").exists():
        number += 1
    return f"{prefix} (redownload {number})"


def _media_item(info: dict[str, Any], request: DownloadRequest, output: Path) -> MediaItem:
    return MediaItem(
        source_id=str(info.get("id", "")),
        source_url=info.get("webpage_url") or request.source_url,
        title=str(info.get("title", "Untitled")),
        media_format=request.media_format,
        local_path=output,
        duration_seconds=_number(info.get("duration")),
        thumbnail_url=info.get("thumbnail"),
        artist=info.get("artist") or info.get("uploader"),
        album=info.get("album"),
        file_size_bytes=_file_size(output),
    )


def _file_size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None
