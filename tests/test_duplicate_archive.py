from pathlib import Path

from yt_tinker.domain.models import DownloadFormat, MediaItem
from yt_tinker.infrastructure.duplicate_archive import DownloadArchive


def _item(media_format: DownloadFormat, tmp_path: Path) -> MediaItem:
    local_path = tmp_path / "Example.mp4"
    local_path.touch()
    return MediaItem(
        source_id="dQw4w9WgXcQ",
        source_url="https://youtube.com/watch?v=dQw4w9WgXcQ",
        title="Example",
        media_format=media_format,
        local_path=local_path,
    )


def test_same_source_format_and_destination_is_a_duplicate(tmp_path: Path) -> None:
    archive = DownloadArchive(tmp_path / "archive.json")
    archive.add(_item(DownloadFormat.VIDEO_MP4, tmp_path), Path("C:/YT"))
    assert archive.find("dQw4w9WgXcQ", DownloadFormat.VIDEO_MP4, Path("C:/YT")) is not None


def test_same_source_with_different_format_or_destination_is_not_a_duplicate(
    tmp_path: Path,
) -> None:
    archive = DownloadArchive(tmp_path / "archive.json")
    archive.add(_item(DownloadFormat.VIDEO_MP4, tmp_path), Path("C:/YT"))
    assert archive.find("dQw4w9WgXcQ", DownloadFormat.AUDIO_MP3, Path("C:/YT")) is None
    assert archive.find("dQw4w9WgXcQ", DownloadFormat.VIDEO_MP4, Path("C:/Other")) is None


def test_a_file_deleted_from_disk_is_no_longer_a_duplicate(tmp_path: Path) -> None:
    archive = DownloadArchive(tmp_path / "archive.json")
    item = _item(DownloadFormat.VIDEO_MP4, tmp_path)
    archive.add(item, Path("C:/YT"))
    item.local_path.unlink()
    assert archive.find("dQw4w9WgXcQ", DownloadFormat.VIDEO_MP4, Path("C:/YT")) is None


def test_entries_survive_a_reload_and_can_be_removed(tmp_path: Path) -> None:
    archive = DownloadArchive(tmp_path / "archive.json")
    archive.add(_item(DownloadFormat.VIDEO_MP4, tmp_path), Path("C:/YT"))
    reloaded = DownloadArchive(tmp_path / "archive.json")
    key, item = reloaded.entries()[0]
    assert item.title == "Example"
    reloaded.remove(key)
    assert DownloadArchive(tmp_path / "archive.json").entries() == []
