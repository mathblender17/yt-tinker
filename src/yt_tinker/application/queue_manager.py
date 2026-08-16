from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from yt_tinker.domain.models import DownloadProgress, QueueItem, QueueStatus


class InvalidQueueTransitionError(ValueError):
    """Raised when an item is moved through an invalid lifecycle transition."""


_TRANSITIONS: dict[QueueStatus, set[QueueStatus]] = {
    QueueStatus.QUEUED: {QueueStatus.PREPARING, QueueStatus.CANCELLED},
    QueueStatus.PREPARING: {QueueStatus.DOWNLOADING, QueueStatus.FAILED, QueueStatus.CANCELLED},
    QueueStatus.DOWNLOADING: {
        QueueStatus.PROCESSING,
        QueueStatus.COMPLETED,
        QueueStatus.FAILED,
        QueueStatus.CANCELLED,
    },
    QueueStatus.PROCESSING: {QueueStatus.COMPLETED, QueueStatus.FAILED, QueueStatus.CANCELLED},
    QueueStatus.COMPLETED: set(),
    QueueStatus.FAILED: set(),
    QueueStatus.CANCELLED: set(),
}


class QueueManager:
    """Owns queue order and lifecycle state; it intentionally has no Qt dependency."""

    def __init__(self) -> None:
        self._items: list[QueueItem] = []
        self._paused = False
        self._active_id: UUID | None = None

    @property
    def items(self) -> Sequence[QueueItem]:
        return tuple(self._items)

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def active_item(self) -> QueueItem | None:
        return self._find(self._active_id) if self._active_id else None

    def add(self, item: QueueItem) -> None:
        self._items.append(item)

    def remove(self, item_id: UUID) -> None:
        item = self._find_required(item_id)
        if item_id == self._active_id:
            raise ValueError("The active item must be cancelled before it can be removed.")
        self._items.remove(item)

    def get(self, item_id: UUID) -> QueueItem | None:
        return self._find(item_id)

    def reorder(self, item_id: UUID, target_index: int) -> None:
        if not 0 <= target_index < len(self._items):
            raise IndexError("Queue target index is out of range.")
        item = self._find_required(item_id)
        if item_id == self._active_id:
            raise ValueError("The active item cannot be reordered.")
        self._items.remove(item)
        self._items.insert(target_index, item)

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def start_next(self) -> QueueItem | None:
        if self._paused or self._active_id is not None:
            return None
        next_item = next((item for item in self._items if item.status is QueueStatus.QUEUED), None)
        if next_item is None:
            return None
        self.transition(next_item.id, QueueStatus.PREPARING)
        self._active_id = next_item.id
        return next_item

    def transition(self, item_id: UUID, target: QueueStatus) -> None:
        item = self._find_required(item_id)
        if target not in _TRANSITIONS[item.status]:
            raise InvalidQueueTransitionError(f"Cannot transition {item.status} to {target}.")
        item.status = target
        if target in {QueueStatus.COMPLETED, QueueStatus.FAILED, QueueStatus.CANCELLED}:
            if self._active_id == item_id:
                self._active_id = None

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
