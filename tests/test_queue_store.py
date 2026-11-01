from pathlib import Path

from yt_tinker.domain.models import (
    DownloadFormat,
    DownloadRequest,
    QueueItem,
    QueueStatus,
    VideoQuality,
)
from yt_tinker.infrastructure.queue_json import QueueStore


def _request() -> DownloadRequest:
    return DownloadRequest(
        "https://youtu.be/abc",
        Path("C:/Media"),
        DownloadFormat.AUDIO_MP3,
        quality=VideoQuality.MAXIMUM,
        collection="Mix",
        index=4,
    )


def test_unfinished_items_come_back_and_active_ones_are_requeued(tmp_path: Path) -> None:
    store = QueueStore(tmp_path / "queue.json")
    active = QueueItem(_request(), status=QueueStatus.DOWNLOADING, title="Song")
    paused = QueueItem(_request(), status=QueueStatus.PAUSED)
    done = QueueItem(_request(), status=QueueStatus.COMPLETED)
    store.save([active, paused, done])

    restored = store.load()

    assert [item.status for item in restored] == [QueueStatus.QUEUED, QueueStatus.PAUSED]
    assert restored[0].request == _request()
    assert restored[0].title == "Song"


def test_corrupt_queue_file_starts_empty(tmp_path: Path) -> None:
    path = tmp_path / "queue.json"
    path.write_text("{broken", encoding="utf-8")
    assert QueueStore(path).load() == []
