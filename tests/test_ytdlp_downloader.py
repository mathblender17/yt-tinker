from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from yt_tinker.application.download_service import (
    DownloadCancelled,
    Downloader,
    DownloadService,
    FfmpegUnavailableError,
)
from yt_tinker.domain.models import (
    DownloadFormat,
    DownloadMode,
    DownloadProgress,
    DownloadRequest,
    DuplicateDownload,
    ErrorCategory,
    MediaItem,
    QueueStatus,
)
from yt_tinker.infrastructure.duplicate_archive import DownloadArchive
from yt_tinker.infrastructure.ytdlp_downloader import YtDlpDownloader


class FakeClient:
    def __init__(self, options: dict[str, Any], failure: Exception | None = None) -> None:
        self.options = options
        self.failure = failure

    def __enter__(self) -> FakeClient:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def extract_info(self, _url: str, download: bool) -> dict[str, Any]:
        if self.failure:
            raise self.failure
        if not download:
            return {
                "id": "abc123",
                "title": "Example",
                "webpage_url": "https://youtube.com/watch?v=abc123",
            }
        self.options["progress_hooks"][0](
            {
                "status": "downloading",
                "downloaded_bytes": 25,
                "total_bytes": 100,
                "speed": 2048,
                "eta": 12,
            }
        )
        self.options["progress_hooks"][0]({"status": "finished"})
        self.options["postprocessor_hooks"][0](
            {"status": "finished", "info_dict": {"filepath": "C:/Media/Example.mp4"}}
        )
        return {
            "id": "abc123",
            "title": "Example",
            "duration": 42,
            "webpage_url": "https://youtube.com/watch?v=abc123",
        }


def _request(media_format: DownloadFormat = DownloadFormat.VIDEO_MP4) -> DownloadRequest:
    return DownloadRequest(
        "https://youtube.com/watch?v=abc123",
        Path("C:/Media"),
        media_format,
        DownloadMode.SINGLE,
    )


def test_ytdlp_adapter_translates_progress_and_builds_mp4_options() -> None:
    captured: dict[str, Any] = {}
    progress: list[DownloadProgress] = []
    states: list[QueueStatus] = []

    def factory(options: dict[str, Any]) -> FakeClient:
        captured.update(options)
        return FakeClient(options)

    downloader = YtDlpDownloader(factory, lambda: "C:/Tools/ffmpeg.exe", lambda: 1.0)
    result = downloader.download(_request(), progress.append, states.append, lambda: False)

    assert captured["continuedl"] is True
    assert captured["retries"] == 3
    assert captured["format"] == "bv*+ba/b"
    assert captured["merge_output_format"] == "mp4"
    assert captured["paths"]["home"] == "C:\\Media\\Video"
    assert progress[0] == DownloadProgress(
        fraction=0.25, speed_bytes_per_second=2048.0, eta_seconds=12
    )
    assert states == [QueueStatus.PREPARING, QueueStatus.DOWNLOADING, QueueStatus.PROCESSING]
    assert result[0].local_path == Path("C:/Media/Example.mp4")
    assert result[0].media_format is DownloadFormat.VIDEO_MP4


def test_adapter_returns_duplicate_before_download_and_does_not_overwrite(tmp_path: Path) -> None:
    archive = DownloadArchive(tmp_path / "archive.json")
    archive.add(
        MediaItem(
            source_id="abc123",
            source_url="https://youtube.com/watch?v=abc123",
            title="Existing",
            media_format=DownloadFormat.VIDEO_MP4,
            local_path=Path("C:/Media/Video/Existing.mp4"),
        ),
        Path("C:/Media"),
    )
    calls: list[bool] = []

    class DuplicateClient(FakeClient):
        def extract_info(self, url: str, download: bool) -> dict[str, Any]:
            calls.append(download)
            return super().extract_info(url, download)

    downloader = YtDlpDownloader(
        lambda options: DuplicateClient(options), lambda: "C:/Tools/ffmpeg.exe", archive=archive
    )
    result = downloader.download(_request(), lambda _: None, lambda _: None, lambda: False)

    assert isinstance(result, DuplicateDownload)
    assert calls == [False]


@pytest.mark.parametrize(
    ("media_format", "folder", "extension"),
    [
        (DownloadFormat.VIDEO_MP4, "Video", "mp4"),
        (DownloadFormat.AUDIO_MP3, "Audio", "mp3"),
    ],
)
def test_intentional_redownload_succeeds_through_service_with_a_new_target(
    tmp_path: Path, media_format: DownloadFormat, folder: str, extension: str
) -> None:
    archive = DownloadArchive(tmp_path / "archive.json")
    original = MediaItem(
        source_id="abc123",
        source_url="https://youtube.com/watch?v=abc123",
        title="Example",
        media_format=media_format,
        local_path=tmp_path / folder / f"Example [abc123].{extension}",
    )
    archive.add(original, tmp_path)
    options_seen: list[dict[str, Any]] = []
    downloader = YtDlpDownloader(
        lambda options: FakeClient(options_seen.append(options) or options),
        lambda: "ffmpeg",
        archive=archive,
    )
    request = DownloadRequest(
        "https://youtube.com/watch?v=abc123",
        tmp_path,
        media_format,
        DownloadMode.SINGLE,
        allow_duplicate=True,
    )
    result = DownloadService(downloader).execute(request, lambda _: None, lambda _: None, lambda: False)

    assert not isinstance(result, DuplicateDownload)
    assert isinstance(result, list)
    assert "(redownload 1).%(ext)s" in options_seen[-1]["outtmpl"]
    assert options_seen[-1]["overwrites"] is False
    assert archive.find("abc123", media_format, tmp_path) == original


def test_repeated_redownload_increments_its_windows_safe_filename(tmp_path: Path) -> None:
    output_folder = tmp_path / "Video"
    output_folder.mkdir()
    (output_folder / "Example [abc123] (redownload 1).mp4").touch()
    options_seen: list[dict[str, Any]] = []
    request = DownloadRequest(
        "https://youtube.com/watch?v=abc123",
        tmp_path,
        DownloadFormat.VIDEO_MP4,
        DownloadMode.SINGLE,
        allow_duplicate=True,
    )
    downloader = YtDlpDownloader(
        lambda options: FakeClient(options_seen.append(options) or options), lambda: "ffmpeg"
    )
    downloader.download(request, lambda _: None, lambda _: None, lambda: False)

    assert "(redownload 2).%(ext)s" in options_seen[-1]["outtmpl"]


def test_ytdlp_adapter_configures_mp3_conversion() -> None:
    captured: dict[str, Any] = {}

    def factory(options: dict[str, Any]) -> FakeClient:
        captured.update(options)
        return FakeClient(options)

    downloader = YtDlpDownloader(factory, lambda: "C:/Tools/ffmpeg.exe", lambda: 1.0)
    result = downloader.download(
        _request(DownloadFormat.AUDIO_MP3), lambda _: None, lambda _: None, lambda: False
    )

    assert captured["format"] == "bestaudio/best"
    assert captured["paths"]["home"] == "C:\\Media\\Audio"
    assert captured["postprocessors"][0]["key"] == "FFmpegExtractAudio"
    assert captured["postprocessors"][0]["preferredcodec"] == "mp3"
    assert result[0].media_format is DownloadFormat.AUDIO_MP3


def test_adapter_requires_ffmpeg_before_starting_a_conversion_or_merge() -> None:
    downloader = YtDlpDownloader(lambda _: pytest.fail("client must not start"), lambda: None)
    with pytest.raises(FfmpegUnavailableError):
        downloader.download(_request(), lambda _: None, lambda _: None, lambda: False)


def test_adapter_cancels_cooperatively_when_the_cancel_token_is_set() -> None:
    downloader = YtDlpDownloader(lambda _: pytest.fail("client must not start"), lambda: "ffmpeg")
    with pytest.raises(DownloadCancelled):
        downloader.download(_request(), lambda _: None, lambda _: None, lambda: True)


class RaisingDownloader(Downloader):
    def __init__(self, error: Exception) -> None:
        self.error = error

    def download(
        self,
        request: DownloadRequest,
        on_progress: Callable[[DownloadProgress], None],
        on_status: Callable[[QueueStatus], None],
        is_cancelled: Callable[[], bool],
    ) -> list[object]:
        raise self.error


def test_download_service_maps_cancellation_ffmpeg_and_backend_errors() -> None:
    callbacks = (lambda _: None, lambda _: None, lambda: False)
    cancelled = DownloadService(RaisingDownloader(DownloadCancelled())).execute(
        _request(), *callbacks
    )
    missing = DownloadService(RaisingDownloader(FfmpegUnavailableError())).execute(
        _request(), *callbacks
    )
    network = DownloadService(RaisingDownloader(RuntimeError("Network timed out"))).execute(
        _request(), *callbacks
    )

    assert cancelled.category is ErrorCategory.CANCELLED
    assert missing.category is ErrorCategory.FFMPEG_MISSING
    assert network.category is ErrorCategory.NETWORK
