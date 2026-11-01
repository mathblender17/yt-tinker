from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from yt_tinker.domain.models import DownloadProgress, QueueItem, QueueStatus


class InvalidQueueTransitionError(ValueError):
    """Raised when an item is moved through an invalid lifecycle transition."""


_TRANSITIONS: dict[QueueStatus, set[QueueStatus]] = {
    QueueStatus.QUEUED: {QueueStatus.PREPARING, QueueStatus.PAUSED, QueueStatus.CANCELLED},
    QueueStatus.PREPARING: {
        QueueStatus.DOWNLOADING,
        QueueStatus.PROCESSING,  # Every stream was already on disk from an earlier attempt.
        QueueStatus.PAUSED,
        QueueStatus.COMPLETED,
        QueueStatus.FAILED,
        QueueStatus.CANCELLED,
    },
    QueueStatus.DOWNLOADING: {
        QueueStatus.PROCESSING,
        QueueStatus.PAUSED,
        QueueStatus.COMPLETED,
        QueueStatus.FAILED,
        QueueStatus.CANCELLED,
    },
    QueueStatus.PROCESSING: {
        QueueStatus.PAUSED,
        QueueStatus.COMPLETED,
        QueueStatus.FAILED,
        QueueStatus.CANCELLED,
    },
    QueueStatus.PAUSED: {QueueStatus.QUEUED, QueueStatus.CANCELLED},
    QueueStatus.COMPLETED: set(),
    QueueStatus.FAILED: {QueueStatus.QUEUED},
    QueueStatus.CANCELLED: {QueueStatus.QUEUED},
}
_FINISHED = {
    QueueStatus.PAUSED,
    QueueStatus.COMPLETED,
    QueueStatus.FAILED,
    QueueStatus.CANCELLED,
}


class QueueManager:
    """Owns queue order and lifecycle state; it intentionally has no Qt dependency."""

    def __init__(self, max_active: int = 3) -> None:
        self._items: list[QueueItem] = []
        self._max_active = max_active
        self._paused = False
        self._active_ids: set[UUID] = set()

    @property
    def items(self) -> Sequence[QueueItem]:
        return tuple(self._items)

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def active_items(self) -> list[QueueItem]:
        return [item for item in self._items if item.id in self._active_ids]

    def add(self, item: QueueItem) -> None:
        self._items.append(item)

    def remove(self, item_id: UUID) -> None:
        item = self._find_required(item_id)
        if item_id in self._active_ids:
            raise ValueError("The active item must be cancelled before it can be removed.")
        self._items.remove(item)

    def get(self, item_id: UUID) -> QueueItem | None:
        return self._find(item_id)

    def reorder(self, item_id: UUID, target_index: int) -> None:
        if not 0 <= target_index < len(self._items):
            raise IndexError("Queue target index is out of range.")
        item = self._find_required(item_id)
        if item_id in self._active_ids:
            raise ValueError("The active item cannot be reordered.")
        self._items.remove(item)
        self._items.insert(target_index, item)

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def start_next(self) -> QueueItem | None:
        if self._paused or len(self._active_ids) >= self._max_active:
            return None
        next_item = next((item for item in self._items if item.status is QueueStatus.QUEUED), None)
        if next_item is None:
            return None
        self.transition(next_item.id, QueueStatus.PREPARING)
        self._active_ids.add(next_item.id)
        return next_item

    def transition(self, item_id: UUID, target: QueueStatus) -> None:
        item = self._find_required(item_id)
        if target not in _TRANSITIONS[item.status]:
            raise InvalidQueueTransitionError(f"Cannot transition {item.status} to {target}.")
        item.status = target
        if target in _FINISHED:
            self._active_ids.discard(item_id)

    def update_progress(self, item_id: UUID, progress: DownloadProgress) -> None:
        item = self._find_required(item_id)
        item.progress = progress

    def overall_progress(self) -> float:
        relevant = [item for item in self._items if item.status is not QueueStatus.CANCELLED]
        if not relevant:
            return 0.0
        return sum(
            1.0 if item.status is QueueStatus.COMPLETED else item.progress.fraction
            for item in relevant
        ) / len(relevant)

    def _find(self, item_id: UUID | None) -> QueueItem | None:
        return next((item for item in self._items if item.id == item_id), None)

    def _find_required(self, item_id: UUID) -> QueueItem:
        item = self._find(item_id)
        if item is None:
            raise KeyError(f"Unknown queue item: {item_id}")
        return item
