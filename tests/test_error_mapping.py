import pytest

from yt_tinker.application.download_service import map_error
from yt_tinker.domain.models import ErrorCategory


@pytest.mark.parametrize(
    ("message", "category"),
    [
        ("ffmpeg not found", ErrorCategory.FFMPEG_MISSING),
        ("JavaScript runtime is required", ErrorCategory.RUNTIME_MISSING),
        ("Sign in to confirm you are not a bot", ErrorCategory.AUTHENTICATION),
        ("Unsupported URL", ErrorCategory.UNSUPPORTED_URL),
        ("Network timed out", ErrorCategory.NETWORK),
        ("[Errno 28] No space left on device", ErrorCategory.DISK_FULL),
        ("[WinError 5] Access is denied", ErrorCategory.FILESYSTEM),
    ],
)
def test_downloader_errors_are_classified_for_the_ui(message: str, category: ErrorCategory) -> None:
    assert map_error(RuntimeError(message)).category is category
