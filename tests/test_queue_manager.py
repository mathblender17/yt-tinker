from pathlib import Path

import pytest

from yt_tinker.application.queue_manager import InvalidQueueTransitionError, QueueManager
from yt_tinker.domain.models import (
    DownloadFormat,
    DownloadMode,
    DownloadProgress,
    DownloadRequest,
    QueueItem,
    QueueStatus,
)


def _item() -> QueueItem:
    return QueueItem(
        DownloadRequest(
            "https://youtube.com/watch?v=abc",
            Path("C:/Media"),
            DownloadFormat.VIDEO_MP4,
            DownloadMode.SINGLE,
        )
    )


def test_queue_allows_valid_lifecycle_and_calculates_overall_progress() -> None:
    manager = QueueManager()
    first, second = _item(), _item()
    manager.add(first)
    manager.add(second)
    assert manager.start_next() is first
    manager.transition(first.id, QueueStatus.DOWNLOADING)
    manager.update_progress(first.id, DownloadProgress(fraction=0.5))
    assert manager.overall_progress() == 0.25
    manager.transition(first.id, QueueStatus.COMPLETED)
    assert manager.overall_progress() == 0.5


def test_queue_rejects_invalid_transition_and_preserves_remaining_items_after_cancel() -> None:
    manager = QueueManager()
    first, second = _item(), _item()
    manager.add(first)
    manager.add(second)
    with pytest.raises(InvalidQueueTransitionError):
        manager.transition(first.id, QueueStatus.COMPLETED)
    manager.start_next()
    manager.transition(first.id, QueueStatus.CANCELLED)
    assert manager.start_next() is second


def test_pause_prevents_starting_a_new_item_without_mutating_its_state() -> None:
    manager = QueueManager()
    item = _item()
    manager.add(item)
    manager.pause()
    assert manager.start_next() is None
    assert item.status is QueueStatus.QUEUED


def test_completed_and_failed_items_remain_in_session_history() -> None:
    manager = QueueManager()
    completed, failed = _item(), _item()
    manager.add(completed)
    manager.add(failed)
    manager.start_next()
    manager.transition(completed.id, QueueStatus.DOWNLOADING)
    manager.transition(completed.id, QueueStatus.COMPLETED)
    manager.start_next()
    manager.transition(failed.id, QueueStatus.FAILED)

    assert manager.items == (completed, failed)
    assert completed.status is QueueStatus.COMPLETED
    assert failed.status is QueueStatus.FAILED
