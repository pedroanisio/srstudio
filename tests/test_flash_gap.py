"""Flashes on a Collage reel stay single: two too close are a strobe, refused before any audio is paid for or rendered,
and the same rule holds for the beats a recording re-timed."""

import pytest

from srstudio import collage_sketch
from srstudio.collage_sketch import FLASH_GAP, check_flashes
from srstudio.sketch import Beat
from srstudio.staging import StagingError


def beats(*flashes: float) -> list[Beat]:
    return [Beat(t, "gary", "", "open", "flat", "hold", None, None, "flash", ()) for t in flashes]


def test_flashes_far_apart_pass():
    check_flashes(beats(1.0, 1.0 + FLASH_GAP, 9.0), "reel")


def test_a_single_flash_or_none_passes():
    check_flashes(beats(), "reel")
    check_flashes(beats(1.0), "reel")


def test_flashes_too_close_are_refused_by_name_and_time():
    with pytest.raises(StagingError, match=r"reel: the flashes at 1.0 and 1.5 s"):
        check_flashes(beats(1.0, 1.5, 9.0), "reel")


def test_the_gap_keeps_under_the_three_a_second_a_strobe_is():
    assert 1 / FLASH_GAP < 3


def test_the_recorded_build_checks_the_beats_it_draws():
    source = collage_sketch.build.__code__.co_names
    assert "check_flashes" in source
