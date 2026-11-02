"""Two Percent as data: the opening line is the viewer's, and it is read first, above the first caption."""

import sys
from pathlib import Path

import pytest

from srstudio import opener, soft_sets

EPISODES = Path(__file__).resolve().parent.parent / "episodes"
BUG = (926, 270, 1044, 332)  # the show's bug, frame pixels


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import two_percent_audio

        return two_percent_audio
    finally:
        sys.path.pop(0)


def test_the_opening_line_is_the_viewers_and_names_nobody(data):
    assert opener.check(data.OPENING, opener.seconds(data.OPENING), names=("juno", "pip")) == data.OPENING


def test_the_opening_line_sits_above_the_first_caption_inside_the_safe_area(data):
    rows = data.OPENING.count("\n") + 1
    width = opener.PAD + 700  # wider than the line will be: the pill's top and bottom do not depend on its width
    left, top, right, bottom = opener.box(width, data.OPENER_TOP, rows=rows)
    first = data.SCRIPT[0].caption
    caption_top, _ = soft_sets.caption_band(first, y=data.UNDER_OPENER)
    assert opener.SAFE.y0 <= top and bottom < caption_top
    assert right < BUG[0]  # clear of the show's bug


def test_the_first_caption_under_the_opening_line_stays_in_the_soft_caption_zone(data):
    assert 200 <= data.UNDER_OPENER < 500  # where caption_gate looks for the Soft look's boxes
