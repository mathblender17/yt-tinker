import pytest

from yt_tinker.ui.formatting import human_duration, human_eta, human_size, human_views


@pytest.mark.parametrize(
    ("size", "expected"),
    [(None, "—"), (512, "512 B"), (2_500, "2.5 KB"), (3_800_000, "3.8 MB"), (1_500_000_000, "1.50 GB")],
)
def test_human_size(size: int | None, expected: str) -> None:
    assert human_size(size) == expected


def test_human_duration_grows_an_hours_field_only_when_needed() -> None:
    assert human_duration(None) == ""
    assert human_duration(19) == "0:19"
    assert human_duration(3661) == "1:01:01"


def test_human_views_uses_short_units() -> None:
    assert human_views(None) == ""
    assert human_views(950) == "950 views"
    assert human_views(963_000) == "963K views"
    assert human_views(1_300_000) == "1.3M views"
    assert human_views(138_000_000) == "138M views"
    assert human_views(2_100_000_000) == "2.1B views"


def test_human_eta_rounds_to_what_a_person_would_say() -> None:
    assert human_eta(45) == "45 sec left"
    assert human_eta(130) == "2 min left"
    assert human_eta(3720) == "1 hr 2 min left"
