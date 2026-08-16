from __future__ import annotations

from yt_tinker.domain.models import DownloadError, ErrorCategory


def map_downloader_error(message: str) -> DownloadError:
    """Turn known backend messages into user-meaningful categories without exposing tracebacks."""
    normalized = message.casefold()
    if "ffmpeg" in normalized and ("not found" in normalized or "missing" in normalized):
        category = ErrorCategory.FFMPEG_MISSING
    elif "javascript runtime" in normalized or "node" in normalized and "not found" in normalized:
        category = ErrorCategory.RUNTIME_MISSING
    elif "sign in" in normalized or "cookies" in normalized:
        category = ErrorCategory.AUTHENTICATION
    elif "unsupported url" in normalized:
        category = ErrorCategory.UNSUPPORTED_URL
    elif "network" in normalized or "timed out" in normalized:
        category = ErrorCategory.NETWORK
    else:
        category = ErrorCategory.UNKNOWN
    return DownloadError(category=category, message=message)
