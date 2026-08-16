from pathlib import Path

from yt_tinker.infrastructure.filesystem import (
    normalize_youtube_url,
    playlist_destination,
    sanitize_windows_filename,
)


def test_filename_sanitization_preserves_unicode_and_removes_windows_characters() -> None:
    assert sanitize_windows_filename('日本語: गीत? "test"') == "日本語_ गीत_ _test_"


def test_filename_sanitization_handles_reserved_names_and_blank_values() -> None:
    assert sanitize_windows_filename("CON") == "_CON"
    assert sanitize_windows_filename("...") == "Untitled"


def test_playlist_destination_uses_a_sanitized_subfolder() -> None:
    assert playlist_destination(Path("C:/Media"), "My: Playlist") == Path("C:/Media/My_ Playlist")


def test_url_normalization_handles_short_and_bare_youtube_urls() -> None:
    assert normalize_youtube_url(" youtu.be/abc ") == "https://youtu.be/abc"
    assert normalize_youtube_url("youtube.com/watch?v=abc") == "https://www.youtube.com/watch?v=abc"
