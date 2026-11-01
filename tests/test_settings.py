from pathlib import Path

from yt_tinker.application.settings_service import AppSettings
from yt_tinker.domain.models import VideoQuality
from yt_tinker.infrastructure.settings_json import JsonSettingsRepository


def test_settings_round_trip(tmp_path: Path) -> None:
    repository = JsonSettingsRepository(tmp_path / "settings.json")
    expected = AppSettings(Path("C:/Media"), VideoQuality.MAXIMUM)
    repository.save(expected)
    assert repository.load() == expected


def test_corrupt_settings_fall_back_to_safe_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{broken", encoding="utf-8")
    assert JsonSettingsRepository(path).load() == AppSettings()
