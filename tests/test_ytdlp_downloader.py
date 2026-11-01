from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from yt_tinker.application.download_service import (
    DownloadCancelled,
    Downloader,
    DownloaderExecutionError,
    DownloadService,
    FfmpegUnavailableError,
)
from yt_tinker.application.search_service import Preview, SearchResult, SearchService
from yt_tinker.domain.models import (
    DownloadFormat,
    DownloadProgress,
    DownloadRequest,
    DuplicateDownload,
    ErrorCategory,
    MediaItem,
    QueueStatus,
    VideoQuality,
)
from yt_tinker.infrastructure.duplicate_archive import DownloadArchive
from yt_tinker.infrastructure.ytdlp_downloader import YtDlpDownloader

VIDEO_URL = "https://youtube.com/watch?v=abc12345678"
INFO = {"id": "abc12345678", "title": "Example", "webpage_url": VIDEO_URL}


class FakeClient:
    extractions = 0

    def __init__(self, options: dict[str, Any], failure: Exception | None = None) -> None:
        self.options = options
        self.failure = failure

    def __enter__(self) -> FakeClient:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def urlopen(self, request: Any) -> Any:
        return request

    def extract_info(self, _url: str, download: bool = True, process: bool = True) -> dict[str, Any]:
        type(self).extractions += 1
        if self.failure:
            raise self.failure
        return dict(INFO)

    def process_ie_result(self, ie_result: dict[str, Any], download: bool = True) -> dict[str, Any]:
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
        return {**ie_result, "duration": 42}


def _request(
    destination: Path, media_format: DownloadFormat = DownloadFormat.VIDEO_MP4
) -> DownloadRequest:
    return DownloadRequest(VIDEO_URL, destination, media_format)


def _capturing(seen: list[dict[str, Any]], client: type[FakeClient] = FakeClient) -> Any:
    def factory(options: dict[str, Any]) -> FakeClient:
        seen.append(options)
        return client(options)

    return factory


def _download(downloader: YtDlpDownloader, request: DownloadRequest) -> Any:
    return downloader.download(request, lambda _: None, lambda _: None, lambda: False)


def test_ytdlp_adapter_translates_progress_and_builds_mp4_options(tmp_path: Path) -> None:
    seen: list[dict[str, Any]] = []
    progress: list[DownloadProgress] = []
    states: list[QueueStatus] = []

    downloader = YtDlpDownloader(_capturing(seen), lambda: "C:/Tools/ffmpeg.exe", lambda: 1.0)
    result = downloader.download(_request(tmp_path), progress.append, states.append, lambda: False)

    captured = seen[-1]
    assert captured["continuedl"] is True
    assert captured["concurrent_fragment_downloads"] == 16
    assert captured["format"].startswith("bv*[vcodec^=avc1][height<=1080]")
    assert "proto:m3u8" in captured["format_sort"]
    assert captured["merge_output_format"] == "mp4"
    assert captured["paths"]["home"] == str(tmp_path / "Video")
    assert captured["paths"]["temp"].startswith(str(tmp_path / "Video" / ".partial"))
    assert captured["outtmpl"] == "Example.%(ext)s"
    assert progress[0] == DownloadProgress(
        fraction=0.25, speed_bytes_per_second=2048.0, eta_seconds=12
    )
    assert states == [QueueStatus.PREPARING, QueueStatus.DOWNLOADING, QueueStatus.PROCESSING]
    assert result[0].local_path == Path("C:/Media/Example.mp4")
    assert result[0].media_format is DownloadFormat.VIDEO_MP4


def test_metadata_is_fetched_once_and_a_preview_skips_the_fetch_entirely(tmp_path: Path) -> None:
    FakeClient.extractions = 0
    _download(YtDlpDownloader(FakeClient, lambda: "ffmpeg"), _request(tmp_path))
    assert FakeClient.extractions == 1

    FakeClient.extractions = 0
    downloader = YtDlpDownloader(FakeClient, lambda: "ffmpeg", prefetched=lambda _url: dict(INFO))
    _download(downloader, _request(tmp_path))
    assert FakeClient.extractions == 0


def test_video_and_audio_streams_read_as_one_rising_run(tmp_path: Path) -> None:
    class TwoStreams(FakeClient):
        def process_ie_result(
            self, ie_result: dict[str, Any], download: bool = True
        ) -> dict[str, Any]:
            hook = self.options["progress_hooks"][0]
            video, audio = {"acodec": "none"}, {"vcodec": "none"}
            for status, done, total, stream in (
                ("downloading", 150, 300, video),
                ("finished", 300, 300, video),
                ("downloading", 50, 100, audio),
                ("finished", 100, 100, audio),
            ):
                hook(
                    {
                        "status": status,
                        "downloaded_bytes": done,
                        "total_bytes": total,
                        "info_dict": stream,
                    }
                )
            return ie_result

    progress: list[float] = []
    states: list[QueueStatus] = []
    clock = iter(range(0, 100))
    downloader = YtDlpDownloader(TwoStreams, lambda: "ffmpeg", lambda: float(next(clock)))
    downloader.download(
        _request(tmp_path), lambda p: progress.append(p.fraction), states.append, lambda: False
    )

    assert progress == pytest.approx([0.46, 0.96, 1.0])
    assert states.count(QueueStatus.PROCESSING) == 1


def test_adapter_returns_duplicate_without_touching_the_network(tmp_path: Path) -> None:
    archive = DownloadArchive(tmp_path / "archive.json")
    existing = tmp_path / "Video" / "Existing.mp4"
    existing.parent.mkdir()
    existing.touch()
    archive.add(
        MediaItem(
            source_id="abc12345678",
            source_url=VIDEO_URL,
            title="Existing",
            media_format=DownloadFormat.VIDEO_MP4,
            local_path=existing,
        ),
        tmp_path,
    )
    downloader = YtDlpDownloader(
        lambda _: pytest.fail("client must not start"),
        lambda: "C:/Tools/ffmpeg.exe",
        archive=archive,
    )

    assert isinstance(_download(downloader, _request(tmp_path)), DuplicateDownload)


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
    local_path = tmp_path / folder / f"Example.{extension}"
    local_path.parent.mkdir()
    local_path.touch()
    original = MediaItem(
        source_id="abc12345678",
        source_url=VIDEO_URL,
        title="Example",
        media_format=media_format,
        local_path=local_path,
    )
    archive.add(original, tmp_path)
    seen: list[dict[str, Any]] = []
    downloader = YtDlpDownloader(_capturing(seen), lambda: "ffmpeg", archive=archive)
    request = DownloadRequest(VIDEO_URL, tmp_path, media_format, allow_duplicate=True)
    result = DownloadService(downloader).execute(
        request, lambda _: None, lambda _: None, lambda: False
    )

    assert isinstance(result, list)
    assert seen[-1]["outtmpl"] == "Example (redownload 1).%(ext)s"
    assert seen[-1]["overwrites"] is False


def test_repeated_redownload_increments_its_windows_safe_filename(tmp_path: Path) -> None:
    output_folder = tmp_path / "Video"
    output_folder.mkdir()
    (output_folder / "Example (redownload 1).mp4").touch()
    seen: list[dict[str, Any]] = []
    request = DownloadRequest(VIDEO_URL, tmp_path, DownloadFormat.VIDEO_MP4, allow_duplicate=True)
    _download(YtDlpDownloader(_capturing(seen), lambda: "ffmpeg"), request)

    assert "(redownload 2).%(ext)s" in seen[-1]["outtmpl"]


def test_a_different_video_with_the_same_title_gets_its_id_in_the_name(tmp_path: Path) -> None:
    (tmp_path / "Video").mkdir()
    (tmp_path / "Video" / "Example.mp4").touch()
    seen: list[dict[str, Any]] = []
    _download(YtDlpDownloader(_capturing(seen), lambda: "ffmpeg"), _request(tmp_path))

    assert seen[-1]["outtmpl"] == "Example [abc12345678].%(ext)s"


def test_percent_signs_in_titles_stay_literal_and_playlists_get_a_numbered_subfolder(
    tmp_path: Path,
) -> None:
    class PercentTitle(FakeClient):
        def extract_info(
            self, _url: str, download: bool = True, process: bool = True
        ) -> dict[str, Any]:
            return {**INFO, "title": "100% Real: Live"}

    seen: list[dict[str, Any]] = []
    request = DownloadRequest(
        VIDEO_URL, tmp_path, DownloadFormat.AUDIO_MP3, collection="Road: Trip", index=7
    )
    downloader = YtDlpDownloader(_capturing(seen, PercentTitle), lambda: "ffmpeg")
    result = _download(downloader, request)

    assert seen[-1]["outtmpl"] == "007 100%% Real_ Live.%(ext)s"
    assert seen[-1]["paths"]["home"] == str(tmp_path / "Audio" / "Road_ Trip")
    assert result[0].playlist_title == "Road: Trip"


def test_maximum_quality_keeps_the_highest_resolution_codec(tmp_path: Path) -> None:
    seen: list[dict[str, Any]] = []
    request = DownloadRequest(
        VIDEO_URL, tmp_path, DownloadFormat.VIDEO_MP4, quality=VideoQuality.MAXIMUM
    )
    _download(YtDlpDownloader(_capturing(seen), lambda: "ffmpeg"), request)

    assert "vcodec" not in seen[-1]["format"]


def test_live_streams_are_refused_before_downloading(tmp_path: Path) -> None:
    downloader = YtDlpDownloader(
        FakeClient, lambda: "ffmpeg", prefetched=lambda _url: {**INFO, "live_status": "is_live"}
    )
    with pytest.raises(DownloaderExecutionError):
        _download(downloader, _request(tmp_path))


def test_discard_removes_partial_files_but_leaves_finished_media(tmp_path: Path) -> None:
    seen: list[dict[str, Any]] = []
    downloader = YtDlpDownloader(_capturing(seen), lambda: "ffmpeg")
    _download(downloader, _request(tmp_path))
    scratch = Path(seen[-1]["paths"]["temp"])
    scratch.mkdir(parents=True)
    (scratch / "video.mp4.part").touch()
    (tmp_path / "Video" / "Done.mp4").touch()

    downloader.discard(_request(tmp_path))

    assert not scratch.parent.exists()
    assert (tmp_path / "Video" / "Done.mp4").exists()


def test_ytdlp_adapter_configures_mp3_conversion_with_cover_art(tmp_path: Path) -> None:
    seen: list[dict[str, Any]] = []
    downloader = YtDlpDownloader(_capturing(seen), lambda: "C:/Tools/ffmpeg.exe", lambda: 1.0)
    result = _download(downloader, _request(tmp_path, DownloadFormat.AUDIO_MP3))

    captured = seen[-1]
    assert captured["format"] == "bestaudio/best"
    assert captured["paths"]["home"] == str(tmp_path / "Audio")
    assert captured["writethumbnail"] is True
    assert [p["key"] for p in captured["postprocessors"]] == [
        "FFmpegExtractAudio",
        "FFmpegThumbnailsConvertor",
        "FFmpegMetadata",
        "EmbedThumbnail",
    ]
    assert captured["postprocessors"][0]["preferredcodec"] == "mp3"
    assert result[0].media_format is DownloadFormat.AUDIO_MP3


def test_mp3_cover_search_is_limited_so_old_videos_do_not_stall(tmp_path: Path) -> None:
    processed: list[dict[str, Any]] = []

    class Recording(FakeClient):
        def process_ie_result(
            self, ie_result: dict[str, Any], download: bool = True
        ) -> dict[str, Any]:
            processed.append(ie_result)
            return ie_result

    info = {**INFO, "extractor_key": "Youtube", "thumbnails": [{"url": "x"}] * 40}
    downloader = YtDlpDownloader(Recording, lambda: "ffmpeg", prefetched=lambda _url: info)
    _download(downloader, _request(tmp_path, DownloadFormat.AUDIO_MP3))

    assert [t["url"].rsplit("/", 1)[1] for t in processed[0]["thumbnails"]] == [
        "mqdefault.jpg",
        "hq720.jpg",
        "maxresdefault.jpg",
    ]


def test_adapter_requires_ffmpeg_before_starting_a_conversion_or_merge(tmp_path: Path) -> None:
    downloader = YtDlpDownloader(lambda _: pytest.fail("client must not start"), lambda: None)
    with pytest.raises(FfmpegUnavailableError):
        _download(downloader, _request(tmp_path))


def test_adapter_cancels_cooperatively_when_the_cancel_token_is_set(tmp_path: Path) -> None:
    downloader = YtDlpDownloader(lambda _: pytest.fail("client must not start"), lambda: "ffmpeg")
    with pytest.raises(DownloadCancelled):
        downloader.download(_request(tmp_path), lambda _: None, lambda _: None, lambda: True)


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


def test_cancel_stops_network_requests_that_are_still_queued(tmp_path: Path) -> None:
    cancelled = False

    class QueuedFragments(FakeClient):
        def process_ie_result(
            self, ie_result: dict[str, Any], download: bool = True
        ) -> dict[str, Any]:
            nonlocal cancelled
            assert self.urlopen("first fragment") == "first fragment"
            cancelled = True
            self.urlopen("next fragment")
            pytest.fail("request should not be sent")

    downloader = YtDlpDownloader(
        QueuedFragments, lambda: "ffmpeg", prefetched=lambda _url: dict(INFO)
    )
    with pytest.raises(DownloadCancelled):
        downloader.download(_request(tmp_path), lambda _: None, lambda _: None, lambda: cancelled)


def test_hls_progress_uses_fragment_counts_over_early_byte_guesses(tmp_path: Path) -> None:
    class Hls(FakeClient):
        def process_ie_result(
            self, ie_result: dict[str, Any], download: bool = True
        ) -> dict[str, Any]:
            self.options["progress_hooks"][0](
                {
                    "status": "downloading",
                    "downloaded_bytes": 900,
                    "total_bytes_estimate": 100,
                    "fragment_index": 3,
                    "fragment_count": 12,
                }
            )
            return ie_result

    progress: list[float] = []
    YtDlpDownloader(Hls, lambda: "ffmpeg").download(
        _request(tmp_path), lambda p: progress.append(p.fraction), lambda _: None, lambda: False
    )
    assert progress == [0.25]


def test_download_service_maps_cancellation_ffmpeg_and_backend_errors(tmp_path: Path) -> None:
    callbacks = (lambda _: None, lambda _: None, lambda: False)
    cancelled = DownloadService(RaisingDownloader(DownloadCancelled())).execute(
        _request(tmp_path), *callbacks
    )
    missing = DownloadService(RaisingDownloader(FfmpegUnavailableError())).execute(
        _request(tmp_path), *callbacks
    )
    network = DownloadService(RaisingDownloader(RuntimeError("Network timed out"))).execute(
        _request(tmp_path), *callbacks
    )

    assert cancelled.category is ErrorCategory.CANCELLED
    assert missing.category is ErrorCategory.FFMPEG_MISSING
    assert network.category is ErrorCategory.NETWORK


def test_search_results_are_cached_and_blank_queries_skip_the_provider() -> None:
    class CountingProvider:
        calls = 0

        def search(self, query: str, limit: int = 24) -> list[SearchResult]:
            self.calls += 1
            return [SearchResult("id", "url", query)]

        def inspect(self, url: str) -> Preview:
            return Preview(url, "title")

    provider = CountingProvider()
    service = SearchService(provider)

    assert service.search("   ") == []
    assert service.search("Lofi") == service.search(" lofi ")
    assert provider.calls == 1
