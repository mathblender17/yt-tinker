from __future__ import annotations

import gc
import hashlib
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
    DownloadProgress,
    DownloadRequest,
    DuplicateDownload,
    MediaItem,
    QueueStatus,
    VideoQuality,
)
from yt_tinker.infrastructure.duplicate_archive import DownloadArchive
from yt_tinker.infrastructure.filesystem import (
    playlist_destination,
    sanitize_windows_filename,
    youtube_video_id,
)

_LIVE_STATUSES = {"is_live", "is_upcoming", "post_live"}
_STANDARD_FORMAT = "bv*[vcodec^=avc1][height<=1080]+ba[ext=m4a]/b[height<=1080]/bv*+ba/b"
_MAXIMUM_FORMAT = "bv*+ba[ext=m4a]/bv*+ba/b"
# Direct HTTPS streams hold at about 1 MB/s per connection; HLS spreads over parallel
# fragments, so it wins any tie at the same resolution. Bitrate first keeps audio quality.
_VIDEO_SHARE = 0.92
_FORMAT_SORT = ["res", "fps", "abr", "proto:m3u8"]
# Forces YouTube's 16:9 thumbnails into the square album art music players expect.
_SQUARE_COVER = "crop='if(gt(ih,iw),iw,ih)':'if(gt(iw,ih),ih,iw)'"


class SilentLogger:
    """Failures arrive as exceptions; a windowed app has no console to print to."""

    def debug(self, message: str) -> None: ...

    def info(self, message: str) -> None: ...

    def warning(self, message: str) -> None: ...

    def error(self, message: str) -> None: ...


BASE_OPTIONS: dict[str, Any] = {
    "quiet": True,
    "noprogress": True,
    "no_warnings": True,
    "logger": SilentLogger(),
    "socket_timeout": 20,
    "extractor_retries": 3,
    "js_runtimes": {"deno": {}, "node": {}, "bun": {}},
}


class YoutubeDlClient(Protocol):
    def __enter__(self) -> YoutubeDlClient: ...

    def __exit__(self, *args: object) -> None: ...

    urlopen: Callable[[Any], Any]

    def extract_info(
        self, url: str, download: bool = True, process: bool = True
    ) -> dict[str, Any] | None: ...

    def process_ie_result(
        self, ie_result: dict[str, Any], download: bool = True
    ) -> dict[str, Any] | None: ...


YoutubeDlFactory = Callable[[dict[str, Any]], YoutubeDlClient]


class YtDlpDownloader:
    """yt-dlp adapter. It is the only layer that knows yt-dlp download option names."""

    def __init__(
        self,
        client_factory: YoutubeDlFactory | None = None,
        ffmpeg_locator: Callable[[], str | None] = lambda: shutil.which("ffmpeg"),
        monotonic: Callable[[], float] = time.monotonic,
        archive: DownloadArchive | None = None,
        prefetched: Callable[[str], dict[str, Any] | None] = lambda _url: None,
    ) -> None:
        self._client_factory = client_factory or _default_client_factory
        self._ffmpeg_locator = ffmpeg_locator
        self._monotonic = monotonic
        self._archive = archive
        self._prefetched = prefetched

    def download(
        self,
        request: DownloadRequest,
        on_progress: Callable[[DownloadProgress], None],
        on_status: Callable[[QueueStatus], None],
        is_cancelled: Callable[[], bool],
    ) -> list[MediaItem] | DuplicateDownload:
        if is_cancelled():
            raise DownloadCancelled()
        ffmpeg = self._ffmpeg_locator()
        if not ffmpeg:
            raise FfmpegUnavailableError()
        if not request.allow_duplicate and (
            existing := self._find_duplicate(youtube_video_id(request.source_url) or "", request)
        ):
            return DuplicateDownload(existing)

        latest_path: Path | None = None
        last_update = float("-inf")
        high_water = 0.0

        def report_progress(payload: dict[str, Any]) -> None:
            nonlocal last_update, high_water
            if is_cancelled():
                raise DownloadCancelled()
            status = payload.get("status")
            start, span = _stream_share(payload.get("info_dict") or {}, request)
            if status == "downloading":
                now = self._monotonic()
                if now - last_update < 0.2:
                    return
                last_update = now
                on_status(QueueStatus.DOWNLOADING)
                high_water = max(high_water, start + span * _stream_fraction(payload))
                on_progress(
                    DownloadProgress(
                        fraction=high_water,
                        speed_bytes_per_second=_number(payload.get("speed")),
                        eta_seconds=_integer(payload.get("eta")),
                    )
                )
            elif status == "finished":
                if start + span >= 1.0:
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
        try:
            metadata = self._metadata(request)
            if is_cancelled():
                raise DownloadCancelled()
            if metadata.get("live_status") in _LIVE_STATUSES:
                raise DownloaderExecutionError("Live streams can't be downloaded.")
            duplicate = self._find_duplicate(str(metadata.get("id", "")), request)
            if duplicate is not None and not request.allow_duplicate:
                return DuplicateDownload(duplicate)
            _output_root(request).mkdir(parents=True, exist_ok=True)
            if request.media_format is DownloadFormat.AUDIO_MP3:
                metadata = _with_likely_covers(metadata)
            options = self._options(request, ffmpeg, report_progress, report_postprocess, metadata)
            with self._client_factory(options) as client:
                client.urlopen = _cancellable(client.urlopen, is_cancelled)
                info = client.process_ie_result(metadata, download=True)
        except (DownloadCancelled, DownloaderExecutionError):
            raise
        except Exception as error:
            raise DownloaderExecutionError(str(error)) from error
        if is_cancelled():
            raise DownloadCancelled()
        if not info:
            raise DownloaderExecutionError("yt-dlp returned no media information.")
        item = _media_item(info, request, _final_path(info, latest_path, request))
        self.discard(request)
        if self._archive:
            self._archive.add(item, request.destination)
        return [item]

    def discard(self, request: DownloadRequest) -> None:
        gc.collect()  # A cancelled yt-dlp run leaves file handles open until collected.
        shutil.rmtree(_scratch_directory(request), ignore_errors=True)
        try:
            _scratch_directory(request).parent.rmdir()
        except OSError:
            pass  # Other downloads still use it, or it was never created.

    def _metadata(self, request: DownloadRequest) -> dict[str, Any]:
        cached = self._prefetched(request.source_url)
        if cached:
            return cached
        with self._client_factory({**BASE_OPTIONS, "noplaylist": True}) as client:
            metadata = client.extract_info(request.source_url, download=False, process=False)
        if not metadata:
            raise DownloaderExecutionError("yt-dlp returned no media information.")
        return metadata

    @staticmethod
    def _options(
        request: DownloadRequest,
        ffmpeg: str,
        progress_hook: Callable[[dict[str, Any]], None],
        postprocessor_hook: Callable[[dict[str, Any]], None],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        options: dict[str, Any] = {
            **BASE_OPTIONS,
            "noplaylist": True,
            "continuedl": True,
            "nopart": False,
            "overwrites": False,
            "retries": 10,
            "fragment_retries": 10,
            "file_access_retries": 5,
            "concurrent_fragment_downloads": request.connections,
            "windowsfilenames": True,
            "trim_file_name": 180,
            "paths": {"home": str(_output_root(request)), "temp": str(_scratch_directory(request))},
            "outtmpl": _output_template(request, metadata),
            "ffmpeg_location": str(Path(ffmpeg).parent),
            "progress_hooks": [progress_hook],
            "postprocessor_hooks": [postprocessor_hook],
        }
        if request.media_format is DownloadFormat.VIDEO_MP4:
            maximum = request.quality is VideoQuality.MAXIMUM
            options["format"] = _MAXIMUM_FORMAT if maximum else _STANDARD_FORMAT
            options["format_sort"] = _FORMAT_SORT
            options["merge_output_format"] = "mp4"
            options["postprocessors"] = [{"key": "FFmpegMetadata", "add_metadata": True}]
        else:
            options["format"] = "bestaudio/best"
            options["writethumbnail"] = True
            options["postprocessor_args"] = {
                "thumbnailsconvertor+ffmpeg_o": ["-vf", _SQUARE_COVER]
            }
            options["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "0"},
                {"key": "FFmpegThumbnailsConvertor", "format": "png"},
                {"key": "FFmpegMetadata", "add_metadata": True},
                {"key": "EmbedThumbnail"},
            ]
        return options

    def _find_duplicate(self, source_id: str, request: DownloadRequest) -> MediaItem | None:
        if self._archive is None or not source_id:
            return None
        return self._archive.find(source_id, request.media_format, request.destination)


def _default_client_factory(options: dict[str, Any]) -> YoutubeDlClient:
    import yt_dlp

    return cast(YoutubeDlClient, yt_dlp.YoutubeDL(options))


def _number(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None


def _integer(value: object) -> int | None:
    return int(value) if isinstance(value, int | float) else None


def _cancellable(
    urlopen: Callable[[Any], Any], is_cancelled: Callable[[], bool]
) -> Callable[[Any], Any]:
    """Queued fragments only notice a cancel in the progress hook, after each has opened its
    own connection; failing the request instead stops a large download in under a second."""

    def guarded(request: Any) -> Any:
        if is_cancelled():
            raise DownloadCancelled()
        return urlopen(request)

    return guarded


def _stream_fraction(payload: dict[str, Any]) -> float:
    """Fragment counts are exact; byte totals for HLS are early guesses that can read 100%."""
    if payload.get("fragment_count"):
        return min(float(payload.get("fragment_index", 0)) / float(payload["fragment_count"]), 1.0)
    total = payload.get("total_bytes") or payload.get("total_bytes_estimate")
    return min(float(payload.get("downloaded_bytes", 0)) / total, 1.0) if total else 0.0


def _stream_share(info: dict[str, Any], request: DownloadRequest) -> tuple[float, float]:
    """Where a stream sits on the 0-1 bar, so video then audio reads as one rising run.

    yt-dlp hides the stream list from progress hooks, but a video-only stream is always
    followed by audio, and audio is a small part of the bytes.
    """
    if request.media_format is DownloadFormat.AUDIO_MP3:
        return 0.0, 1.0
    if info.get("acodec") == "none":
        return 0.0, _VIDEO_SHARE
    if info.get("vcodec") == "none":
        return _VIDEO_SHARE, 1.0 - _VIDEO_SHARE
    return 0.0, 1.0


def _with_likely_covers(metadata: dict[str, Any]) -> dict[str, Any]:
    """yt-dlp probes dozens of thumbnail URLs one 404 at a time, which took 10s on older videos.

    These three cover almost every video, best first, and the last always exists.
    """
    source_id = metadata.get("id")
    if metadata.get("extractor_key") != "Youtube" or not source_id:
        return metadata
    names = ("mqdefault", "hq720", "maxresdefault")
    covers = [
        {"url": f"https://i.ytimg.com/vi/{source_id}/{name}.jpg", "preference": rank}
        for rank, name in enumerate(names)
    ]
    return {**metadata, "thumbnails": covers}


def _final_path(
    info: dict[str, Any], hook_path: Path | None, request: DownloadRequest
) -> Path:
    downloads = info.get("requested_downloads") or [{}]
    filename = downloads[-1].get("filepath") or hook_path or info.get("filepath")
    if filename:
        return Path(filename)
    return _output_root(request) / f"{_stem(request, info)}.{_extension(request)}"


def _output_root(request: DownloadRequest) -> Path:
    folder = "Video" if request.media_format is DownloadFormat.VIDEO_MP4 else "Audio"
    root = request.destination / folder
    return playlist_destination(root, request.collection) if request.collection else root


def _scratch_directory(request: DownloadRequest) -> Path:
    """Partial files stay here, out of the media folder, until the download succeeds."""
    identity = f"{request.source_url}|{request.media_format}|{request.quality}"
    digest = hashlib.sha1(identity.encode(), usedforsecurity=False).hexdigest()[:12]
    return _output_root(request) / ".partial" / digest


def _extension(request: DownloadRequest) -> str:
    return "mp4" if request.media_format is DownloadFormat.VIDEO_MP4 else "mp3"


def _output_template(request: DownloadRequest, metadata: dict[str, Any]) -> str:
    stem = _stem(request, metadata).replace("%", "%%")
    return f"{stem}.%(ext)s"


def _stem(request: DownloadRequest, metadata: dict[str, Any]) -> str:
    title = sanitize_windows_filename(str(metadata.get("title", "Untitled")))[:150].rstrip(". ")
    if request.index:
        title = f"{request.index:03d} {title}"
    root = _output_root(request)
    extension = _extension(request)
    if request.allow_duplicate:
        number = 1
        while (root / f"{title} (redownload {number}).{extension}").exists():
            number += 1
        return f"{title} (redownload {number})"
    if (root / f"{title}.{extension}").exists():  # A different video with the same title.
        return f"{title} [{metadata.get('id', 'unknown')}]"
    return title


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
        playlist_title=request.collection,
        file_size_bytes=_file_size(output),
    )


def _file_size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None
