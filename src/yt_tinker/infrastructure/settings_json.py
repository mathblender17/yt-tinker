from __future__ import annotations

import json
from pathlib import Path

from platformdirs import user_config_path

from yt_tinker.application.settings_service import AppSettings, SettingsRepository
from yt_tinker.domain.models import DownloadFormat, DownloadMode


class JsonSettingsRepository(SettingsRepository):
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or user_config_path("YT Tinker", appauthor=False) / "settings.json"

    def load(self) -> AppSettings:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return AppSettings(
                last_download_directory=Path(raw["last_download_directory"])
                if raw.get("last_download_directory")
                else None,
                preferred_format=DownloadFormat(
                    raw.get("preferred_format", DownloadFormat.VIDEO_MP4)
                ),
                preferred_mode=DownloadMode(raw.get("preferred_mode", DownloadMode.SINGLE)),
                compact_logs=bool(raw.get("compact_logs", True)),
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "last_download_directory": str(settings.last_download_directory)
            if settings.last_download_directory
            else None,
            "preferred_format": settings.preferred_format,
            "preferred_mode": settings.preferred_mode,
            "compact_logs": settings.compact_logs,
        }
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self.path)
