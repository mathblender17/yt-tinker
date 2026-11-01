from pathlib import Path

import pytest

from yt_tinker.infrastructure.filesystem import (
    is_url,
    normalize_youtube_url,
    playlist_destination,
    sanitize_windows_filename,
    youtube_playlist_id,
    youtube_video_id,
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
    assert normalize_youtube_url("youtube.com/watch?v=abc") == "https://youtube.com/watch?v=abc"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=4",
        "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "youtu.be/dQw4w9WgXcQ?si=abc",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
    ],
)
def test_video_id_is_read_from_every_link_shape(url: str) -> None:
    assert youtube_video_id(url) == "dQw4w9WgXcQ"


def test_video_id_ignores_other_pages() -> None:
    assert youtube_video_id("https://www.youtube.com/@channel") is None
    assert youtube_video_id("https://vimeo.com/watch?v=dQw4w9WgXcQ") is None


def test_playlist_id_skips_endless_radio_mixes() -> None:
    assert youtube_playlist_id("https://youtube.com/watch?v=abc&list=PLabc") == "PLabc"
    assert youtube_playlist_id("https://youtube.com/watch?v=abc&list=RDabc") is None


def test_is_url_separates_links_from_search_terms() -> None:
    assert is_url("youtube.com/watch?v=abc")
    assert is_url("https://vimeo.com/1")
    assert not is_url("lofi hip hop")
