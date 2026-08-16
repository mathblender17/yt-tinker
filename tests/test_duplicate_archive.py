from pathlib import Path

from yt_tinker.domain.models import DownloadFormat, MediaItem
from yt_tinker.infrastructure.duplicate_archive import DownloadArchive


def _item(media_format: DownloadFormat) -> MediaItem:
    return MediaItem(
        source_id="dQw4w9WgXcQ",
        source_url="https://youtube.com/watch?v=dQw4w9WgXcQ",
        title="Example",
        media_format=media_format,
        local_path=Path("C:/Media/Video/Example.mp4"),
    )


def test_same_source_format_and_destination_is_a_duplicate(tmp_path: Path) -> None:
    archive = DownloadArchive(tmp_path / "archive.json")
    archive.add(_item(DownloadFormat.VIDEO_MP4), Path("C:/YT"))
    assert archive.find("dQw4w9WgXcQ", DownloadFormat.VIDEO_MP4, Path("C:/YT")) is not None


def test_same_source_with_different_format_or_destination_is_not_a_duplicate(
    tmp_path: Path,
) -> None:
    archive = DownloadArchive(tmp_path / "archive.json")
    archive.add(_item(DownloadFormat.VIDEO_MP4), Path("C:/YT"))
    assert archive.find("dQw4w9WgXcQ", DownloadFormat.AUDIO_MP3, Path("C:/YT")) is None
    assert archive.find("dQw4w9WgXcQ", DownloadFormat.VIDEO_MP4, Path("C:/Other")) is None
