from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from yt_tinker.domain.models import DownloadFormat, DownloadMode


@dataclass(frozen=True, slots=True)
class AppSettings:
    last_download_directory: Path | None = None
    preferred_format: DownloadFormat = DownloadFormat.VIDEO_MP4
    preferred_mode: DownloadMode = DownloadMode.SINGLE
    compact_logs: bool = True


class SettingsRepository(Protocol):
    def load(self) -> AppSettings: ...

    def save(self, settings: AppSettings) -> None: ...


class SettingsService:
    def __init__(self, repository: SettingsRepository) -> None:
        self._repository = repository
        self._settings = repository.load()

    @property
    def current(self) -> AppSettings:
        return self._settings

    def update(self, settings: AppSettings) -> None:
        self._repository.save(settings)
        self._settings = settings
