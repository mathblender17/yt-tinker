import pytest

from yt_tinker.domain.models import ErrorCategory
from yt_tinker.infrastructure.error_mapping import map_downloader_error


@pytest.mark.parametrize(
    ("message", "category"),
    [
        ("ffmpeg not found", ErrorCategory.FFMPEG_MISSING),
        ("JavaScript runtime is required", ErrorCategory.RUNTIME_MISSING),
        ("Sign in to confirm you are not a bot", ErrorCategory.AUTHENTICATION),
        ("Unsupported URL", ErrorCategory.UNSUPPORTED_URL),
        ("Network timed out", ErrorCategory.NETWORK),
    ],
)
def test_downloader_errors_are_classified_for_the_ui(message: str, category: ErrorCategory) -> None:
    assert map_downloader_error(message).category is category
